"""
explain/normalizer.py
Layer 1 — ExplainRequestNormalizer

Responsibility: clean and unify incoming fields only.
No business logic, no rule judgment, no DB access.
"""

from __future__ import annotations

import logging
from typing import List, Optional

from app.shared.contracts.enums import NutrientID
from app.shared.contracts.nutrition import NutrientAnalysis
from app.domains.explain.contracts.contracts import (
    ExplainRecipeRequest,
    NormalizedExplainInput,
    NormalizedPetContext,
    NormalizedRecipeContext,
    NormalizedIngredient,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Enum normalization maps
# ---------------------------------------------------------------------------

_LIFE_STAGE_MAP: dict[str, str] = {
    # LifeStage enum values (what the adapter extracts via .value)
    "puppy":       "puppy",
    "adult":       "adult",
    "senior":      "senior",
    # Legacy / frontend raw string forms
    "dog_puppy":   "puppy",
    "dog_adult":   "adult",
    "dog_senior":  "senior",
}

_VALID_LIFE_STAGES = {"puppy", "adult", "senior"}

_DERIVED_NUTRIENT_ID_ALIASES = {
    "ca_p_ratio": "CA_P_RATIO",
    "ca:p_ratio": "CA_P_RATIO",
    "calcium_phosphorus_ratio": "CA_P_RATIO",
    "calcium:phosphorus_ratio": "CA_P_RATIO",

    "epa_dha_sum": "EPA_DHA_SUM",
    "epa+dha": "EPA_DHA_SUM",
    "epa_dha": "EPA_DHA_SUM",

    "n6_n3_ratio": "N6_N3_RATIO",
    "n3_n6_ratio": "N6_N3_RATIO",  # 如果你最终决定叫 N6_N3_RATIO，这里做兼容
    "omega6_omega3_ratio": "N6_N3_RATIO",
    "omega_6_omega_3_ratio": "N6_N3_RATIO",
}


def _normalize_life_stage(raw: str | None) -> str:
    if raw is None:
        logger.warning("life_stage is None — defaulting to raw passthrough 'UNKNOWN'")
        return "UNKNOWN"

    raw = str(raw).strip()
    normalized = _LIFE_STAGE_MAP.get(raw.lower())
    if normalized is not None:
        return normalized

    upper = raw.upper()
    if upper in _VALID_LIFE_STAGES:
        return upper

    logger.warning("Unknown life_stage value %r — passing through as-is", raw)
    return raw


def _normalize_species(raw: str | None) -> str:
    if raw is None:
        return "dog"
    return str(raw).strip().lower()


def _normalize_nutrient_id(raw):
    if raw is None:
        return ""

    # 1. NutrientID enum -> 保留为 int enum 或 int
    if isinstance(raw, NutrientID):
        return raw

    # 2. int -> 尝试转 NutrientID；不认识就保留 int
    if isinstance(raw, int):
        try:
            return NutrientID(raw)
        except ValueError:
            return raw

    # 3. numeric string -> 尝试转 NutrientID；不认识就保留 int
    text = str(raw).strip()
    if text.isdigit():
        value = int(text)
        try:
            return NutrientID(value)
        except ValueError:
            return value

    # 4. derived metric string -> 统一成大写 canonical key
    key = text.strip().lower()
    if key in _DERIVED_NUTRIENT_ID_ALIASES:
        return _DERIVED_NUTRIENT_ID_ALIASES[key]

    # 5. 已经是 canonical derived key
    upper = text.upper()
    if upper in {"CA_P_RATIO", "EPA_DHA_SUM", "N6_N3_RATIO"}:
        return upper

    # 6. 其他未知字符串，保留原值或 upper 都可以
    return text


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def normalize(request: ExplainRecipeRequest) -> NormalizedExplainInput:
    """
    Convert ExplainRecipeRequest → NormalizedExplainInput.

    Field renames:
      weight_kg      → body_weight_kg
      daily_calories_kcal  → daily_calories_kcal
      recipe_id   → recipe_id

    Enum unification:
      species          → lowercase  "dog"
      life_stage       → uppercase  "DOG_PUPPY" / "DOG_ADULT" / "DOG_SENIOR"
      nutrient_id      → lowercase

    Null safety:
      health_conditions / allergies → [] if None
      all Optional fields           → kept as None, never filled with defaults
    """
    if isinstance(request, dict):
        request = ExplainRecipeRequest(**request)
        
    pet    = request.pet
    recipe = request.recipe

    return NormalizedExplainInput(
        pet_context=_normalize_pet_context(pet),
        recipe_context=_normalize_recipe_context(recipe),
        ingredients=_normalize_ingredients(recipe),
        nutrient_analysis=_normalize_nutrient_analysis(recipe),
    )


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _normalize_pet_context(pet) -> NormalizedPetContext:
    try:
        return NormalizedPetContext(
            species=_normalize_species(getattr(pet, "species", None)),
            life_stage=_normalize_life_stage(_normalize_optional_enum(getattr(pet, "life_stage", None))),
            age_months=(
                int(pet.age_months) if getattr(pet, "age_months", None) is not None else None
            ),
            body_weight_kg=float(getattr(pet, "weight_kg", 0.0) or 0.0),
            size_class=_normalize_optional_enum(getattr(pet, "size_class", None)),
            daily_calories_kcal=float(getattr(pet, "daily_calories_kcal", 0.0) or 0.0),
            activity_level=_normalize_optional_enum(getattr(pet, "activity_level", None)),
            sterilization_status=_normalize_optional_enum(getattr(pet, "sterilization_status", None)),
            reproductive_stage=_normalize_optional_enum(getattr(pet, "reproductive_stage", None)),
            health_conditions=list(getattr(pet, "health_conditions", None) or []),
            allergies=list(getattr(pet, "allergies", None) or []),
        )
    except Exception as exc:
        logger.warning(
            "Pet context normalization error: %s — falling back to best-effort values", exc
        )
        # Best-effort: preserve every field we can read; never silently drop
        # size_class is critical for small-puppy rules
        return NormalizedPetContext(
            species=_normalize_species(getattr(pet, "species", "dog")),
            life_stage=_normalize_life_stage(getattr(pet, "life_stage", "DOG_ADULT")),
            age_months=int(getattr(pet, "age_months", 0)),
            body_weight_kg=float(getattr(pet, "weight_kg", 0.0)),
            size_class=getattr(pet, "size_class", None),
            daily_calories_kcal=float(getattr(pet, "daily_calories_kcal", 0.0)),
            activity_level=getattr(pet, "activity_level", None),
            sterilization_status=getattr(pet, "sterilization_status", None),
            reproductive_stage=getattr(pet, "reproductive_stage", None),
            health_conditions=list(getattr(pet, "health_conditions", None) or []),
            allergies=list(getattr(pet, "allergies", None) or []),
        )


def _normalize_recipe_context(recipe) -> NormalizedRecipeContext:
    return NormalizedRecipeContext(
        recipe_id=recipe.recipe_id or "",
        rank=recipe.rank,
        total_weight_grams=(
            float(recipe.total_weight_grams)
            if recipe.total_weight_grams is not None
            else None
        ),
        used_supplements=list(recipe.used_supplements or []),
    )


def _normalize_ingredients(recipe) -> List[NormalizedIngredient]:
    result: List[NormalizedIngredient] = []
    for w in recipe.weights:
        try:
            result.append(
                NormalizedIngredient(
                    ingredient_id=w.ingredient_id,
                    ingredient_name=w.ingredient_name.strip(),
                    weight_grams=float(w.weight_grams),
                    pct_of_recipe=(float(w.pct_of_recipe) if w.pct_of_recipe is not None else None),
                    is_supplement=bool(w.is_supplement),
                    slot_type=(
                        str(w.slot_type.value)
                        if getattr(w, "slot_type", None) is not None and hasattr(w.slot_type, "value")
                        else (str(w.slot_type) if getattr(w, "slot_type", None) is not None else None)
                    ),
                    display_amount_text=getattr(w, "display_amount_text", None),
                )
            )
        except Exception as exc:
            logger.warning(
                "Ingredient normalization error for %r: %s — skipping this ingredient",
                getattr(w, "ingredient_name", "unknown"),
                exc,
            )
    return result


def _normalize_nutrient_analysis(recipe) -> List[NutrientAnalysis]:
    result: List[NutrientAnalysis] = []
    for n in recipe.nutrient_analysis:
        try:
            result.append(
                n.model_copy(update={
                    "nutrient_id": _normalize_nutrient_id(n.nutrient_id),
                    "nutrient_name": (n.nutrient_name or "").strip(),
                })
            )
        except Exception as exc:
            logger.warning(
                "NutrientAnalysis normalization error for %r: %s — skipping this nutrient",
                getattr(n, "nutrient_id", "unknown"),
                exc,
            )
    return result

# ------------------------------------------------------------------------------------------
# helper
# ------------------------------------------------------------------------------------------

def _normalize_optional_enum(raw) -> Optional[str]:
    if raw is None:
        return None
    if hasattr(raw, "value"):
        return str(raw.value)
    return str(raw)
