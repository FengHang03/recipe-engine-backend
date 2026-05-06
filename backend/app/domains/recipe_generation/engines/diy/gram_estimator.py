from __future__ import annotations

from typing import Dict, Iterable, List, Optional, Sequence

from app.shared.contracts.ingredient import IngredientProfile
from app.domains.recipe_generation.contracts.results import WeightedIngredient
from app.domains.recipe_generation.contracts.recipe_spec import BeginnerSupplementSpec
from app.domains.recipe_generation.engines.diy.ratio_expander import ExpandedRatioItem


class GramEstimationError(ValueError):
    pass


def estimate_weighted_ingredients_from_expanded_ratios(
    expanded_items: Sequence[ExpandedRatioItem],
    ingredient_profiles: Dict[str, IngredientProfile],
    target_energy_kcal: float,
) -> List[WeightedIngredient]:
    """
    Estimate recipe grams from fixed weight ratios + target calories.

    Interpretation:
    - final_ratio is treated as recipe weight percentage (not energy percentage)
    - total recipe weight is inferred from target calories and weighted-average kcal/g

    Steps:
    1. Convert each final_ratio into fraction of total weight
    2. Compute weighted-average kcal/g for the whole recipe
    3. total_weight_g = target_energy_kcal / avg_kcal_per_g
    4. ingredient_weight_g = total_weight_g * fraction

    Returns:
        List[WeightedIngredient] for non-supplement ingredients only.
    """
    if target_energy_kcal <= 0:
        raise GramEstimationError(f"target_energy_kcal must be > 0, got {target_energy_kcal}")

    if not expanded_items:
        return []

    ratio_sum = sum(float(item.final_ratio) for item in expanded_items)
    if ratio_sum <= 0:
        raise GramEstimationError("expanded ratio sum must be > 0")

    avg_kcal_per_g = _compute_weighted_average_kcal_per_g(
        expanded_items=expanded_items,
        ingredient_profiles=ingredient_profiles,
    )
    if avg_kcal_per_g <= 0:
        raise GramEstimationError("weighted average kcal/g must be > 0")

    total_recipe_weight_g = float(target_energy_kcal) / avg_kcal_per_g

    weights: List[WeightedIngredient] = []
    for item in expanded_items:
        ingredient_id = item.ingredient.ingredient_id
        fraction = float(item.final_ratio) / ratio_sum
        weight_g = total_recipe_weight_g * fraction

        weights.append(
            WeightedIngredient(
                ingredient_id=ingredient_id,
                ingredient_name=_resolve_ingredient_name(item.ingredient, ingredient_profiles),
                short_name=_resolve_short_name(item.ingredient, ingredient_profiles),
                slot_type=item.ingredient.default_slot,
                weight_grams=round(weight_g, 6),
                pct_of_recipe=round(float(item.final_ratio), 6),
                is_supplement=False,
                was_user_locked=False,
            )
        )

    return weights


def convert_supplements_to_weighted_ingredients(
    supplements: Sequence[BeginnerSupplementSpec],
    ingredient_profiles: Dict[str, IngredientProfile],
) -> List[WeightedIngredient]:
    """
    Convert grams-based supplements into WeightedIngredient objects.

    pct_of_recipe is left as 0 for now and should be recomputed after supplements
    are merged with the rest of the recipe.
    """
    result: List[WeightedIngredient] = []

    for supplement in supplements:
        ingredient = supplement.ingredient
        result.append(
            WeightedIngredient(
                ingredient_id=ingredient.ingredient_id,
                ingredient_name=_resolve_ingredient_name(ingredient, ingredient_profiles),
                short_name=_resolve_short_name(ingredient, ingredient_profiles),
                slot_type=ingredient.default_slot,
                weight_grams=round(float(supplement.grams), 6),
                pct_of_recipe=0.0,
                is_supplement=True,
                was_user_locked=True,
            )
        )

    return result


