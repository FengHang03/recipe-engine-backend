from typing import Any, List, Dict, Set, Tuple, Optional
from enum import Enum
from pydantic import BaseModel, Field

# import config
from app.shared.contracts.enums import(
    Species, ActivityLevel, LifeStage, SizeClass,
    SterilizationStatus, ReproductiveStage,
)

class PetProfile(BaseModel):
    daily_calories_kcal:        float
    weight_kg:                  float

    species:                    Species | str = Species.DOG
    life_stage:                 LifeStage
    size_class:                 SizeClass | str = "medium"
    breed                     : Optional[str] = None
    age_months:                 Optional[int] = None
    activity_level:             Optional[ActivityLevel]
    sterilization_status:       Optional[SterilizationStatus] = SterilizationStatus.INTACT
    reproductive_stage:         Optional[ReproductiveStage] = ReproductiveStage.NONE
    lactation_week:             Optional[int] = 4,
    nursing_count:              Optional[int] = 1,
    allergies:                  List[str] = Field(default_factory=list)
    health_conditions:          List[str] = Field(default_factory=list)
