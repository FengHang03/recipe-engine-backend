from __future__ import annotations

from typing import Any, Dict

from app.domains.recipe_generation.contracts.results import RecipeGenerationResult
from app.shared.contracts.pet import PetProfile


class ExplainPayloadBuilder:
    """Build a stable payload for the explain domain from generation results.

    This builder intentionally produces a business-shaped dict so the explain
    layer can evolve independently from recipe_generation internals.
    """

    def build(self, pet_profile: PetProfile, result: RecipeGenerationResult) -> Dict[str, Any]:
        return {
            "pet": {
                "species": pet_profile.species.value if hasattr(pet_profile.species, "value") else pet_profile.species,
                "age_months": pet_profile.age_months,
                "weight_kg": pet_profile.weight_kg,
                "life_stage": pet_profile.life_stage.value if hasattr(pet_profile.life_stage, "value") else pet_profile.life_stage,
                "size_class": pet_profile.size_class,
                "activity_level": (
                    pet_profile.activity_level.value
                    if getattr(pet_profile, "activity_level", None) is not None and hasattr(pet_profile.activity_level, "value")
                    else pet_profile.activity_level
                ),
                "daily_calories_kcal": pet_profile.daily_calories_kcal,
                "sterilization_status": (
                    pet_profile.sterilization_status.value
                    if getattr(pet_profile, "sterilization_status", None) is not None and hasattr(pet_profile.sterilization_status, "value")
                    else pet_profile.sterilization_status
                ),
                "reproductive_stage": (
                    pet_profile.reproductive_stage.value
                    if getattr(pet_profile, "reproductive_stage", None) is not None and hasattr(pet_profile.reproductive_stage, "value")
                    else pet_profile.reproductive_stage
                ),
                "health_conditions": list(getattr(pet_profile, "health_conditions", []) or []),
                "allergies": list(getattr(pet_profile, "allergies", []) or []),
            },
            "recipe": {
                "recipe_id": result.recipe_id,
                "source_recipe_id": result.source_recipe_id,
                "mode": result.mode.value if hasattr(result.mode, "value") else result.mode,
                "rank": result.rank,
                "total_weight_grams": result.total_weight_grams,
                "objective_value": result.objective_value,
                "used_supplements": result.used_supplements,
                "weights": [
                    {
                        "ingredient_id": item.ingredient_id,
                        "ingredient_name": item.ingredient_name,
                        "weight_grams": item.weight_grams,
                        "pct_of_recipe": item.pct_of_recipe,
                        "is_supplement": item.is_supplement,
                        "slot_type": item.slot_type.value if item.slot_type is not None and hasattr(item.slot_type, "value") else item.slot_type,
                    }
                    for item in result.weights
                ],
                "nutrient_analysis": [item.model_dump() for item in result.nutrient_analysis],
                "warnings": result.warnings,
            },
        }
