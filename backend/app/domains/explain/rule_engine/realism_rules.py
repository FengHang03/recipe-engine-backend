"""
explain/rule_engine/realism_rules.py

Realism judgment — checks per-ingredient amounts against realistic limits.
Uses coarse category and grams_per_kg_bw from DerivedMetrics.

Note: pct_of_recipe > max_pct_kcal rule is SKIPPED this sprint.
      Placeholder is left for next sprint activation.

Fruit detection:
  EnrichedIngredient.food_group is the COARSE category produced by
  derived_metrics._to_coarse_category().
  Blueberries → "fruit" (via _FRUIT_BY_NAME regex in derived_metrics).
  Beet / Eggplant → "vegetable" (correctly excluded from fruit rules).
"""

from __future__ import annotations

import logging
from typing import List

from app.domains.explain.contracts.contracts import (
    DerivedMetrics,
    EnrichedIngredient,
    NormalizedPetContext,
    RiskFlag,
)

logger = logging.getLogger(__name__)

# Coarse categories (post-mapping from derived_metrics)
_COARSE_FRUIT  = "fruit"

# food_subgroup value for liver (from DB ingredients table, via enrichment layer)
_SUBGROUP_ORGAN_LIVER = "organ_liver"

# Thresholds
_FRUIT_PCT_THRESHOLD_PUPPY   = 10.0  # pct_of_recipe > 10% — small/toy puppy
_FRUIT_PCT_THRESHOLD_GENERAL = 15.0  # pct_of_recipe > 15% — any life stage / size
_LIVER_PCT_THRESHOLD         = 5.0   # pct_of_recipe > 5%

# Life stages that trigger puppy-specific rules
_PUPPY_LIFE_STAGES = {"puppy"}

# Size classes that qualify for the stricter puppy fruit rule
_SMALL_SIZE_CLASSES = {"toy", "small"}


def run(
    ingredient_metrics: List[EnrichedIngredient],
    pet_context: NormalizedPetContext,
) -> List[RiskFlag]:
    """
    Evaluates per-ingredient realism and returns ingredient_amount RiskFlags.

    Fruit rules (mutually exclusive, stronger wins):
      1. high_fruit_for_small_puppy — DOG_PUPPY + size in [toy, small] + fruit > 10%
         If this fires, high_fruit_proportion is suppressed for the same recipe.
      2. high_fruit_proportion      — any life stage/size + fruit > 15%
         Only fires if high_fruit_for_small_puppy did NOT fire.

    Liver rule:
      Uses food_subgroup == "organ_liver" for precise detection (not coarse "organ").

    g/kg BW rule:
      Handled separately via check_g_per_kg_bw() called by engine.py.
    """
    flags: List[RiskFlag] = []
    seen_codes: set[str] = set()

    is_puppy       = pet_context.life_stage.lower() in _PUPPY_LIFE_STAGES
    is_small_puppy = (
        is_puppy
        and (pet_context.size_class or "").lower() in _SMALL_SIZE_CLASSES
    )

    for m in ingredient_metrics:
        coarse    = (m.food_group or "").lower()
        subgroup  = (m.food_subgroup or "").lower()

        # ── Fruit proportion ─────────────────────────────────────────────────
        if coarse == _COARSE_FRUIT:
            if (
                is_small_puppy
                and m.pct_of_recipe >= _FRUIT_PCT_THRESHOLD_PUPPY
                and "high_fruit_for_small_puppy" not in seen_codes
            ):
                # Stronger, more specific rule fires → suppress general rule
                flags.append(RiskFlag(
                    type="ingredient_amount",
                    severity="medium",
                    code="high_fruit_for_small_puppy",
                    priority=3,
                    recommended_action_code="reduce_fruit_proportion",
                ))
                seen_codes.add("high_fruit_for_small_puppy")
                seen_codes.add("high_fruit_proportion")   # suppress general

            elif (
                "high_fruit_proportion" not in seen_codes
                and "high_fruit_for_small_puppy" not in seen_codes
                and m.pct_of_recipe > _FRUIT_PCT_THRESHOLD_GENERAL
            ):
                # General rule — fires for any life stage / size
                flags.append(RiskFlag(
                    type="ingredient_amount",
                    severity="medium",
                    code="high_fruit_proportion",
                    priority=4,
                    recommended_action_code="reduce_fruit_proportion",
                ))
                seen_codes.add("high_fruit_proportion")

        # ── Liver proportion (food_subgroup-based, precise) ──────────────────
        if (
            subgroup == _SUBGROUP_ORGAN_LIVER
            and m.pct_of_recipe > _LIVER_PCT_THRESHOLD
            and "high_liver_proportion" not in seen_codes
        ):
            flags.append(RiskFlag(
                type="ingredient_amount",
                severity="medium",
                code="high_liver_proportion",
                priority=3,
                recommended_action_code=None,
            ))
            seen_codes.add("high_liver_proportion")

    return flags


def check_g_per_kg_bw(
    ingredient_metrics: List[EnrichedIngredient],
    enrich_map: dict[str, float],   # ingredient_id → max_g_per_kg_bw
) -> List[RiskFlag]:
    """
    Called by engine.py with the max_g_per_kg_bw values extracted from
    EnrichedIngredient list.

    enrich_map: {ingredient_id: max_g_per_kg_bw}
    Only ingredients where enrich_available=True and max_g_per_kg_bw is not None
    should appear in enrich_map.
    """
    flags: List[RiskFlag] = []
    seen_codes: set[str] = set()

    for m in ingredient_metrics:
        limit = enrich_map.get(m.ingredient_id)
        if limit is None:
            continue
        if m.grams_per_kg_bw > limit and "ingredient_exceeds_g_per_kg_bw_limit" not in seen_codes:
            logger.debug(
                "%r: grams_per_kg_bw=%.2f exceeds limit=%.2f",
                m.ingredient_name, m.grams_per_kg_bw, limit,
            )
            flags.append(RiskFlag(
                type="ingredient_amount",
                severity="medium",
                code="ingredient_exceeds_g_per_kg_bw_limit",
                priority=3,
                recommended_action_code=None,
            ))
            seen_codes.add("ingredient_exceeds_g_per_kg_bw_limit")

    return flags

    # TODO (next sprint): pct_of_recipe > max_pct_kcal rule
    # Activate once percentage field is unified across recipe generation pipeline.
