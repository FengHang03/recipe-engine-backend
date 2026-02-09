"""
L1 Recipe Generator - 食材组合生成层

功能:
1. 根据槽位配置和依赖规则筛选食材
2. 生成所有可能的食材组合
3. 应用互斥规则和多样性约束
4. 输出候选组合给 L2 优化

作者: Dog Recipe Optimizer
日期: 2025-01
"""

import pandas as pd
from typing import List, Dict, Set, Tuple, Optional
from dataclasses import dataclass, field
from enum import Enum
import logging
from collections import defaultdict

# 导入配置
from l1_config import (
    L1Config,
    SlotConfig,
    IngredientFilter,
    ExclusionRule,
    DependencyConfig,
    FoodGroup,
    FoodSubgroup
)

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ========== 数据模型 ==========

@dataclass
class Ingredient:
    """食材数据模型"""
    ingredient_id: str
    description: str
    short_name: str
    ingredient_group: str
    food_subgroup: str
    tags: List[str]
    diversity_cluster: Optional[str] = None
    max_g_per_kg_bw: Optional[float] = None
    max_pct_kcal: Optional[float] = None
    
    def has_tag(self, tag: str) -> bool:
        """检查是否包含指定标签"""
        return tag in self.tags
    
    def has_any_tag(self, tags: List[str]) -> bool:
        """检查是否包含任一指定标签"""
        return any(tag in self.tags for tag in tags)
    
    def has_all_tags(self, tags: List[str]) -> bool:
        """检查是否包含所有指定标签"""
        return all(tag in self.tags for tag in tags)


@dataclass
class RecipeCombination:
    """L1 输出的候选组合"""
    combination_id: str
    ingredients: Dict[str, List[Ingredient]]  # slot_name -> [ingredients]
    
    # 评分指标
    diversity_score: float = 0.0
    risk_score: float = 0.0  # 风险分数(越低越好)
    completeness_score: float = 0.0  # 完整性分数
    
    # 元数据
    active_slots: List[str] = field(default_factory=list)
    applied_rules: List[str] = field(default_factory=list)
    metadata: Dict = field(default_factory=dict)
    
    def get_all_ingredients(self) -> List[Ingredient]:
        """获取所有食材"""
        result = []
        for ing_list in self.ingredients.values():
            result.extend(ing_list)
        return result
    
    def get_ingredient_ids(self) -> List[str]:
        """获取所有食材ID"""
        return [ing.ingredient_id for ing in self.get_all_ingredients()]


# ========== 槽位调度器 ==========

