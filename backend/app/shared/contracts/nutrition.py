from typing import Any, List, Dict, Set, Tuple, Optional
from enum import Enum
from pydantic import BaseModel, Field

# import config
from app.shared.contracts.enums import(
    Species, ActivityLevel, LifeStage,
    SterilizationStatus, ReproductiveStage,
    FoodGroup, FoodSubgroup, SlotType
)
from app.shared.contracts.enums import NutrientID

# ---------------------------------------------------------------------------
# Nutrient analysis
# ---------------------------------------------------------------------------

class NutrientAnalysis(BaseModel):
    nutrient_id:            NutrientID | str
    nutrient_name:          str
    value:                  float
    unit:                   Optional[str] = None

    min_required:           Optional[float] = None
    max_allowed:            Optional[float] = None
    ideal_target:           Optional[float] = None

    meets_min:              Optional[bool] = True
    meets_max:              Optional[bool] = True
    deviation_from_ideal:   Optional[float] = None


class NutritionDataBundle(BaseModel):
    # 不直接放 DataFrame，改成 service 层传入或 repository 层加载
    nutrient_matrix_ref                 : Optional[str] = None
    nutrient_info_ref                   : Optional[str] = None
    converted_nutrient_matrix_ref       : Optional[str] = None
    nutrient_conversion_factor_ref      : Optional[str] = None