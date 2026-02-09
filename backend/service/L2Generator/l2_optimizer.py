"""
L2 核心求解器
L2 Core Optimizer using Google OR-Tools

实现两阶段求解策略:
Phase 1: 无补剂求解 (优先天然食材)
Phase 2: 带补剂求解 (必要时使用)
"""

import time
from typing import List, Dict, Tuple, Optional
import pandas as pd
from collections import defaultdict

from ortools.linear_solver import pywraplp


from backend.service.common.utils import (
    UnitConverter
)
from backend.service.database.data_loader import ingredients
from .l2_data_models import (
    PetProfile, Ingredient, RecipeCombination, L2Input,
    OptimizedWeight, NutrientAnalysis, OptimizationResult,
    SolveStatus, InfeasibilityReason, InfeasibilityDiagnostic,
    LifeStage, NutrientID, SlotType, get_nutrient_value
)
from .l2_aafco_config import AAFCO_STANDARDS, get_constraint
from .l2_slot_config import (
    SLOT_CONSTRAINTS, RISK_TAG_CONSTRAINTS,
    get_slot_constraint, get_risk_constraint,
    get_ingredients_with_tag
)


# ==================== 权重配置 ====================

WEIGHT_CONFIG = {
    "toxic": 1e5,        # 毒性安全 >> 一切
    "balance": 50,       # 营养平衡优化
    "supplement": 1e3,   # 尽量少用补剂
    "ca_p_ratio": 500,   # Ca:P 比率 (特别重要)
}

# 补剂具体权重 (相对于基础补剂罚分)
SUPPLEMENT_WEIGHTS = {
    "kelp": 1.0,           # 海带: 低成本
    "zinc": 2.0,           # 锌: 中等
    "vit_e": 3.0,          # 维E: 中高
    "fish_oil": 4.0,       # 鱼油: 高
    "calcium": 5.0,        # 钙粉: 最高 (最后手段)
}

# 分段线性惩罚配置
PENALTY_CONFIG = {
    NutrientID.SELENIUM: {
        "safe_target": 120,      # µg/1000kcal
        "warning_target": 300,
        "w_safe": 0,
        "w_warning": 10,
        "w_danger": 1000
    },
    NutrientID.VITAMIN_D: {
        "safe_target": 200,      # IU/1000kcal
        "warning_target": 500,
        "w_safe": 0,
        "w_warning": 10,
        "w_danger": 1000
    },
    NutrientID.VITAMIN_A: {
        "safe_target": 10000,    # IU/1000kcal
        "warning_target": 30000,
        "w_safe": 0,
        "w_warning": 5,
        "w_danger": 500
    },
    NutrientID.IODINE: {
        "safe_target": 0.5,      # mg/1000kcal
        "warning_target": 1.5,
        "w_safe": 0,
        "w_warning": 50,
        "w_danger": 2000
    }
}


# ==================== L2 优化器类 ====================

