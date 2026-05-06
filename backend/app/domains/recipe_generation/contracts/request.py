"""
这个文件应该放什么

它只放进入 recipe_generation orchestration 的请求模型。
不要放 domain entity，不要放 recipe template。


C. RecipeGenerationRequest

这是主入口 request。

字段建议：
request_id
requested_by

这个模型的目的，是让 orchestrator 只认这一种入口。

"""
from typing import List, Dict, Optional
from click import Option
from pydantic import BaseModel, Field

from app.shared.contracts.enums import(
    SlotType
)
from app.shared.contracts.pet import PetProfile
from app.shared.contracts.ingredient import IngredientRef

from app.domains.recipe_generation.contracts.constraints import SlotConstraint
from app.domains.recipe_generation.contracts.enums import(
    RecipeGenerationMode, MacroPreference
    )
from app.shared.contracts.nutrition import NutritionDataBundle
from app.domains.recipe_generation.contracts.recipe_spec import(
    RecipeCombinationSpec, UserDefinedRecipeSpec, PresetRecipeRef, BeginnerDiyRecipeSpec, 
)

class ConstraintProfile(BaseModel):
    protein_mode                    : MacroPreference = MacroPreference.STANDARD
    fat_mode                        : MacroPreference = MacroPreference.STANDARD
    carb_mode                       : MacroPreference = MacroPreference.STANDARD

    calorie_tolerance_pct           : Optional[float] = 0.5
    allow_supplements               : bool = True
    strict_core_positive_weight     : bool = True
    prefer_natural_calcium          : bool = False
    slot_ratio_overrides            : Dict[SlotType, SlotConstraint] = Field(default_factory=dict)


class RecipeGenerationRequest(BaseModel):
    mode                    : RecipeGenerationMode = RecipeGenerationMode.OPTIMIZE_FIXED_SET
    pet_profile             : PetProfile
    constraints             : ConstraintProfile = Field(default_factory=ConstraintProfile)

    # 三选一
    combination_spec        : Optional[RecipeCombinationSpec] = None
    user_defined_spec       : Optional[UserDefinedRecipeSpec] = None
    preset_recipe_spec      : Optional[PresetRecipeRef] = None
    beginner_diy_spec       : Optional[BeginnerDiyRecipeSpec] = None

    # preset_recipe_id        : Optional[str] = None
    supplement_toolkit_ids  : List[str] = Field(default_factory=list)
    nutrition_data          : Optional[NutritionDataBundle] = None

    request_id              : Optional[str] = None
    requested_by            : Optional[str] = None

