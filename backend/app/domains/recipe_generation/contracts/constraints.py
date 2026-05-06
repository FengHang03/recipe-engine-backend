from optparse import Option
from pydantic import BaseModel, Field
from typing import Any, Dict, List, Union, Optional
from app.shared.contracts.enums import(
    NutrientID,
    FoodGroup, FoodSubgroup, SlotType
)
from app.domains.recipe_generation.contracts.enums import MacroPreference

class NutrientConstraint(BaseModel):
    nutrient_id                 : NutrientID | str
    min                         : Optional[float] = None
    max                         : Optional[float] = None
    max_soft                    : Optional[float] = None
    max_hard                    : Optional[float] = None
    ideal                       : Optional[float] = None
    safe_target                 : Optional[float] = None
    warning_target              : Optional[float] = None
    unit                        : Optional[str] = None
    basis                       : Optional[str] = None
    priority                    : Optional[int] = None
    tolerance                   : Optional[float] = None
    penalty_type                : Optional[str] = None
    source                      : Optional[str] = None
    condition                   : Optional[str] = None


class SlotConstraint(BaseModel):
    slot_type                   : SlotType
    min_ratio                   : float       # 硬最小值
    max_ratio                   : float       # 硬最大值
    ideal_min                   : float       # 理想最小值（罚分引导）
    ideal_max                   : float       # 理想最大值
    fixed_value                 : Optional[float]


class RiskTagConstraint(BaseModel):
    tag                         : str
    max_ratio                   : float       # 该风险标签食材的最大占比
    reason                      : str         # 约束原因


class SubgroupConstraint(BaseModel):
    subgroup                    : Union[FoodSubgroup, str]  # 食材子组名称
    max_ratio                   : float                     # 该子组的最大占比
    reason                      : str                       # 约束原因


class MutualExclusionRule(BaseModel):
    rule_id                     : Optional[str]         # 规则唯一标识
    ingredient_ids              : List[str]   # 互斥的食材ID列表
    max_count                   : int         # 最多可同时使用的数量
    reason                      : str         # 互斥原因


class WeightConfig(BaseModel):
    """目标函数权重配置"""
    toxic                       : float = 1e5                # 毒性罚分权重
    balance                     : float = 50               # 平衡罚分权重
    supplement                  : float = 1e3           # 补剂罚分权重
    
    # 补剂具体权重 (相对于 supplement)
    supplement_weights          :Dict[str, float] = Field(default_factory=lambda: {
        "kelp"                  : 1.0,
        "zinc"                  : 2.0,
        "vit_e"                 : 3.0,
        "fish_oil"              : 4.0,
        "calcium"               : 5.0
    })


class ConstraintBundle(BaseModel):
    nutrient_constraints        : Dict[NutrientID | str, NutrientConstraint]
    slot_constraints            : Dict[SlotType, SlotConstraint]
    risk_tag_constraints        : Dict[str, RiskTagConstraint]
    subgroup_constraints        : Dict[FoodSubgroup | str, SubgroupConstraint]
    mutual_exclusion_rules      : List[MutualExclusionRule]
    weight_config               : WeightConfig