class L2Optimizer:
    """L2 营养优化引擎"""
    
    def __init__(self, debug: bool = False):
        self.debug = debug
        self.solver = None
        self.vars = {}  # {ingredient_id: solver variable}
        self.total_weight_var = None
        self.nutrient_vars = {}  # {nutrient_id: calculated value variable}
        
    def optimize(self, l2_input: L2Input) -> OptimizationResult:
        """
        主入口: 优化食谱配方
        
        两阶段策略:
        1. 先尝试无补剂求解
        2. 如果失败,再尝试带补剂求解
        """
        start_time = time.time()
        
        # Phase 1: 无补剂求解
        if self.debug:
            print("🔍 Phase 1: Trying without supplements...")
        
        result_phase1 = self._solve_phase(
            l2_input,
            use_supplements=False
        )
        
        if result_phase1.status == SolveStatus.OPTIMAL:
            result_phase1.solve_time_seconds = time.time() - start_time
            if self.debug:
                print("✅ Phase 1 succeeded! No supplements needed.")
            return result_phase1
        
        # Phase 2: 带补剂求解
        if self.debug:
            print("🔍 Phase 2: Trying with supplements...")
        
        result_phase2 = self._solve_phase(
            l2_input,
            use_supplements=True
        )
        
        result_phase2.solve_time_seconds = time.time() - start_time
        
        if result_phase2.status == SolveStatus.OPTIMAL:
            if self.debug:
                print("✅ Phase 2 succeeded with supplements.")
        else:
            if self.debug:
                print("❌ Both phases failed.")
        
        return result_phase2
    
    def _solve_phase(
        self,
        l2_input: L2Input,
        use_supplements: bool
    ) -> OptimizationResult:
        """
        单阶段求解
        
        Args:
            l2_input: 输入数据
            use_supplements: 是否允许使用补剂
            
        Returns:
            优化结果
        """
        # 准备食材列表
        base_ingredients = []
        for ing_list in l2_input.combination.ingredients.values():
            base_ingredients.extend(ing_list)

        if l2_input.supplement_toolkit:
            all_ingredients = base_ingredients + l2_input.supplement_toolkit
        else:
            all_ingredients = base_ingredients

        unique_ingredients_map = {ing.ingredient_id: ing for ing in all_ingredients}
        final_ingredient_list = list(unique_ingredients_map.values())
        
        # 创建求解器
        self.solver = pywraplp.Solver.CreateSolver('GLOP')
        if not self.solver:
            return OptimizationResult(
                status=SolveStatus.ERROR,
                solve_time_seconds=0,
                combination_id=l2_input.combination.combination_id
            )
        
        # 设置超时 (10 秒)
        self.solver.SetTimeLimit(10000)
        
        # 创建决策变量
        self._create_variables(final_ingredient_list)
        
        # 添加硬约束
        self._add_hard_constraints(l2_input, final_ingredient_list)
        
        # 构建目标函数 (软约束 + 罚分)
        objective = self._build_objective(l2_input, final_ingredient_list, use_supplements)
        
        self.solver.Minimize(objective)
        
        # 求解
        status = self.solver.Solve()
        
        # 解析结果
        return self._parse_result(
            status,
            l2_input,
            final_ingredient_list,
            use_supplements
        )
    
    def _create_variables(self, ingredients: List[Ingredient]):
        """创建决策变量: 每个食材的重量 (g)"""
        self.vars = {}
        
        for ing in ingredients:
            # 每个食材的重量变量 (0 到无穷)
            var = self.solver.NumVar(
                0,
                self.solver.infinity(),
                f'w_{ing.ingredient_id}'
            )
            self.vars[ing.ingredient_id] = var
        
        # 总重量变量
        self.total_weight_var = self.solver.Sum([v for v in self.vars.values()])
    
    def _add_hard_constraints(
        self,
        l2_input: L2Input,
        ingredients: List[Ingredient]
    ):
        """
        添加硬约束
        
        包括:
        1. 目标热量约束
        2. AAFCO 营养素 Min/Max (P0, P1)
        3. Ca:P 比率
        4. 槽位约束
        5. 风险标签约束
        """
        pet_profile = l2_input.pet_profile
        life_stage = pet_profile.life_stage
        target_calories = pet_profile.target_calories
        nutrition_matrix = l2_input.nutrient_matrix
        
        # ===== 1. 目标热量约束 =====
        ENERGY_ID = NutrientID.ENERGY

        total_calories_expr = []

        for ing in ingredients:
            # 安全检查：确保矩阵里有这个食材和能量列
            if ing.ingredient_id not in nutrition_matrix.index:
                # 防御性编程：如果矩阵里没这个食材（虽然理论上不该发生），默认热量为0
                print(f"Warning: Ingredient {ing.ingredient_id} not found in nutrition matrix.")
                kcal_val = 0
            else:
                # 核心逻辑：从矩阵查值 per 1000 kcal
                kcal_val = nutrition_matrix.at[ing.ingredient_id, ENERGY_ID]
            # OR-Tools 逻辑: 变量(g) * (kcal/100g / 100)
            weight_var = self.vars[ing.ingredient_id]
            
            # 注意：matrix 里的单位通常是 per 100g，所以要除以 100
            total_calories_expr.append(weight_var * (kcal_val / 100.0))

        if total_calories_expr:
            total_calories_sum = self.solver.Sum(total_calories_expr)
            
            # 允许 ±5% 误差
            self.solver.Add(total_calories_sum >= target_calories * 0.95)
            self.solver.Add(total_calories_sum <= target_calories * 1.05)

        nutrient_conversion_factor = l2_input.nutrient_conversion_factor
        
        # ===== 2. AAFCO 营养素约束 =====
        self._add_nutrient_constraints(
            life_stage,
            target_calories,
            ingredients,
            nutrition_matrix,
            nutrient_conversion_factor,
        )
        
        # ===== 3. 槽位约束 (硬上限) =====
        comb_ingredients = l2_input.combination.ingredients
        self._add_slot_constraints(comb_ingredients)
        
        # ===== 4. 风险标签约束 =====
        self._add_risk_tag_constraints(ingredients)
    
    def _add_nutrient_constraints(
        self,
        life_stage: LifeStage,
        target_calories: float,
        ingredients: List[Ingredient],
        nutrition_matrix: pd.DataFrame,
        nutrient_conversion_factor: Dict[int, float],
    ):
        """添加 AAFCO 营养素约束"""
        ENERGY_ID = NutrientID.ENERGY # 1008
        standards = AAFCO_STANDARDS.get(life_stage, {})

        total_calories_expr_parts = []
        for ing in ingredients:
            if ing.ingredient_id in nutrition_matrix.index:
                kcal_val = nutrition_matrix.at[ing.ingredient_id, ENERGY_ID]
                total_calories_expr_parts.append(self.vars[ing.ingredient_id] * (kcal_val / 100.0))

        current_total_calories = self.solver.Sum(total_calories_expr_parts)

        for nutrient_id, constraint in standards.items():
            # 跳过比率约束 (单独处理)
            if isinstance(nutrient_id, str) and "RATIO" in nutrient_id: continue
            # 跳过非 NutrientID 的项
            if not isinstance(nutrient_id, NutrientID): continue
            # 只处理 P0 和 P1 级别的硬约束
            priority = constraint.get("priority", 1)
            if priority > 1:
                continue
            if nutrient_id == ENERGY_ID: continue

            nutrient_factor = nutrient_conversion_factor.get(nutrient_id.value, 1.0)
            
            # weight * amount / 100
            nutrient_expr_parts = []
            for ing in ingredients:
                if ing.ingredient_id in nutrition_matrix.index:
                    # 查表获取含量
                    # 注意: 如果 nutrient_id 在矩阵里没有列，会报错，建议加 try-except 或预检查
                    if nutrient_id in nutrition_matrix.columns:
                        amount_val = nutrition_matrix.at[ing.ingredient_id, nutrient_id]
                        # 只有含量 > 0 才加入计算 (优化性能)
                        if amount_val > 0:
                            part = self.vars[ing.ingredient_id] * (nutrient_factor * amount_val / 100.0)
                            nutrient_expr_parts.append(part)
            
            if not nutrient_expr_parts:
                continue # 如果所有食材都不含这个营养素，跳过（或者报错 Infeasible）

            current_nutrient_total = self.solver.Sum(nutrient_expr_parts)

            self.nutrient_vars[nutrient_id] = current_nutrient_total
            
            # # 计算该营养素的总量 (per 1000kcal)
            # nutrient_total = self._calculate_nutrient_total(
            #     nutrient_id,
            #     ingredients,
            #     target_calories,
            #     nutrient_factor=nutrient_factor
            # )
            
            # 添加 Min 约束
            min_val = constraint.get("min")
            if min_val is not None:
                tolerance = constraint.get("tolerance", 0)
                min_with_tolerance = min_val * (1 - tolerance)
                self.solver.Add(current_nutrient_total * 1000 >= min_with_tolerance * current_total_calories)
            
            # 添加 Max 约束 (优先 max_hard)
            max_val = constraint.get("max_hard") or constraint.get("max")
            if max_val is not None:
                self.solver.Add(current_nutrient_total * 1000 <= max_val * current_total_calories)
        
        # ===== Ca:P 比率约束 =====
        self._add_ca_p_ratio_constraint(life_stage, target_calories, nutrition_matrix, nutrient_conversion_factor)
    
    def _calculate_nutrient_total(
        self,
        nutrient_id: NutrientID,
        ingredients: List[Ingredient],
        target_calories: float,
        nutrient_factor: float,
    ):
        """
        计算营养素总量 (per 1000kcal)
        
        公式:
        Total = Σ (weight_i * nutrient_per_100g_i / 100) * (1000 / target_calories)
        """
        nutrient_sum = 0
        
        for ing in ingredients:
            weight_var = self.vars[ing.ingredient_id]
            nutrient_per_100g = get_nutrient_value(ing, nutrient_id.value)
            
            # 累加: (weight / 100) * nutrient_per_100g
            nutrient_sum += (weight_var / 100) * nutrient_per_100g
        
        # 转换为 per 1000kcal
        nutrient_per_1000kcal = nutrient_sum * (1000 / target_calories)
        
        return nutrient_per_1000kcal
    
    def _add_ca_p_ratio_constraint(
            self,
            life_stage: LifeStage,
            ingredients: List[Ingredient],
            nutrition_matrix: pd.DataFrame,
            nutrient_conversion_factor: Dict[int, float],
        ):
            """
            添加 Ca:P 比率约束 (基于矩阵查表)
            
            硬约束: 1.2 <= Ca/P <= 1.4
            线性化: Total_Ca >= min_ratio * Total_P
            """
            # 1. 获取 ID
            CA_ID = NutrientID.CALCIUM
            P_ID = NutrientID.PHOSPHORUS
            
            # 2. 获取标准配置
            # 注意: AAFCO_STANDARDS 结构可能因你的定义而异，这里假设是用 "CA_P_RATIO" 键存储
            # 或者你可能直接用 NutrientID.CA_P_RATIO (如果有定义的话)
            standards = AAFCO_STANDARDS.get(life_stage, {})
            ratio_config = standards.get("CA_P_RATIO") 
            # 如果标准里没有比率配置，直接返回
            if not ratio_config:
                return

            min_ratio = ratio_config.get("min", 1.0)
            max_ratio = ratio_config.get("max", 2.0)
            
            # 3. 获取单位转换系数 (确保 Ca 和 P 都在同一量级，通常转为 g)
            ca_factor = nutrient_conversion_factor.get(CA_ID.value, 1.0)
            p_factor = nutrient_conversion_factor.get(P_ID.value, 1.0)

            # 4. 计算 Total Calcium (物理总量)
            ca_expr_parts = []
            if CA_ID in nutrition_matrix.columns:
                for ing in ingredients:
                    if ing.ingredient_id in nutrition_matrix.index:
                        raw_val = nutrition_matrix.at[ing.ingredient_id, CA_ID]
                        if raw_val > 0:
                            # Weight * (Raw * Factor / 100)
                            ca_expr_parts.append(
                                self.vars[ing.ingredient_id] * (raw_val * ca_factor / 100.0)
                            )

            # 5. 计算 Total Phosphorus (物理总量)
            p_expr_parts = []
            if P_ID in nutrition_matrix.columns:
                for ing in ingredients:
                    if ing.ingredient_id in nutrition_matrix.index:
                        raw_val = nutrition_matrix.at[ing.ingredient_id, P_ID]
                        if raw_val > 0:
                            p_expr_parts.append(
                                self.vars[ing.ingredient_id] * (raw_val * p_factor / 100.0)
                            )
            
            # 防御性检查：如果没有任何食材含钙或磷，无法添加约束
            if not ca_expr_parts or not p_expr_parts:
                return

            total_ca = self.solver.Sum(ca_expr_parts)
            total_p = self.solver.Sum(p_expr_parts)

            # 6. 添加线性约束
            # 原理: Ca / P >= min  --->  Ca >= min * P
            self.solver.Add(total_ca >= min_ratio * total_p)
            
            # 原理: Ca / P <= max  --->  Ca <= max * P
            self.solver.Add(total_ca <= max_ratio * total_p)
    
    def _add_slot_constraints(self, comb_ingredients: Dict[str, List[Ingredient]]):
            """添加槽位约束 (硬上限)"""
            
            # ✅ 修改点 1: 直接遍历字典的 items()
            # key 是 slot_name (槽位名), value 是 ingredients (该槽位下的食材列表)
            for slot_name, ingredients_in_slot in comb_ingredients.items():
                
                # 1. 收集当前槽位下所有食材的变量
                current_slot_vars = []
                for ing in ingredients_in_slot:
                    # 确保该食材在优化变量中有定义 (防御性检查)
                    if ing.ingredient_id in self.vars:
                        current_slot_vars.append(self.vars[ing.ingredient_id])
                
                # 如果该槽位没有对应的变量（可能被过滤掉了），跳过
                if not current_slot_vars:
                    continue

                # 2. 计算该槽位的总重量 (Sum Expression)
                slot_weight_sum = self.solver.Sum(current_slot_vars)

                # 3. 获取约束配置
                # 注意：这里直接用 loop 中的 slot_name
                constraint = get_slot_constraint(slot_name)
                if not constraint:
                    continue
                
                # 4. 添加约束
                # 硬最大值: Slot_Weight <= Max% * Total_Weight
                if constraint.max_ratio is not None:
                    self.solver.Add(
                        slot_weight_sum <= constraint.max_ratio * self.total_weight_var
                    )
                
                # 硬最小值: Slot_Weight >= Min% * Total_Weight
                if constraint.min_ratio is not None and constraint.min_ratio > 0:
                    self.solver.Add(
                        slot_weight_sum >= constraint.min_ratio * self.total_weight_var
                    )
    
    def _add_risk_tag_constraints(self, ingredients: List[Ingredient]):
        """添加风险标签约束"""
        for tag, constraint in RISK_TAG_CONSTRAINTS.items():
            # 找到带有该标签的食材
            tagged_ingredients = get_ingredients_with_tag(ingredients, tag)
            
            if not tagged_ingredients:
                continue
            
            # 这些食材的总重量不能超过限制
            tagged_weight = sum(self.vars[ing.ingredient_id] for ing in tagged_ingredients)
            
            self.solver.Add(
                tagged_weight <= constraint.max_ratio * self.total_weight_var
            )
    
    def _build_objective(
        self,
        l2_input: L2Input,
        ingredients: List[Ingredient],
        use_supplements: bool
    ):
        """
        构建目标函数
        
        Minimize: Z = W_toxic * P_toxic + W_balance * P_balance + W_supplement * P_supplement
        """
        objective = 0
        
        # ===== 1. 毒性罚分 (ALARA) =====
        toxic_penalty = self._build_toxic_penalty(l2_input.pet_profile.life_stage)
        objective += WEIGHT_CONFIG["toxic"] * toxic_penalty
        
        # ===== 2. 平衡罚分 =====
        balance_penalty = self._build_balance_penalty(l2_input.pet_profile.life_stage)
        objective += WEIGHT_CONFIG["balance"] * balance_penalty
        
        # ===== 3. Ca:P 理想比率罚分 =====
        ca_p_penalty = self._build_ca_p_penalty(l2_input.pet_profile.life_stage)
        objective += WEIGHT_CONFIG["ca_p_ratio"] * ca_p_penalty
        
        # ===== 4. 补剂罚分 =====
        if use_supplements:
            supplement_penalty = self._build_supplement_penalty(ingredients)
            objective += WEIGHT_CONFIG["supplement"] * supplement_penalty
        
        # ===== 5. 槽位理想范围罚分 (软约束) =====
        slot_penalty = self._build_slot_penalty(ingredients)
        objective += 10 * slot_penalty  # 权重较低
        
        return objective
    
    def _build_toxic_penalty(self, life_stage: LifeStage):
        """
        构建毒性元素罚分 (ALARA)
        
        使用分段线性惩罚
        """
        penalty = 0
        
        for nutrient_id, config in PENALTY_CONFIG.items():
            if nutrient_id not in self.nutrient_vars:
                continue
            
            nutrient_var = self.nutrient_vars[nutrient_id]
            
            # 获取约束的 min 值
            constraint = get_constraint(life_stage, nutrient_id)
            min_val = constraint.get("min", 0)
            
            # 分段惩罚
            safe_target = config["safe_target"]
            warning_target = config["warning_target"]
            
            # 安全区偏差: [min, safe_target]
            dev_safe = self.solver.NumVar(0, self.solver.infinity(), f'{nutrient_id.value}_dev_safe')
            self.solver.Add(dev_safe >= nutrient_var - safe_target)
            self.solver.Add(dev_safe >= 0)
            
            # 警戒区偏差: [safe_target, warning_target]
            dev_warning = self.solver.NumVar(0, self.solver.infinity(), f'{nutrient_id.value}_dev_warning')
            self.solver.Add(dev_warning >= nutrient_var - warning_target)
            self.solver.Add(dev_warning >= 0)
            
            # 累加罚分
            penalty += config["w_safe"] * dev_safe
            penalty += config["w_warning"] * dev_warning
        
        return penalty
    
    def _build_balance_penalty(self, life_stage: LifeStage):
        """
        构建平衡元素罚分
        
        引导营养素接近理想值
        """
        penalty = 0
        
        balance_nutrients = [
            NutrientID.ZINC,
            NutrientID.MANGANESE,
            NutrientID.COPPER
        ]
        
        for nutrient_id in balance_nutrients:
            if nutrient_id not in self.nutrient_vars:
                continue
            
            nutrient_var = self.nutrient_vars[nutrient_id]
            constraint = get_constraint(life_stage, nutrient_id)
            ideal = constraint.get("ideal")
            
            if not ideal:
                continue
            
            # 双向偏差
            deviation = self.solver.NumVar(0, self.solver.infinity(), f'{nutrient_id.value}_dev')
            self.solver.Add(deviation >= nutrient_var - ideal)
            self.solver.Add(deviation >= ideal - nutrient_var)
            
            penalty += deviation
        
        return penalty
    
    def _build_ca_p_penalty(self, life_stage: LifeStage):
        """
        构建 Ca:P 理想比率罚分
        
        引导比率接近 1.3:1
        """
        ca_var = self.nutrient_vars.get(NutrientID.CALCIUM)
        p_var = self.nutrient_vars.get(NutrientID.PHOSPHORUS)
        
        if not ca_var or not p_var:
            return 0
        
        ratio_constraint = AAFCO_STANDARDS[life_stage].get("CA_P_RATIO", {})
        ideal_ratio = ratio_constraint.get("ideal", 1.3)
        
        # 偏差: |Ca - ideal_ratio * P|
        deviation = self.solver.NumVar(0, self.solver.infinity(), 'ca_p_dev')
        self.solver.Add(deviation >= ca_var - ideal_ratio * p_var)
        self.solver.Add(deviation >= ideal_ratio * p_var - ca_var)
        
        return deviation
    
    def _build_supplement_penalty(self, ingredients: List[Ingredient]):
        """
        构建补剂罚分
        
        补剂权重 = 基础罚分 × 补剂类型系数
        """
        penalty = 0
        
        for ing in ingredients:
            if not ing.is_supplement:
                continue
            
            weight_var = self.vars[ing.ingredient_id]
            
            # 根据补剂类型确定系数
            supplement_type = ing.ingredient_id.replace("sup_", "").replace("supplement_", "")
            coeff = SUPPLEMENT_WEIGHTS.get(supplement_type, 3.0)
            
            penalty += coeff * weight_var
        
        return penalty
    
    def _build_slot_penalty(self, ingredients: List[Ingredient]):
        """
        构建槽位理想范围罚分 (软约束)
        
        引导槽位占比接近理想范围
        """
        penalty = 0
        
        # 按槽位分组
        slot_weights = defaultdict(lambda: 0)
        for ing in ingredients:
            slot_weights[ing.slot] += self.vars[ing.ingredient_id]
        
        # 对每个槽位
        for slot, weight_sum in slot_weights.items():
            constraint = get_slot_constraint(slot)
            if not constraint:
                continue
            
            # 如果有理想最小值,且当前可能低于
            if constraint.ideal_min:
                dev_min = self.solver.NumVar(0, self.solver.infinity(), f'{slot.value}_dev_min')
                self.solver.Add(dev_min >= constraint.ideal_min * self.total_weight_var - weight_sum)
                penalty += dev_min
            
            # 如果有理想最大值,且当前可能高于
            if constraint.ideal_max:
                dev_max = self.solver.NumVar(0, self.solver.infinity(), f'{slot.value}_dev_max')
                self.solver.Add(dev_max >= weight_sum - constraint.ideal_max * self.total_weight_var)
                penalty += dev_max
        
        return penalty
    
    def _parse_result(
        self,
        status: int,
        l2_input: L2Input,
        ingredients: List[Ingredient],
        use_supplements: bool
    ) -> OptimizationResult:
        """解析求解结果"""
        
        # 转换状态
        if status == pywraplp.Solver.OPTIMAL:
            solve_status = SolveStatus.OPTIMAL
        elif status == pywraplp.Solver.FEASIBLE:
            solve_status = SolveStatus.FEASIBLE
        elif status == pywraplp.Solver.INFEASIBLE:
            solve_status = SolveStatus.INFEASIBLE
        else:
            solve_status = SolveStatus.TIMEOUT
        
        # 如果不可行,进行诊断
        if solve_status == SolveStatus.INFEASIBLE:
            return OptimizationResult(
                status=solve_status,
                solve_time_seconds=0,
                combination_id=l2_input.combination.combination_id,
                infeasibility_diagnostic=self._diagnose_infeasibility(l2_input)
            )
        
        # 提取结果
        weights = []
        used_supplements = []
        
        for ing in ingredients:
            weight = self.vars[ing.ingredient_id].solution_value()
            
            # 忽略极小的重量 (< 0.1g)
            if weight < 0.1:
                continue
            
            weights.append(OptimizedWeight(
                ingredient_id=ing.ingredient_id,
                ingredient_name=ing.name,
                weight_grams=weight,
                is_supplement=ing.is_supplement
            ))
            
            if ing.is_supplement:
                used_supplements.append(ing.ingredient_id)
        
        total_weight = sum(w.weight_grams for w in weights)
        
        # 营养分析
        nutrient_analysis = self._analyze_nutrients(
            weights,
            ingredients,
            l2_input.pet_profile
        )
        
        # 罚分分解
        penalty_breakdown = {
            "toxic": 0,  # TODO: 计算实际罚分
            "balance": 0,
            "supplement": 0
        }
        
        return OptimizationResult(
            status=solve_status,
            solve_time_seconds=0,  # 由外层填充
            weights=weights,
            total_weight_grams=total_weight,
            nutrient_analysis=nutrient_analysis,
            objective_value=self.solver.Objective().Value(),
            penalty_breakdown=penalty_breakdown,
            combination_id=l2_input.combination.combination_id,
            used_supplements=used_supplements
        )
    
    def _analyze_nutrients(
        self,
        weights: List[OptimizedWeight],
        ingredients: List[Ingredient],
        pet_profile: PetProfile
    ) -> List[NutrientAnalysis]:
        """生成营养分析报告"""
        
        # 构建食材字典
        ing_dict = {ing.ingredient_id: ing for ing in ingredients}
        
        # 计算总热量
        total_calories = 0
        for w in weights:
            ing = ing_dict[w.ingredient_id]
            total_calories += (w.weight_grams / 100) * ing.calories_per_100g
        
        # 计算每个营养素
        analyses = []
        standards = AAFCO_STANDARDS[pet_profile.life_stage]
        
        for nutrient_id, constraint in standards.items():
            if not isinstance(nutrient_id, NutrientID):
                continue
            
            # 计算总量
            nutrient_total = 0
            for w in weights:
                ing = ing_dict[w.ingredient_id]
                nutrient_per_100g = get_nutrient_value(ing, nutrient_id.value)
                nutrient_total += (w.weight_grams / 100) * nutrient_per_100g
            
            # 转换为 per 1000kcal
            value_per_1000kcal = nutrient_total * (1000 / total_calories) if total_calories > 0 else 0
            
            # 检查达标情况
            min_val = constraint.get("min")
            max_val = constraint.get("max_hard") or constraint.get("max")
            ideal_val = constraint.get("ideal")
            
            meets_min = True if min_val is None else value_per_1000kcal >= min_val
            meets_max = True if max_val is None else value_per_1000kcal <= max_val
            
            deviation = None
            if ideal_val:
                deviation = abs(value_per_1000kcal - ideal_val)
            
            analyses.append(NutrientAnalysis(
                nutrient_id=nutrient_id.value,
                nutrient_name=nutrient_id.value.replace("_", " ").title(),
                value=value_per_1000kcal,
                unit=constraint.get("unit", ""),
                min_required=min_val,
                max_allowed=max_val,
                ideal_target=ideal_val,
                meets_min=meets_min,
                meets_max=meets_max,
                deviation_from_ideal=deviation
            ))
        
        return analyses
    
    def _diagnose_infeasibility(self, l2_input: L2Input) -> InfeasibilityDiagnostic:
        """诊断不可行性 (简化版)"""
        
        # TODO: 实现详细的诊断逻辑
        # 这里先返回一个通用的诊断
        
        return InfeasibilityDiagnostic(
            reason=InfeasibilityReason.UNKNOWN,
            conflicting_nutrients=[],
            suggestion="尝试更换食材组合或放宽约束"
        )

    def precalculate_conversion_factors(
        self, 
        l2_input: L2Input, 
        life_stage: LifeStage = LifeStage.DOG_ADULT,
    ) -> Dict[int, float]:
        """
        预计算营养素单位转换系数 Map (仅处理分子量级，如 mg -> g)
        
        Returns:
            Dict[nutrient_id, factor]
            例如: {
                1003: 1.0,    # Protein: g -> g
                1004: 0.001,  # Calcium: mg -> g
                1104: 0.0003  # Vit A: mcg RAE -> IU (假设值)
            }
        """
        conversion_map = {}
        standards = AAFCO_STANDARDS.get(life_stage, {})

        ENERGY_ID = NutrientID.ENERGY
        conversion_map[ENERGY_ID] = 1.0

        nutrient_matrix = l2_input.nutrient_matrix
        nutrient_info = l2_input.nutrient_info

        kcal_val = nutrient_matrix.at[ing.ingredient_id, ENERGY_ID]

        for nutrient_id, row in nutrient_info.iterrows():
            source_unit = row['unit_name'] # DB 单位, e.g., 'mg'
            
            # 获取 AAFCO 标准单位
            std_config = standards.get(nutrient_id)
            if not std_config:
                conversion_map[nutrient_id] = 1.0 # 无标准，保持原样
                continue
                
            target_unit_full = std_config.get("unit", "g/1000kcal")
            
            # === 核心逻辑 ===
            # 我们只提取分子部分进行对比 (mg vs g)
            # 因为分母 (/1000kcal) 的逻辑是在 Solver 的线性约束里处理的
            
            # 解析目标分子 (如 "g/1000kcal" -> "g")
            target_numerator, _ = UnitConverter.parse_unit_string(target_unit_full, default_denom='1000kcal')
            
            # 解析来源分子 (如 "mg" -> "mg")
            source_numerator, _ = UnitConverter.parse_unit_string(source_unit, default_denom='100g')

            try:
                # 计算系数 (mg -> g)
                # 这里调用你之前的 calculate_magnitude_factor 或 get_unit_factor
                # 这里的 threshold_unit 只需要传分子即可，比如 "g/100g" 骗过函数，或者重写一个纯净的 magnitude 函数
                
                # 假设你已经有一个 clean 的 magnitude 计算函数
                factor = UnitConverter.get_unit_factor(
                    nutrient_id=nutrient_id,
                    nutrient_unit=source_numerator, # "mg"
                    threshold_unit=target_numerator # "g"
                )
                base_factor = UnitConverter.get_base_factor(
                    energy_series=energy
                )
                
                conversion_map[nutrient_id] = factor
                
            except Exception as e:
                print(f"Factor calc error {nutrient_id}: {e}")
                conversion_map[nutrient_id] = 1.0

        return conversion_map