class SlotScheduler:
    """
    槽位调度器 - 负责根据依赖关系动态启用/禁用槽位
    """
    
    def __init__(self, config: L1Config, ingredients_df: pd.DataFrame):
        self.config = config
        self.ingredients_df = ingredients_df
        
        # 槽位状态
        self.active_slots: Dict[str, bool] = {}
        
        # 已选择的食材
        self.selected_ingredients: Dict[str, List[Ingredient]] = {}
        
        # 初始化槽位状态
        self._initialize_slots()
    
    def _initialize_slots(self):
        """根据默认配置初始化槽位状态"""
        for slot_name, slot_config in self.config.slots.items():
            self.active_slots[slot_name] = slot_config.is_mandatory_default
    
    def reset(self):
        """重置调度器状态"""
        self._initialize_slots()
        self.selected_ingredients = {}
    
    def get_active_slots(self) -> List[str]:
        """返回当前启用的槽位列表"""
        return [name for name, active in self.active_slots.items() if active]
    
    def set_slot_active(self, slot_name: str, active: bool, reason: str = ""):
        """设置槽位启用状态"""
        if slot_name in self.active_slots:
            old_state = self.active_slots[slot_name]
            self.active_slots[slot_name] = active
            
            if old_state != active:
                action = "启用" if active else "禁用"
                logger.debug(f"{action}槽位 [{slot_name}]: {reason}")
    
    def select_ingredients_for_slot(
        self,
        slot_name: str,
        ingredients: List[Ingredient]
    ):
        """
        为指定槽位选择食材,并触发依赖规则评估
        """
        self.selected_ingredients[slot_name] = ingredients
        
        # 重新评估依赖关系
        self.apply_dependencies()
    
    def apply_dependencies(self):
        """
        根据已选择的食材应用依赖规则
        """
        policies = self.config.policies
        
        # 获取已选择的食材
        primary_protein = self.selected_ingredients.get("main_protein_primary", [])
        carbohydrate = self.selected_ingredients.get("carbohydrate", [])

        decision_protein = None
        # === [新增] 骨骼与钙逻辑 (CRITICAL) ===
        # 必须最先检查，因为这决定了是否需要补钙
        if primary_protein:
            # 检查主蛋白是否含有骨头
            # 注意：如果是混合模式，通常只看 Anchor (第一个)
            if primary_protein[0].ingredient_group == "PROTEIN_SHELLFISH":
                self.set_slot_active(
                    "main_protein_secondary",
                    True,
                    "主蛋白是甲壳类，必须选择肉类/鱼类作为辅助"
                )

                secondary_protein = self.selected_ingredients.get("main_protein_secondary", [])

                if secondary_protein:
                    # 已选 secondary，用它做判断
                    decision_protein = secondary_protein[0]
                    logger.debug(f"贝类模式：使用辅助蛋白 [{decision_protein.description}] 作为决策依据")

                else:
                    # secondary 未选，使用保守策略
                    decision_protein = primary_protein[0] 
                    logger.debug("贝类模式：secondary未选，使用保守规则")
            else:
                # 主蛋白不是贝类，禁用第二槽
                self.set_slot_active(
                    "main_protein_secondary",
                    False,
                    "主蛋白不是甲壳类，无需第二蛋白"
                )
                decision_protein = primary_protein[0]
            
            if decision_protein.has_tag("role_calcium_source"):
                self.set_slot_active(
                    "calcium", 
                    False, 
                    "主蛋白含骨骼(role_calcium_source), 跳过钙粉槽"
                )
            else:
                # 没骨头，必须开启钙槽
                self.set_slot_active(
                    "calcium", 
                    True, 
                    "主蛋白无骨骼, 强制开启钙槽"
                )
        
        # === Omega3 LC 逻辑 ===
        if policies.skip_omega3_lc_if_oily_fish and decision_protein:
            # 检查主蛋白是否含 omega3_lc
            if decision_protein.has_tag("role_omega3_lc"):
                self.set_slot_active(
                    "omega3_lc", 
                    False, 
                    "主蛋白含omega3_lc,跳过鱼油槽"
                )
            else:
                # 恢复默认状态
                default = self.config.slots["omega3_lc"].is_mandatory_default
                self.set_slot_active("omega3_lc", default, "主蛋白不含omega3_lc")
        
        # === Omega6 LA 逻辑 ===
        if policies.skip_omega6_la_if_fatty_meat and decision_protein:
            if decision_protein.has_tag("role_omega6_la"):
                self.set_slot_active(
                    "omega6_la",
                    False,
                    "主蛋白含omega6_la,跳过植物油槽"
                )
            else:
                default = self.config.slots["omega6_la"].is_mandatory_default
                self.set_slot_active("omega6_la", default, "主蛋白不含omega6_la")
        
        # === 碳水逻辑 ===
        if decision_protein:
            protein_subgroup = decision_protein.food_subgroup
            
            # 瘦肉强制碳水
            if policies.force_carb_if_lean_protein:
                if protein_subgroup in ["meat_lean", "fish_lean"]:
                    self.set_slot_active(
                        "carbohydrate",
                        True,
                        "主蛋白是瘦肉,强制开启碳水(防止蛋白中毒)"
                    )
            
            # 高脂肉允许无碳水
            if policies.allow_no_carb_if_fatty_protein:
                if protein_subgroup in ["meat_fat", "meat_moderate"]:
                    self.set_slot_active(
                        "carbohydrate",
                        False,
                        "主蛋白脂肪充足,碳水可选"
                    )
        
        # === 纤维逻辑 ===
        # 如果碳水含纤维,跳过纤维槽
        if policies.skip_fiber_if_carb_has_fiber and carbohydrate:
            if carbohydrate[0].has_tag("role_fiber_source"):
                self.set_slot_active(
                    "fiber",
                    False,
                    "碳水含纤维,跳过纤维槽"
                )
            else:
                # 如果碳水不含纤维,检查是否需要开启纤维槽
                if not self.active_slots.get("carbohydrate", False):
                    # 无碳水必选纤维
                    if policies.force_fiber_if_no_carb:
                        self.set_slot_active(
                            "fiber",
                            True,
                            "无碳水,强制开启纤维槽"
                        )
    
    def get_slot_candidates(
        self,
        slot_name: str,
        exclude_used_diversity: bool = True
    ) -> List[Ingredient]:
        """
        获取指定槽位的候选食材
        
        Args:
            slot_name: 槽位名称
            exclude_used_diversity: 是否排除已使用的diversity_cluster
        """
        if slot_name not in self.config.slots:
            return []
        
        slot_config = self.config.slots[slot_name]
        
        # 应用筛选器
        candidates = self._apply_filters(
            self.ingredients_df,
            slot_config.filters
        )
        
        # 应用多样性约束
        if exclude_used_diversity:
            candidates = self._apply_diversity_constraints(candidates)
        
        # 转换为 Ingredient 对象
        ingredients = self._df_to_ingredients(candidates)
        
        return ingredients
    
    def _apply_filters(
        self,
        df: pd.DataFrame,
        filters: IngredientFilter
    ) -> pd.DataFrame:
        """应用 IngredientFilter"""
        result = df.copy()
        
        # 过滤 ingredient_group
        if filters.allowed_groups:
            allowed = [g.value if isinstance(g, Enum) else g 
                      for g in filters.allowed_groups]
            result = result[result['ingredient_group'].isin(allowed)]
        
        # 过滤 food_subgroup
        if filters.allowed_subgroups:
            allowed = [sg.value if isinstance(sg, Enum) else sg 
                      for sg in filters.allowed_subgroups]
            result = result[result['food_subgroup'].isin(allowed)]
        
        # 必须包含的标签
        if filters.required_tags:
            def has_all_required(tags_list):
                return all(tag in tags_list for tag in filters.required_tags)
            result = result[result['tags'].apply(has_all_required)]
        
        # 必须排除的标签
        if filters.excluded_tags:
            def has_no_excluded(tags_list):
                return not any(tag in tags_list for tag in filters.excluded_tags)
            result = result[result['tags'].apply(has_no_excluded)]
        
        return result
    
    def _apply_diversity_constraints(self, df: pd.DataFrame) -> pd.DataFrame:
        """多样性约束 - 排除已使用的 diversity_cluster"""
        # 收集已使用的 clusters
        used_clusters = set()
        for ing_list in self.selected_ingredients.values():
            for ing in ing_list:
                if ing.diversity_cluster:
                    used_clusters.add(ing.diversity_cluster)
        
        if not used_clusters:
            return df
        
        # 过滤
        return df[
            df['diversity_cluster'].isna() | 
            ~df['diversity_cluster'].isin(used_clusters)
        ]
    
    def _df_to_ingredients(self, df: pd.DataFrame) -> List[Ingredient]:
        """将 DataFrame 转换为 Ingredient 对象列表"""
        ingredients = []
        for _, row in df.iterrows():
            ing = Ingredient(
                ingredient_id=row['ingredient_id'],
                description=row['description'],
                short_name=row.get('short_name', row['description']),
                ingredient_group=row['ingredient_group'],
                food_subgroup=row['food_subgroup'],
                tags=row['tags'] if isinstance(row['tags'], list) else [],
                diversity_cluster=row.get('diversity_cluster'),
                max_g_per_kg_bw=row.get('max_g_per_kg_bw'),
                max_pct_kcal=row.get('max_pct_kcal')
            )
            ingredients.append(ing)
        return ingredients


