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

from numpy import core
import pandas as pd
from typing import List, Dict, Set, Tuple, Optional
from dataclasses import dataclass, field
from enum import Enum
import logging
from collections import defaultdict

# 导入配置
from backend.service.L1Generator.l1_config import (
    L1Config,
    SlotConfig,
    IngredientFilter,
    ExclusionRule,
    DependencyConfig,
)

from backend.service.L1Generator.l1_data_models import (
    Ingredient,
    RecipeCombination,
)

from backend.service.L1Generator.l1_slot_scheduler import (
    SlotScheduler
)

# from service.common.models import (
#     Ingredient,
#     RecipeCombination
# )

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class CombinationGenerator:
    """
    组合生成器 - 负责生成所有可能的食材组合
    """
    
    def __init__(
        self,
        scheduler: SlotScheduler,
        config: L1Config,
        max_core_ingredients: int = 9
    ):
        self.scheduler = scheduler
        self.config = config
        self.max_core_ingredients = max_core_ingredients
        self.combination_counter = 0
        self.seen_combinations = set()  # 新增：记录已见过的组合签名
    
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
        self.seen_combinations.clear()
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

    def _get_slot_state(self, slot_name: str) -> str:
        """
        获取槽位的当前状态（从 scheduler 获取）
        
        Returns:
            "disabled": 不选（跳过）
            "optional": 可选（尝试0和1+）
            "mandatory": 必选（至少1个）
        """
        return self.scheduler.slot_states.get(slot_name, "optional")
    
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
        # === check core ingredients count ===
        current_core_count = self._count_core_ingredients(current_combo)

        # 终止条件1: 达到最大组合数
        if current_core_count >= self.max_core_ingredients:
            return
        
        # 终止条件2: 所有槽位都已处理
        if not remaining_slots:
            # 创建完整组合（可能返回 None 如果是重复）
            combo = self._create_combination(current_combo)
            if combo is not None:
                combinations.append(combo)
                if len(combinations) % 100 == 0:
                    logger.info(f"已生成 {len(combinations)} 个唯一组合 (核心食材: {current_core_count})...")
            else:
                logger.debug("检测到重复组合，已跳过")
            return
        
        # 处理当前槽位
        current_slot = remaining_slots[0]
        next_slots = remaining_slots[1:]

        slot_config = self.config.slots[current_slot]
        slot_state = self._get_slot_state(current_slot)
        
        # 1. 检查槽位是否仍然启用
        if slot_state == "disabled":
            # 不选：直接跳过此槽位
            logger.debug(f"槽位 [{current_slot}] 被禁用，跳过")
            self._backtrack(
                current_combo,
                next_slots,
                combinations,
                max_combinations,
                enable_pruning
            )
            return
        
        # 2. 获取候选食材
        candidates = self.scheduler.get_slot_candidates(current_slot, exclude_used_diversity=slot_config.apply_diversity)
        
        if not candidates:
            # 无候选食材,跳过此槽位
            # logger.warning(f"槽位 [{current_slot}] 无候选食材")
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
        min_items = slot_config.min_item
        is_core_slot = self._is_core_ingredient_slot(current_slot)
        
        # === 根据动态状态计算 min_items ===
        if slot_state == "mandatory":
            min_items = 1  # 必选：至少1个
        else:  # optional
            # 可选：检查核心食材上限
            if is_core_slot and current_core_count >= self.max_core_ingredients:
                logger.debug(f"槽位 [{current_slot}] 跳过：核心食材已满 ({current_core_count}/{self.max_core_ingredients})")
                self._backtrack(
                    current_combo,
                    next_slots,
                    combinations,
                    max_combinations,
                    enable_pruning
                )
                return
            min_items = 0  # 可选：可以选0

        # 3. 遍历候选数量
        for n_items in range(min_items, min(max_items + 1, len(candidates) + 1)):
            # 检查核心食材上限
            if is_core_slot and n_items > 0:
                if current_core_count + n_items > self.max_core_ingredients:
                    continue

            if n_items == 0:
                # 不选择此槽位
                self._backtrack(
                    current_combo,
                    next_slots,
                    combinations,
                    max_combinations,
                    enable_pruning
                )
                continue
            # 选择 n_items 个食材
            from itertools import combinations as iter_combinations
            
            for selected in iter_combinations(candidates, n_items):
                selected_list = list(selected)

                # 1. 计算当前选择中包含了几个核心食材
                new_core_count = sum(1 for ing in selected_list if self._is_core_ingredient(ing))
                
                if new_core_count > 0 and (current_core_count + new_core_count > self.max_core_ingredients):
                    # logger.debug(f"跳过选择: 核心食材超标 ({current_core_count} + {new_core_count} > {self.max_core_ingredients})")
                    continue

                # 2. 检查是否违反互斥规则
                if enable_pruning and self._violates_exclusion_rules(
                    current_combo, 
                    current_slot, 
                    selected_list
                ):
                    continue
                
                # 3. 更新组合
                new_combo = current_combo.copy()
                new_combo[current_slot] = selected_list

                # 4. 更新调度器状态
                self.scheduler.select_ingredients_for_slot(
                    current_slot,
                    selected_list
                )
                
                # === [修复] 获取更新后的槽位列表 ===
                # 关键修复: 重新扫描所有未选择的槽位，包括被动态启用的
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
    ) -> Optional[RecipeCombination]:
        """
        创建 RecipeCombination 对象，并检查是否重复
        
        Returns:
            RecipeCombination 对象，如果是重复组合则返回 None
        """
        # 生成组合的唯一签名
        signature = self._generate_combo_signature(combo_dict)
        
        # 检查是否重复
        if signature in self.seen_combinations:
            logger.debug(f"跳过重复组合: {signature[:50]}...")
            return None
        
        # 记录签名
        self.seen_combinations.add(signature)
        
        # 创建组合
        combo_id = f"combo_{self.combination_counter:04d}"
        self.combination_counter += 1
        
        return RecipeCombination(
            combination_id=combo_id,
            ingredients=combo_dict,
            active_slots=list(combo_dict.keys())
        )
    
    def _generate_combo_signature(
        self,
        combo_dict: Dict[str, List[Ingredient]]
    ) -> str:
        """
        生成组合的唯一签名
        
        使用排序后的 ingredient_id 列表作为签名
        这样即使槽位顺序不同，相同食材的组合也会被识别为重复
        """
        all_ids = []
        for slot_name in sorted(combo_dict.keys()):
            for ing in sorted(combo_dict[slot_name], key=lambda x: x.ingredient_id):
                all_ids.append(ing.ingredient_id)
        
        return '|'.join(all_ids)

    def _count_core_ingredients(self, combo: Dict[str, List[Ingredient]]) -> int:
        """
        统计当前组合中的核心食材数量（不含 FAT_OIL 和 SUPPLEMENT）
        """
        count = 0
        for ing_list in combo.values():
            for ing in ing_list:
                if self._is_core_ingredient(ing):
                    count += 1
        return count
    
    def _is_core_ingredient(self, ingredient: Ingredient) -> bool:
        """
        判断单个食材是否为核心食材
        
        逻辑：排除 FAT_OIL 和 SUPPLEMENT，其他都算核心食材
        """
        # 注意：请确保 ingredient_group 的字符串与数据库中的一致
        non_core_groups = ["FAT_OIL", "SUPPLEMENT"]
        return ingredient.ingredient_group not in non_core_groups
    
    def _is_core_ingredient_slot(self, slot_name: str) -> bool:
        """
        判断槽位是否包含核心食材
        
        FAT_OIL 和 SUPPLEMENT 不是核心食材
        """
        if slot_name not in self.config.slots:
            return False
        
        slot_config = self.config.slots[slot_name]
        
        # 检查 is_core_ingredient 字段
        if hasattr(slot_config, 'is_core_ingredient'):
            return slot_config.is_core_ingredient
        
        # 默认逻辑：检查 allowed_groups
        for group in slot_config.filters.allowed_groups:
            group_str = str(group)
            if 'FAT_OIL' in group_str or 'SUPPLEMENT' in group_str:
                return False
        
        return True

    def _score_combinations(self, combinations: List[RecipeCombination]):
        """为组合计算评分"""
        for combo in combinations:
            # 食材统计（新增）
            combo.calculate_ingredient_stats()

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
        config: Optional[L1Config] = None,
        max_core_ingredients: int = 9
    ):
        """
        初始化 L1 生成器
        
        Args:
            ingredients_df: 食材数据 (从数据库加载)
            config: L1 配置 (可选,默认使用标准配置)
            max_core_ingredients: 核心食材数量上限 (不含FAT_OIL和SUPPLEMENT)
        """
        self.ingredients_df = ingredients_df
        self.config = config or L1Config()
        self.max_core_ingredients = max_core_ingredients
        
        # 初始化调度器和生成器
        self.scheduler = SlotScheduler(self.config, ingredients_df)
        self.generator = CombinationGenerator(self.scheduler, self.config, max_core_ingredients=max_core_ingredients)
        
        logger.info(f"L1 生成器初始化完成")
        logger.info(f"  食材总数: {len(ingredients_df)}")
        logger.info(f"  配置槽位数: {len(self.config.slots)}")
        logger.info(f"  核心食材上限: {max_core_ingredients}")
    
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