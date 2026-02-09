from typing import List, Dict, Set, Tuple, Optional
from dataclasses import dataclass, field
from enum import Enum

# 导入配置
from .enums import (
    FoodGroup,
    FoodSubgroup
)

@dataclass
class Ingredient:
    """食材数据模型"""
    ingredient_id: str
    description: str
    short_name: str
    ingredient_group: str
    food_subgroup: str
    tags: List[str]
    diversity_tags: Optional[List[str]] = field(default_factory=list)
    diversity_cluster: Optional[str] = None
    max_g_per_kg_bw: Optional[float] = None
    max_pct_kcal: Optional[float] = None
    
    def has_tag(self, tag: str) -> bool:
        """检查是否包含指定标签"""
        return tag in self.tags

    def get_protein_diversity_tag(self) -> Optional[str]:
        """
        获取蛋白质多样性标签
        
        Returns:
            div_protein_* 标签，例如 "div_protein_ruminant", "div_protein_poultry"
        """
        for tag in self.diversity_tags:
            if tag.startswith('div_protein_'):
                return tag
        # 兼容旧的 tags 字段
        for tag in self.tags:
            if tag.startswith('div_protein_'):
                return tag
        return None
    
    def has_any_tag(self, tags: List[str]) -> bool:
        """检查是否包含任一指定标签"""
        return any(tag in self.tags for tag in tags)
    
    def has_all_tags(self, tags: List[str]) -> bool:
        """检查是否包含所有指定标签"""
        return all(tag in self.tags for tag in tags)
    
    def in_ingredient_group(self, group: List[FoodGroup]) -> bool:
        if self.ingredient_group in [g.value for g in group]:
            return True
        else: False

@dataclass
class RecipeCombination:
    """L1 输出的候选组合"""
    combination_id: str
    ingredients: Dict[str, List[Ingredient]]  # slot_name -> [ingredients]
    
    # 评分指标
    diversity_score: float = 0.0
    risk_score: float = 0.0  # 风险分数(越低越好)
    completeness_score: float = 0.0  # 完整性分数

    n_core_ingredients: int = 0
    n_fat_oil: int = 0  # FAT_OIL数量
    n_supplement: int = 0  # SUPPLEMENT数量
    n_total_items: int = 0  # 总食材数
    
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
    
    def calculate_ingredient_stats(self):
        """
        计算食材分类统计
        
        分类：
        - 核心食材: 不包括 FAT_OIL 和 SUPPLEMENT
        - FAT_OIL: 食用油
        - SUPPLEMENT: 补充剂
        """
        self.n_core_ingredients = 0
        self.n_fat_oil = 0
        self.n_supplement = 0
        self.n_total_items = 0
        
        for ing in self.get_all_ingredients():
            self.n_total_items += 1
            
            if ing.ingredient_group == "FAT_OIL":
                self.n_fat_oil += 1
            elif ing.ingredient_group == "SUPPLEMENT":
                self.n_supplement += 1
            else:
                self.n_core_ingredients += 1

    def get_ingredient_ids(self) -> List[str]:
        """获取所有食材ID"""
        return [ing.ingredient_id for ing in self.get_all_ingredients()]
