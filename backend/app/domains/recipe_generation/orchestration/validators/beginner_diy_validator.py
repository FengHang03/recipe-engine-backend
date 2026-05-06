from __future__ import annotations

from typing import List, Set

from app.domains.recipe_generation.contracts.recipe_spec import (
    BeginnerCategoryIngredientSpec,
    BeginnerCategorySpec,
    BeginnerDiyRecipeSpec,
    BeginnerSupplementSpec,
)


class BeginnerDiyValidationError(ValueError):
    def __init__(self, errors: List[str]):
        self.errors = errors
        message = "Beginner DIY spec validation failed:\n- " + "\n- ".join(errors)
        super().__init__(message)


def validate_beginner_diy_spec(
    spec: BeginnerDiyRecipeSpec,
    ratio_tolerance: float = 0.5,
    internal_ratio_tolerance: float = 0.5,
) -> None:
    """
    Validate BeginnerDiyRecipeSpec.

    Rules:
    1. target_energy_kcal, if provided, must be > 0
    2. effective category ratios (active + non-empty) must sum to ~100
    3. each effective category must have ratio in [0, 100]
    4. internal ratios in each effective category must sum to ~100
    5. ingredient ids must not repeat across effective categories
    6. supplement grams must be >= 0
    7. supplement ids must not repeat
    8. at least one effective category must exist
    """
    errors: List[str] = []

    if spec.target_energy_kcal is not None and spec.target_energy_kcal <= 0:
        errors.append("target_energy_kcal must be greater than 0")

    _validate_categories(
        categories=spec.categories,
        errors=errors,
        ratio_tolerance=ratio_tolerance,
        internal_ratio_tolerance=internal_ratio_tolerance,
    )

    _validate_supplements(
        supplements=spec.supplements,
        errors=errors,
    )

    if errors:
        raise BeginnerDiyValidationError(errors)


def _validate_categories(
    categories: List[BeginnerCategorySpec],
    errors: List[str],
    ratio_tolerance: float,
    internal_ratio_tolerance: float,
) -> None:
    effective_categories = [c for c in categories if c.is_active and len(c.ingredients) > 0]

    if not effective_categories:
        errors.append(
            "Beginner DIY spec must contain at least one active category with ingredients."
        )
        return

    effective_ratio_sum = 0.0
    seen_ingredient_ids: Set[str] = set()

    for category in effective_categories:
        if not category.category_key:
            errors.append("category_key cannot be empty")

        if category.category_ratio < 0 or category.category_ratio > 100:
            errors.append(
                f"category '{category.category_key}' ratio must be within [0, 100], got {category.category_ratio}"
            )

        effective_ratio_sum += float(category.category_ratio)

        _validate_category_ingredients(
            category=category,
            errors=errors,
            seen_ingredient_ids=seen_ingredient_ids,
            internal_ratio_tolerance=internal_ratio_tolerance,
        )

    for category in categories:
        if not category.is_active and category.category_ratio != 0:
            errors.append(
                f"inactive category '{category.category_key}' should have category_ratio=0, got {category.category_ratio}"
            )


def _validate_category_ingredients(
    category: BeginnerCategorySpec,
    errors: List[str],
    seen_ingredient_ids: Set[str],
    internal_ratio_tolerance: float,
) -> None:
    internal_sum = 0.0
    local_seen: Set[str] = set()

    for item in category.ingredients:
        _validate_category_ingredient_item(
            category_key=category.category_key,
            item=item,
            errors=errors,
            seen_ingredient_ids=seen_ingredient_ids,
            local_seen=local_seen,
        )
        internal_sum += float(item.internal_ratio)

    if abs(internal_sum - 100.0) > internal_ratio_tolerance:
        errors.append(
            f"internal ratios in category '{category.category_key}' must sum to 100±{internal_ratio_tolerance}, got {round(internal_sum, 4)}"
        )


def _validate_category_ingredient_item(
    category_key: str,
    item: BeginnerCategoryIngredientSpec,
    errors: List[str],
    seen_ingredient_ids: Set[str],
    local_seen: Set[str],
) -> None:
    ingredient_id = item.ingredient.ingredient_id

    if not ingredient_id:
        errors.append(f"category '{category_key}' contains an ingredient with empty ingredient_id")
        return

    if item.internal_ratio < 0 or item.internal_ratio > 100:
        errors.append(
            f"ingredient '{ingredient_id}' in category '{category_key}' must have internal_ratio within [0, 100], got {item.internal_ratio}"
        )

    if ingredient_id in local_seen:
        errors.append(
            f"duplicate ingredient '{ingredient_id}' found inside category '{category_key}'"
        )
    else:
        local_seen.add(ingredient_id)

    if ingredient_id in seen_ingredient_ids:
        errors.append(
            f"ingredient '{ingredient_id}' appears in multiple effective categories"
        )
    else:
        seen_ingredient_ids.add(ingredient_id)


def _validate_supplements(
    supplements: List[BeginnerSupplementSpec],
    errors: List[str],
) -> None:
    seen_supplement_ids: Set[str] = set()

    for supplement in supplements:
        ingredient_id = supplement.ingredient.ingredient_id

        if not ingredient_id:
            errors.append("supplement contains an empty ingredient_id")
            continue

        if supplement.grams < 0:
            errors.append(
                f"supplement '{ingredient_id}' grams must be >= 0, got {supplement.grams}"
            )

        if ingredient_id in seen_supplement_ids:
            errors.append(
                f"duplicate supplement '{ingredient_id}' found in supplements"
            )
        else:
            seen_supplement_ids.add(ingredient_id)

            