def recompute_pct_of_recipe_by_weight(
    weights: Iterable[WeightedIngredient],
) -> List[WeightedIngredient]:
    """
    Recompute pct_of_recipe using total recipe weight.

    This is useful after ratio-based ingredients and grams-based supplements
    are merged together.
    """
    weight_list = list(weights)
    total_weight = sum(float(w.weight_grams) for w in weight_list if w.weight_grams is not None)

    if total_weight <= 0:
        return weight_list

    recomputed: List[WeightedIngredient] = []
    for item in weight_list:
        pct = (float(item.weight_grams) / total_weight) * 100.0
        recomputed.append(
            WeightedIngredient(
                ingredient_id=item.ingredient_id,
                ingredient_name=item.ingredient_name,
                short_name=item.short_name,
                slot_type=item.slot_type,
                weight_grams=item.weight_grams,
                pct_of_recipe=round(pct, 6),
                is_supplement=item.is_supplement,
                was_user_locked=item.was_user_locked,
            )
        )
    return recomputed


def estimate_total_recipe_weight_grams(
    expanded_items: Sequence[ExpandedRatioItem],
    ingredient_profiles: Dict[str, IngredientProfile],
    target_energy_kcal: float,
) -> float:
    """
    Convenience helper if caller only wants total weight.
    """
    if target_energy_kcal <= 0:
        raise GramEstimationError(f"target_energy_kcal must be > 0, got {target_energy_kcal}")

    avg_kcal_per_g = _compute_weighted_average_kcal_per_g(
        expanded_items=expanded_items,
        ingredient_profiles=ingredient_profiles,
    )
    if avg_kcal_per_g <= 0:
        raise GramEstimationError("weighted average kcal/g must be > 0")

    return float(target_energy_kcal) / avg_kcal_per_g


def _compute_weighted_average_kcal_per_g(
    expanded_items: Sequence[ExpandedRatioItem],
    ingredient_profiles: Dict[str, IngredientProfile],
) -> float:
    ratio_sum = sum(float(item.final_ratio) for item in expanded_items)
    if ratio_sum <= 0:
        raise GramEstimationError("expanded ratio sum must be > 0")

    avg_kcal_per_g = 0.0

    for item in expanded_items:
        ingredient_id = item.ingredient.ingredient_id
        profile = ingredient_profiles.get(ingredient_id)
        if profile is None:
            raise GramEstimationError(
                f"missing IngredientProfile for ingredient_id='{ingredient_id}'"
            )

        if profile.energy_per_100g is None:
            raise GramEstimationError(
                f"ingredient '{ingredient_id}' is missing energy_per_100g"
            )

        kcal_per_g = float(profile.energy_per_100g) / 100.0
        if kcal_per_g < 0:
            raise GramEstimationError(
                f"ingredient '{ingredient_id}' has invalid negative energy_per_100g={profile.energy_per_100g}"
            )

        fraction = float(item.final_ratio) / ratio_sum
        avg_kcal_per_g += fraction * kcal_per_g

    return avg_kcal_per_g


def _resolve_short_name(
    ingredient_ref,
    ingredient_profiles: Dict[str, IngredientProfile],
) -> Optional[str]:
    if getattr(ingredient_ref, "short_name", None):
        return str(ingredient_ref.short_name)
    profile = ingredient_profiles.get(ingredient_ref.ingredient_id)
    if profile is not None and getattr(profile, "short_name", None):
        return str(profile.short_name)
    return None


def _resolve_ingredient_name(
    ingredient_ref,
    ingredient_profiles: Dict[str, IngredientProfile],
) -> str:
    if getattr(ingredient_ref, "description", None):
        return str(ingredient_ref.description)

    profile = ingredient_profiles.get(ingredient_ref.ingredient_id)
    if profile is not None and getattr(profile, "description", None):
        return str(profile.description)

    if profile is not None and getattr(profile, "short_name", None):
        return str(profile.short_name)

    return ingredient_ref.ingredient_id
    