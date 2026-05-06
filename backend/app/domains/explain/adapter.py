from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from app.shared.contracts.pet import PetProfile
from app.domains.recipe_generation.contracts.results import RecipeGenerationResult
from app.domains.explain.contracts.contracts import ExplainRecipeRequest


class ExplainOptionsPayload(BaseModel):
    language: str = "en"
    include_debug: bool = False


class ExplainPetPayload(BaseModel):
    species: str
    breed: Optional[str] = None
    age_months: Optional[int] = None
    weight_kg: float
    life_stage: str
    size_class: Optional[str] = None
    activity_level: Optional[str] = None
    sterilization_status: Optional[str] = None
    reproductive_stage: Optional[str] = None
    daily_calories_kcal: float
    health_conditions: List[str] | Dict[str, bool] = Field(default_factory=list)
    allergies: List[str] | Dict[str, bool] = Field(default_factory=list)


class ExplainRecipeApiRequest(BaseModel):
    pet: ExplainPetPayload
    recipe: Dict[str, Any]
    options: Optional[ExplainOptionsPayload] = None


def _normalize_flag_list(value: List[str] | Dict[str, bool] | None) -> List[str]:
    if value is None:
        return []

    if isinstance(value, list):
        return [str(v).strip() for v in value if str(v).strip()]

    if isinstance(value, dict):
        return [str(k).strip() for k, enabled in value.items() if enabled and str(k).strip()]

    return []

def _adapt_recipe_payload(recipe_payload: Dict[str, Any]) -> RecipeGenerationResult:
    data = dict(recipe_payload)

    data.setdefault("mode", "beginner_diy_preview")
    data.setdefault("status", "FEASIBLE")
    data.setdefault("weights", [])
    data.setdefault("nutrient_analysis", [])
    data.setdefault("used_supplements", [])
    data.setdefault("warnings", [])
    data.setdefault("debug_meta", {})

    for w in data["weights"]:
        if "ingredient_id" in w:
            w["ingredient_id"] = str(w["ingredient_id"])
        if "pct_of_recipe" not in w and "percentage" in w:
            w["pct_of_recipe"] = w.get("percentage")
        w.setdefault("is_supplement", False)
        w.setdefault("was_user_locked", False)

    return RecipeGenerationResult.model_validate(data)


def adapt_to_explain_request(api_req: ExplainRecipeApiRequest) -> ExplainRecipeRequest:
    pet_payload = api_req.pet

    pet = PetProfile(
        species=pet_payload.species,
        breed=pet_payload.breed,
        age_months=pet_payload.age_months,
        weight_kg=pet_payload.weight_kg,
        life_stage=pet_payload.life_stage or "adult",
        size_class=pet_payload.size_class or 'medium',
        activity_level=pet_payload.activity_level or "moderate",
        sterilization_status=pet_payload.sterilization_status or "neutered",
        reproductive_stage=pet_payload.reproductive_stage or "none",
        daily_calories_kcal=pet_payload.daily_calories_kcal,
        health_conditions=_normalize_flag_list(pet_payload.health_conditions),
        allergies=_normalize_flag_list(pet_payload.allergies),
    )

    recipe = _adapt_recipe_payload(api_req.recipe)


    return ExplainRecipeRequest(
        pet=pet,
        recipe=recipe,
    )