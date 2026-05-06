from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, List

from app.shared.contracts.ingredient import IngredientRef
from app.domains.recipe_generation.contracts.recipe_spec import BeginnerDiyRecipeSpec


@dataclass(frozen=True)
class ExpandedRatioItem:
    ingredient: IngredientRef
    category_key: str
    category_ratio: float
    internal_ratio: float
    final_ratio: float  # final recipe weight ratio, 0~100


def expand_beginner_category_ratios(
    spec: BeginnerDiyRecipeSpec,
) -> List[ExpandedRatioItem]:
    """
    Expand effective category ratios into final ingredient ratios.

    Effective category:
      - is_active == True
      - contains at least one ingredient

    Behavior:
      - categories that are active but empty are skipped
      - effective category ratios are re-normalized to 100 before expansion

    Example:
      main_protein = 50 (has ingredients)
      carb         = 20 (has ingredients)
      organ        = 5  (empty -> skipped)

    effective sum = 70

    normalized:
      main_protein = 71.4286
      carb         = 28.5714
    """
    expanded: List[ExpandedRatioItem] = []

    effective_categories = [
        category
        for category in spec.categories
        if category.is_active and len(category.ingredients) > 0
    ]

    effective_ratio_sum = sum(float(category.category_ratio) for category in effective_categories)
    if effective_ratio_sum <= 0:
        return expanded

    for category in effective_categories:
        normalized_category_ratio = (
            float(category.category_ratio) / float(effective_ratio_sum)
        ) * 100.0

        for item in category.ingredients:
            final_ratio = (
                float(normalized_category_ratio) * float(item.internal_ratio)
            ) / 100.0

            expanded.append(
                ExpandedRatioItem(
                    ingredient=item.ingredient,
                    category_key=category.category_key,
                    category_ratio=float(normalized_category_ratio),
                    internal_ratio=float(item.internal_ratio),
                    final_ratio=final_ratio,
                )
            )

    return expanded


def compute_final_ratio_map(
    expanded_items: Iterable[ExpandedRatioItem],
) -> Dict[str, float]:
    """
    Collapse expanded ratio items into:
      ingredient_id -> final_ratio

    Usually Beginner validator already prevents duplicates across categories,
    but this function is written defensively and will aggregate if duplicates appear.
    """
    ratio_map: Dict[str, float] = {}

    for item in expanded_items:
        ingredient_id = item.ingredient.ingredient_id
        ratio_map[ingredient_id] = ratio_map.get(ingredient_id, 0.0) + float(item.final_ratio)

    return ratio_map


def compute_final_ratio_sum(
    expanded_items: Iterable[ExpandedRatioItem],
) -> float:
    return sum(float(item.final_ratio) for item in expanded_items)

    