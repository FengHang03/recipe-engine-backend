from typing import Any, List, Dict, Optional
from pydantic import BaseModel, Field

from app.shared.contracts.enums import(
    FoodGroup, FoodSubgroup, SlotType,
)
from app.shared.contracts.nutrition import NutrientAnalysis
from app.domains.recipe_generation.contracts.enums import(
    SolveStatus, InfeasibilityReason, RecipeGenerationMode
)
# from app.domains.recipe_generation.contracts.results import(
#     InfeasibilityDiagnostic
# )


# ---------------------------------------------------------------------------
# Infeasibility diagnostic
# ---------------------------------------------------------------------------

class InfeasibilityDiagnostic(BaseModel):
    reason                  : InfeasibilityReason
    conflicting_nutrients   : List[str] = Field(default_factory=list)
    bottleneck_constraint   : Optional[str] = None
    suggestion              : Optional[str] = None
    details                 : Dict[str, Any] = Field(default_factory=dict)


# ---------------------------------------------------------------------------
# Basic results
# ---------------------------------------------------------------------------

class WeightedIngredient(BaseModel):
    ingredient_id                   : str
    ingredient_name                 : str
    short_name                      : Optional[str] = None
    slot_type                       : Optional[SlotType] = None
    weight_grams                    : Optional[float] = None
    pct_of_recipe                   : Optional[float] = None
    is_supplement                   : bool = False
    was_user_locked                 : bool = False

    display_amount                  : Optional[float] = None
    display_unit                    : Optional[str] = None
    display_amount_text             : Optional[str] = None

# ---------------------------------------------------------------------------
# Unified Generation of results
# ---------------------------------------------------------------------------

class RecipeGenerationResult(BaseModel):
    mode                            : RecipeGenerationMode = RecipeGenerationMode.OPTIMIZE_FIXED_SET
    status                          : SolveStatus

    source_type                     : Optional[str] = None
    recipe_id                       : Optional[str] = None
    source_recipe_id                : Optional[str] = None

    rank                            : Optional[int] = None
    solve_time_seconds              : Optional[float] = None
    total_weight_grams              : Optional[float] = None
    weights                         : List[WeightedIngredient] = Field(default_factory=list)
    nutrient_analysis               : List[NutrientAnalysis] = Field(default_factory=list)

    objective_value                 : Optional[float] = None
    penalty_breakdown               : Dict[str, float] | None = None
    infeasibility_diagnostic        : InfeasibilityDiagnostic | None = None    

    used_supplements                : List[str] = Field(default_factory=list)
    warnings                        : List[str] = Field(default_factory=list)

    # 结果归档与 explain 复用
    explanation_payload             : Optional[Dict[str, Any]] = None
    debug_meta                      : Dict[str, Any] = Field(default_factory=dict)