# ========== 组合生成器 ==========

class CombinationGenerator:
    """
    组合生成器 - 负责生成所有可能的食材组合
    """
    
    def __init__(
        self,
        scheduler: SlotScheduler,
        config: L1Config
    ):
        self.scheduler = scheduler
        self.config = config
        self.combination_counter = 0
    
    def generate_combinations(
        self,
        max_combinations: int = 1000,
        enable_pruning: bool = True
    ) -> List[RecipeCombination]:
        """
        生成所有可能的组合
        
        Args:
            max_combinations: 最大组合数
            enable_pruning: 是否启用剪枝优化
        
        Returns:
            候选组合列表
        """
        logger.info("开始生成食材组合...")
        logger.info(f"最大组合数限制: {max_combinations}")
        
        self.combination_counter = 0
        combinations = []
        
        # 重置调度器
        self.scheduler.reset()
        
        # 获取初始启用的槽位
        initial_slots = self.scheduler.get_active_slots()
        logger.info(f"初始启用槽位: {initial_slots}")
        
        # 递归生成组合
        self._backtrack(
            current_combo={},
            remaining_slots=initial_slots,
            combinations=combinations,
            max_combinations=max_combinations,
            enable_pruning=enable_pruning
        )
        
        logger.info(f"生成完成! 共生成 {len(combinations)} 个组合")
        
        # 计算评分
        self._score_combinations(combinations)
        
        # 排序
        combinations.sort(
            key=lambda c: (c.completeness_score, c.diversity_score, -c.risk_score),
            reverse=True
        )
        
        return combinations
    
    def _backtrack(
        self,
        current_combo: Dict[str, List[Ingredient]],
        remaining_slots: List[str],
        combinations: List[RecipeCombination],
        max_combinations: int,
        enable_pruning: bool
    ):
        """
        递归回溯生成组合
        """
        # 终止条件1: 达到最大组合数
        if len(combinations) >= max_combinations:
            return
        
        # 终止条件2: 所有槽位都已处理
        if not remaining_slots:
            # 创建完整组合
            combo = self._create_combination(current_combo)
            combinations.append(combo)
            self.combination_counter += 1
            
            if self.combination_counter % 100 == 0:
                logger.info(f"已生成 {self.combination_counter} 个组合...")
            
            return
        
        # 处理当前槽位
        current_slot = remaining_slots[0]
        next_slots = remaining_slots[1:]
        
        # 检查槽位是否仍然启用
        if not self.scheduler.active_slots.get(current_slot, False):
            # 槽位被依赖规则禁用,跳过
            self._backtrack(
                current_combo,
                next_slots,
                combinations,
                max_combinations,
                enable_pruning
            )
            return
        
        # 获取候选食材
        candidates = self.scheduler.get_slot_candidates(current_slot)
        
        if not candidates:
            # 无候选食材,跳过此槽位
            logger.warning(f"槽位 [{current_slot}] 无候选食材")
            self._backtrack(
                current_combo,
                next_slots,
                combinations,
                max_combinations,
                enable_pruning
            )
            return
        
        # 获取槽位配置
        slot_config = self.config.slots[current_slot]
        max_items = slot_config.max_items
        
        # 尝试不同数量的食材 (0 到 max_items)
        # 注意: 如果是必选槽位,从1开始
        min_items = 1 if slot_config.is_mandatory_default else 0
        
        for n_items in range(min_items, min(max_items + 1, len(candidates) + 1)):
            if n_items == 0:
                # 不选择此槽位
                self._backtrack(
                    current_combo,
                    next_slots,
                    combinations,
                    max_combinations,
                    enable_pruning
                )
            else:
                # 选择 n_items 个食材
                from itertools import combinations as iter_combinations
                
                for selected in iter_combinations(candidates, n_items):
                    selected_list = list(selected)
                    
                    # 检查是否违反互斥规则
                    if enable_pruning and self._violates_exclusion_rules(
                        current_combo, 
                        current_slot, 
                        selected_list
                    ):
                        continue
                    
                    # 更新组合
                    new_combo = current_combo.copy()
                    new_combo[current_slot] = selected_list
                    
                    # 更新调度器状态
                    self.scheduler.select_ingredients_for_slot(
                        current_slot,
                        selected_list
                    )
                    
                    # 获取更新后的槽位列表
                    updated_slots = self.scheduler.get_active_slots()
                    all_slot_names = list(self.config.slots.keys())
                    # 构建新的剩余槽位列表
                    remaining_updated = []
                    for slot_name in all_slot_names:
                        # 跳过已选择的槽位
                        if slot_name in new_combo:
                            continue
                        # 跳过当前槽位
                        if slot_name == current_slot:
                            continue
                        # 只包含当前启用的槽位
                        if slot_name in updated_slots:
                            remaining_updated.append(slot_name)
                    
                    # 递归
                    self._backtrack(
                        new_combo,
                        remaining_updated,
                        combinations,
                        max_combinations,
                        enable_pruning
                    )
                    
                    # 回溯: 清除此槽位的选择
                    self.scheduler.selected_ingredients.pop(current_slot, None)
                    self.scheduler.apply_dependencies()
    
    def _violates_exclusion_rules(
        self,
        current_combo: Dict[str, List[Ingredient]],
        new_slot: str,
        new_ingredients: List[Ingredient]
    ) -> bool:
        """
        检查是否违反互斥规则
        """
        # 创建临时组合(包含新食材)
        temp_combo = current_combo.copy()
        temp_combo[new_slot] = new_ingredients
        
        # 检查每条规则
        for rule in self.config.exclusion_rules:
            if self._check_exclusion_rule_violation(temp_combo, rule):
                return True
        
        return False
    
    def _check_exclusion_rule_violation(
        self,
        combo: Dict[str, List[Ingredient]],
        rule: ExclusionRule
    ) -> bool:
        """检查单条互斥规则是否被违反"""
        all_ingredients = []
        for ing_list in combo.values():
            all_ingredients.extend(ing_list)
        
        # 统计匹配的食材数量
        matched_count = 0
        total_weight = 0.0
        
        for ing in all_ingredients:
            # 检查 subgroup 匹配
            if rule.target_subgroups:
                subgroup_values = [
                    sg.value if isinstance(sg, Enum) else sg 
                    for sg in rule.target_subgroups
                ]
                if ing.food_subgroup in subgroup_values:
                    matched_count += 1
                    # 注意: 这里无法获取实际重量,L2会处理
                    # 这里只检查数量
            
            # 检查 tag 匹配
            if rule.target_tags:
                if ing.has_any_tag(rule.target_tags):
                    matched_count += 1
        
        # 检查是否违反数量限制
        if matched_count > rule.max_count:
            return True
        
        return False
    
    def _create_combination(
        self,
        combo_dict: Dict[str, List[Ingredient]]
    ) -> RecipeCombination:
        """创建 RecipeCombination 对象"""
        combo_id = f"combo_{self.combination_counter:04d}"
        
        return RecipeCombination(
            combination_id=combo_id,
            ingredients=combo_dict,
            active_slots=list(combo_dict.keys())
        )
    
    def _score_combinations(self, combinations: List[RecipeCombination]):
        """为组合计算评分"""
        for combo in combinations:
            # 多样性评分
            combo.diversity_score = self._calculate_diversity_score(combo)
            
            # 风险评分
            combo.risk_score = self._calculate_risk_score(combo)
            
            # 完整性评分
            combo.completeness_score = self._calculate_completeness_score(combo)
    
    def _calculate_diversity_score(self, combo: RecipeCombination) -> float:
        """
        计算多样性评分 (0-1)
        基于: diversity_cluster 的数量
        """
        all_ings = combo.get_all_ingredients()
        
        clusters = set()
        for ing in all_ings:
            if ing.diversity_cluster:
                clusters.add(ing.diversity_cluster)
        
        # 归一化: 假设最多10个不同的cluster
        return min(len(clusters) / 10.0, 1.0)
    
    def _calculate_risk_score(self, combo: RecipeCombination) -> float:
        """
        计算风险评分 (0-1, 越低越好)
        基于: risk_* 标签的数量
        """
        all_ings = combo.get_all_ingredients()
        
        risk_tags = set()
        for ing in all_ings:
            for tag in ing.tags:
                if tag.startswith('risk_'):
                    risk_tags.add(tag)
        
        # 归一化: 假设最多5个不同的风险
        return min(len(risk_tags) / 5.0, 1.0)
    
    def _calculate_completeness_score(self, combo: RecipeCombination) -> float:
        """
        计算完整性评分 (0-1)
        基于: 启用的槽位数量 / 总槽位数量
        """
        total_slots = len(self.config.slots)
        active_slots = len(combo.active_slots)
        
        return active_slots / total_slots if total_slots > 0 else 0.0


