from typing import Any, List, Dict, Set, Tuple, Optional
from enum import Enum
from pydantic import BaseModel, Field, AliasChoices

# import config
from app.shared.contracts.enums import(
    FoodGroup, FoodSubgroup, SlotType,
    NutrientID
)

class PrepState(str, Enum):
    """
    Internal analysis basis/state.

    AS_IS:
        Use the current ingredient_id and current weight directly.

    RAW:
        Convert current ingredient/weight into raw-equivalent ingredient/weight.

    COOKED:
        Convert current ingredient/weight into cooked ingredient/weight.
    """
    AS_IS = "as_is"
    RAW = "raw"
    COOKED = "cooked"

class IngredientRef(BaseModel):
    ingredient_id:          str
    description:            Optional[str] = Field(
        default=None,
        validation_alias=AliasChoices("description", "name")
    )
    short_name:             Optional[str] = None
    fdc_id:                 Optional[str] = None
    prep_state:             Optional[PrepState] = "as_is"
    raw_equivalent_fdc_id  :Optional[str] = None
    yield_factor:           Optional[float] = None
    food_group:             FoodGroup
    food_subgroup:          Optional[FoodSubgroup] = None
    default_slot:           Optional[SlotType] = None
    tags:                   List[str] = Field(default_factory=list)
    diversity_cluster:      Optional[str] = None
    diversity_tags:         List[str] = Field(default_factory=list)

    def __init__(self, /, **data: Any) -> None:
        super().__init__(**data)
    
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
    
    def in_food_group(self, groups: List[FoodGroup]) -> bool:
    # 直接比较枚举实例，类型完全统一
        return self.food_group in groups

class IngredientProfile(IngredientRef):
    energy_per_100g:        Optional[float] = None
    max_g_per_kg_bw:        Optional[float] = None
    max_pct_kcal:           Optional[float] = None

    nutrients_per_100g:     Dict[NutrientID, float] = Field(default_factory=dict)
    is_supplement:          bool = False
