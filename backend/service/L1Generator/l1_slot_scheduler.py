from typing import List, Dict, Optional
from pydantic import BaseModel, Field
from enum import Enum
import logging
import pandas as pd

from backend.service.L1Generator.l1_config import (
    L1Config,
    SlotConfig,
    IngredientFilter,
)

from backend.service.L1Generator.l1_data_models import (
    Ingredient,
    RecipeCombination,
)

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SlotScheduler:
    """
    槽位调度器 - 负责根据依赖关系动态启用/禁用槽位
    """
    
    def __init__(self, config: L1Config, ingredients_df: pd.DataFrame):
        self.config = config
        self.ingredients_df = ingredients_df
        
        # 已选择的食材
        self.selected_ingredients: Dict[str, List[Ingredient]] = {}

        self.slot_states: Dict[str, str] = {}
        # 初始化槽位状态
        self._initialize_slots()
    
    def _initialize_slots(self):
        """根据默认配置初始化槽位状态"""
        self.slot_states = {
            name: slot_config.initial_state
            for name, slot_config in self.config.slots.items()
        }

    def reset(self):
        """重置调度器状态"""
        self._initialize_slots()
        self.selected_ingredients = {}

    def set_slot_state(self, slot_name: str, state: str, reason: str = ""):
        """
        设置槽位状态
        
        Args:
            slot_name: 槽位名称
            state: "mandatory" / "optional" / "disabled"
            reason: 原因说明
        """
        if slot_name not in self.config.slots:
            logger.warning(f"槽位 [{slot_name}] 不存在")
            return
        
        old_state = self.slot_states.get(slot_name, "optional")
        if old_state != state:
            self.slot_states[slot_name] = state
            logger.debug(f"槽位 [{slot_name}] 状态: {old_state} → {state} ({reason})")


    # 🟢 新增：获取槽位是否必选
    def is_slot_mandatory(self, slot_name: str) -> bool:
        return self.mandatory_slots.get(slot_name, False)
    
    def get_active_slots(self) -> List[str]:
        """
        获取当前启用的槽位（非 disabled）
        
        Returns:
            启用的槽位名称列表
        """
        return [
            name for name, state in self.slot_states.items()
            if state != "disabled"
        ]
    
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
        main_protein = self.selected_ingredients.get("main_protein", [])
        carbohydrate = self.selected_ingredients.get("carbohydrate", [])
        
        # 物种过滤：内脏应该与决策蛋白同源
        if main_protein:
            self._apply_species_constraints(main_protein[0])
        
        # === 1. Omega3 LC 逻辑 ===
        if policies.skip_omega3_lc_if_oily_fish:
            if main_protein and main_protein[0].has_tag("role_omega3_lc"):
                self.set_slot_state("omega3_lc", "disabled", "主蛋白含omega3")
            else:
                initial = self.config.slots["omega3_lc"].initial_state
                self.set_slot_state("omega3_lc", initial, "需要omega3")
        
        # === 2. Omega6 LA 逻辑 ===
        if policies.skip_omega6_la_if_fatty_meat:
            if main_protein and main_protein[0].has_tag("role_omega6_la"):
                self.set_slot_state("omega6_la", "disabled", "主蛋白含omega6")
            else:
                initial = self.config.slots["omega6_la"].initial_state
                self.set_slot_state("omega6_la", initial, "需要omega6")
        
        # === 3. 碳水逻辑 ===
        if policies.force_carb_if_lean_protein or policies.allow_no_carb_if_fatty_protein:
            if main_protein:
                subgroup = main_protein[0].food_subgroup
                if subgroup in ["meat_lean", "fish_lean"]:
                    # 瘦肉 → 碳水必选
                    self.set_slot_state("carbohydrate", "mandatory", "瘦肉需要碳水")
                else:
                    # 高脂肉 → 恢复初始状态（optional）
                    initial = self.config.slots["carbohydrate"].initial_state
                    self.set_slot_state("carbohydrate", initial, "高脂肉碳水可选")
            else:
                # 没有主蛋白 → 恢复初始状态
                initial = self.config.slots["carbohydrate"].initial_state
                self.set_slot_state("carbohydrate", initial, "未选主蛋白")
  
        
        # === 纤维逻辑 ===
        # 如果碳水含纤维,跳过纤维槽
        if policies.skip_fiber_if_carb_has_fiber:
            has_fiber_source = False
            existing_source_name = ""
            
            # 遍历所有已选槽位的食材列表
            for ing_list in self.selected_ingredients.values():
                for ing in ing_list:
                    if ing.has_tag("role_fiber_source"):
                        has_fiber_source = True
                        existing_source_name = ing.short_name
                        break
                if has_fiber_source:
                    break

            if has_fiber_source:
                # A. 已有纤维源 -> 禁用纤维槽
                self.set_slot_state(
                    "fiber", 
                    "disabled", 
                    f"已有纤维源({existing_source_name}),禁用纤维槽"
                )
            
        else:
            # B. 没有纤维源 -> 检查是否需要强制
            # 检查是否有碳水 (用于判断是否处于"无碳水"状态)
            has_carb = len(carbohydrate) > 0
            
            if not has_carb and policies.force_fiber_if_no_carb:
                # 无碳水且无其他纤维源 -> 必选
                self.set_slot_state(
                    "fiber", 
                    "mandatory", 
                    "无碳水且无其他纤维源,强制纤维必选"
                )
            else:
                # 其他情况 (有白米饭但无纤维标签，或无碳水但也无强制策略) -> 恢复默认(通常是 Optional)
                initial = self.config.slots["fiber"].initial_state
                self.set_slot_state("fiber", initial, "恢复默认状态")

        # === 碘槽逻辑（新增 2026 02 03） ===
        if policies.skip_iodine_if_high_iodine_ingredient:
            has_high_iodine = any(
                ing.has_tag("risk_high_iodine")
                for ing_list in self.selected_ingredients.values()
                for ing in ing_list
            )
            
            if has_high_iodine:
                self.set_slot_state("iodine", "disabled", "已有高碘食材")
            else:
                initial = self.config.slots["iodine"].initial_state
                self.set_slot_state("iodine", initial, "需要碘补充")

        # === optional ingredients slot logic ===
        if policies.choose_optional_ingredients:
            core_ingredients_count = 0
            for ing_list in self.selected_ingredients.values():
                for ing in ing_list:
                    if ing.ingredient_group not in ['FAT_OIL', 'SUPPLEMENT']:
                        core_ingredients_count += 1

            opt_default = self.config.slots["optional_ingredients"].is_mandatory_default
            
            if core_ingredients_count < 9:
                # 这里逻辑似乎是: 如果核心食材没满，可选槽位保持默认(通常是False)
                # 如果你想表达 "没满的时候可以选，满了就不能选"，应该在 CombinationGenerator 里控制
                # 或者在这里 Active=True/False
                self.set_slot_state("optional_ingredients", "optional", "核心食材未满,允许可选食材")
            else:
                # 满了 -> 禁用
                self.set_slot_state("optional_ingredients", "diasble", "核心食材已满,禁用可选食材")

        if main_protein:
            self._apply_species_constraints(main_protein[0])
    
    def _apply_species_constraints(self, decision_protein: Ingredient):
        """
        应用物种一致性约束
        
        确保内脏与主蛋白来自同一物种（避免 Beef + Beef Liver 的情况）
        
        Args:
            decision_protein: 决策蛋白（通常是 secondary protein，如果没有则是 primary）
        """
        # 提取物种标识
        protein_div_tag = decision_protein.get_protein_diversity_tag()
        if not protein_div_tag:
            logger.debug(f"未找到蛋白质多样性标签: {decision_protein.short_name}")
            return
        logger.debug(f"检测到主蛋白多样性标签: {protein_div_tag}")
        # 为内脏槽位添加物种排除过滤
        # organ_slots = ["organ_liver", "organ_secreting", "organ_muscular"]
        organ_slots = ["organ_liver"]
        
        for slot_name in organ_slots:
            if slot_name not in self.config.slots:
                continue
            
            slot_config = self.config.slots[slot_name]
            
            # 清除之前的物种过滤（避免累积）
            slot_config.filters.excluded_tags = [
                tag for tag in slot_config.filters.excluded_tags
                if not tag.startswith('div_protein_')
            ]

            # 添加排除同物种的过滤
            if protein_div_tag not in slot_config.filters.excluded_tags:
                slot_config.filters.excluded_tags.append(protein_div_tag)
                logger.debug(f"为槽位 [{slot_name}] 添加排除过滤: {protein_div_tag}")
    
    def get_slot_candidates(
        self,
        slot_name: str,
        limit: Optional[int] = None,
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

        candidates = self.ingredients_df.copy()

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

        # 限制数量
        if limit:
            ingredients = ingredients[:limit]
        
        logger.debug(f"槽位 [{slot_name}] 候选食材: {len(ingredients)} 个")
        
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
        # 1. 排除已使用的食材ID
        if df.empty:
            return df

        if 'ingredient_id' not in df.columns:
            return df

        used_ids = set()
        for ing_list in self.selected_ingredients.values():
            for ing in ing_list:
                used_ids.add(ing.ingredient_id)
        
        if used_ids:
            df = df[~df['ingredient_id'].isin(used_ids)]

        # 2. 排除已使用的 diversity_cluster
        used_clusters = set()
        for ing_list in self.selected_ingredients.values():
            for ing in ing_list:
                if ing.diversity_cluster and pd.notna(ing.diversity_cluster):
                    used_clusters.add(ing.diversity_cluster)
        
        if used_clusters:
            df = df[
            df['diversity_cluster'].isna() | 
            ~df['diversity_cluster'].isin(used_clusters)
        ]
        
        # 过滤
        return df
    
    def _df_to_ingredients(self, df: pd.DataFrame) -> List[Ingredient]:
        """将 DataFrame 转换为 Ingredient 对象列表"""
        ingredients = []
        for _, row in df.iterrows():
            # 处理 diversity_tags
            diversity_tags = []
            if 'diversity_tags' in row:
                if isinstance(row['diversity_tags'], list):
                    diversity_tags = row['diversity_tags']
                elif pd.notna(row['diversity_tags']):
                    # 如果是字符串，尝试解析
                    diversity_tags = [row['diversity_tags']]

            ing = Ingredient(
                ingredient_id=row['ingredient_id'],
                description=row['description'],
                short_name=row.get('short_name', row['description']),
                ingredient_group=row['ingredient_group'],
                food_subgroup=row['food_subgroup'],
                tags=row['tags'] if isinstance(row['tags'], list) else [],
                diversity_tags=diversity_tags,
                diversity_cluster=row.get('diversity_cluster'),
                max_g_per_kg_bw=row.get('max_g_per_kg_bw'),
                max_pct_kcal=row.get('max_pct_kcal')
            )
            ingredients.append(ing)
        return ingredients