# ========== 主类: L1 Recipe Generator ==========

class L1RecipeGenerator:
    """
    L1 Recipe Generator - 主入口
    """
    
    def __init__(
        self,
        ingredients_df: pd.DataFrame,
        config: Optional[L1Config] = None
    ):
        """
        初始化 L1 生成器
        
        Args:
            ingredients_df: 食材数据 (从数据库加载)
            config: L1 配置 (可选,默认使用标准配置)
        """
        self.ingredients_df = ingredients_df
        self.config = config or L1Config()
        
        # 初始化调度器和生成器
        self.scheduler = SlotScheduler(self.config, ingredients_df)
        self.generator = CombinationGenerator(self.scheduler, self.config)
        
        logger.info(f"L1 生成器初始化完成")
        logger.info(f"  食材总数: {len(ingredients_df)}")
        logger.info(f"  配置槽位数: {len(self.config.slots)}")
    
    def generate(
        self,
        max_combinations: int = 500,
        dog_profile: Optional[Dict] = None
    ) -> List[RecipeCombination]:
        """
        生成候选组合
        
        Args:
            max_combinations: 最大组合数
            dog_profile: 狗的配置信息 (可选,用于动态调整)
        
        Returns:
            候选组合列表
        """
        logger.info("=" * 60)
        logger.info("开始 L1 食材组合生成")
        logger.info("=" * 60)
        
        # 应用狗的配置 (如果有)
        if dog_profile:
            self._apply_dog_profile(dog_profile)
        
        # 生成组合
        combinations = self.generator.generate_combinations(
            max_combinations=max_combinations,
            enable_pruning=True
        )
        
        logger.info("=" * 60)
        logger.info(f"L1 生成完成! 共 {len(combinations)} 个组合")
        logger.info("=" * 60)
        
        return combinations
    
    def _apply_dog_profile(self, dog_profile: Dict):
        """
        根据狗的配置动态调整筛选规则
        
        Args:
            dog_profile: {
                'conditions': ['hyperlipidemia', 'kidney_disease', ...],
                'allergies': ['chicken', 'beef', ...],
                'preferences': {...}
            }
        """
        conditions = dog_profile.get('conditions', [])
        allergies = dog_profile.get('allergies', [])
        
        # 根据健康状况排除某些食材
        if 'hyperlipidemia' in conditions:
            # 高血脂: 排除高胆固醇食材
            for slot_config in self.config.slots.values():
                if 'risk_cholesterol' not in slot_config.filters.excluded_tags:
                    slot_config.filters.excluded_tags.append('risk_cholesterol')
            logger.info("检测到高血脂,已排除高胆固醇食材")
        
        if 'kidney_disease' in conditions:
            # 肾脏疾病: 限制高蛋白,排除高磷食材
            logger.info("检测到肾脏疾病,建议在L2层控制蛋白质和磷含量")
        
        # 处理过敏原
        if allergies:
            allergy_tags = [f"allergen_{a}" for a in allergies]
            for slot_config in self.config.slots.values():
                slot_config.filters.excluded_tags.extend(allergy_tags)
            logger.info(f"已排除过敏原: {allergies}")
    
    def export_combinations_summary(
        self,
        combinations: List[RecipeCombination],
        top_n: int = 10
    ) -> pd.DataFrame:
        """
        导出组合摘要 (用于查看和调试)
        
        Args:
            combinations: 组合列表
            top_n: 返回前N个组合
        
        Returns:
            摘要 DataFrame
        """
        summary_data = []
        
        for combo in combinations[:top_n]:
            row = {
                'combination_id': combo.combination_id,
                'n_ingredients': len(combo.get_all_ingredients()),
                'active_slots': ','.join(combo.active_slots),
                'diversity_score': round(combo.diversity_score, 3),
                'risk_score': round(combo.risk_score, 3),
                'completeness_score': round(combo.completeness_score, 3),
            }
            
            # 添加每个槽位的食材
            for slot_name, ing_list in combo.ingredients.items():
                row[f'slot_{slot_name}'] = ','.join(
                    [ing.short_name for ing in ing_list]
                )
            
            summary_data.append(row)
        
        return pd.DataFrame(summary_data)


# ========== 使用示例 ==========

if __name__ == "__main__":
    # 这里需要实际的数据加载代码
    # 示例: 假设已经从数据库加载了数据
    
    print("L1 Recipe Generator 模块")
    print("请使用 IngredientDataLoader 加载数据后调用此模块")
    
    # 示例代码结构:
    """
    from data_loader import IngredientDataLoader
    
    # 1. 加载数据
    loader = IngredientDataLoader(connection_string="postgresql://...")
    ingredients_df = loader.load_ingredients_for_l1()
    
    # 2. 创建 L1 生成器
    l1_generator = L1RecipeGenerator(ingredients_df)
    
    # 3. 生成组合
    combinations = l1_generator.generate(max_combinations=500)
    
    # 4. 查看结果
    summary = l1_generator.export_combinations_summary(combinations, top_n=20)
    print(summary)
    
    # 5. 传递给 L2
    for combo in combinations[:10]:
        ingredient_ids = combo.get_ingredient_ids()
        # 调用 L2 优化器...
    """