"""
explain/rule_engine/guidance_rules.py

Feeding guidance — derives FeedingGuidanceFlags from pet context and
the risk flags already produced by other rule modules.

watch_stool_quality triggers on ingredient realism risks (high fruit,
high liver, g/kg BW exceeded) — NOT on missing_omega3 / missing_calcium.
"""

from __future__ import annotations

import logging
from typing import List, Set

from app.domains.explain.contracts.contracts import (
    FeedingGuidanceFlag,
    NormalizedPetContext,
    RiskFlag,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# human_readable text for each guidance code
# ---------------------------------------------------------------------------

CODE_TO_READABLE: dict[str, str] = {
    "split_into_3_meals_for_small_puppy": (
        "Split daily portion into 3 meals "
        "(recommended for small/toy breed puppies)"
    ),
    "watch_stool_quality": (
        "Monitor stool quality during the first 2 weeks of this recipe"
    ),
    "monitor_body_weight_and_condition": (
        "Weigh your dog weekly and adjust portion size "
        "if body condition changes"
    ),
    "increase_calcium_support": (
        "Consider adding a calcium source "
        "such as eggshell powder or bone meal"
    ),
    "rebalance_calcium_phosphorus": (
        "Ca:P ratio needs rebalancing — "
        "consider adjusting calcium or phosphorus sources"
    ),
    "add_omega3_support": (
        "Add an omega-3 source "
        "such as salmon, sardine, or fish oil"
    ),
    "reduce_fruit_proportion": (
        "Reduce fruit proportion — "
        "current amount may be high for a small/toy puppy"
    ),
    "high_fruit_proportion": (
        "Consider reducing fruit proportion in this recipe"
    ),
}

# Life stages that trigger puppy-specific guidance
_PUPPY_LIFE_STAGES  = {"puppy"}
_SENIOR_LIFE_STAGES = {"senior"}
_WEIGHT_WATCH_STAGES = _PUPPY_LIFE_STAGES | _SENIOR_LIFE_STAGES

# Size classes that qualify for meal-splitting guidance
_SMALL_SIZE_CLASSES = {"toy", "small"}

# Risk codes that trigger stool monitoring
_STOOL_TRIGGER_CODES = {
    "high_fruit_for_small_puppy",
    "high_fruit_proportion",
    "high_liver_proportion",
    "ingredient_exceeds_g_per_kg_bw_limit",
    # extendable: "high_oil_proportion"
}

# Risk codes that trigger adjustment guidance
_CALCIUM_RISK_CODES = {"missing_calcium_source"}
_CA_P_RISK_CODES    = {"ca_p_ratio_below_target", "ca_p_ratio_above_target"}
_OMEGA3_RISK_CODES  = {"missing_omega3_support"}
_FRUIT_RISK_CODES   = {"high_fruit_for_small_puppy", "high_fruit_proportion"}


def run(
    pet_context: NormalizedPetContext,
    risk_flags: List[RiskFlag],
    flagged_nutrient_ids: Set[str],   # nutrient_ids from FlaggedNutrient list
) -> List[FeedingGuidanceFlag]:
    """
    Produces FeedingGuidanceFlags in deterministic order:
      feeding_strategy → monitoring → adjustment

    Args:
        pet_context:           from Layer 1 Normalizer
        risk_flags:            all risk flags from nutrition + structure + realism rules
        flagged_nutrient_ids:  set of nutrient_ids that appear in FlaggedNutrient
                               (used to detect calcium flagged by numeric analysis)
    """
    risk_codes = {f.code for f in risk_flags}
    flags: List[FeedingGuidanceFlag] = []

    # ── feeding_strategy ────────────────────────────────────────────────────
    if (
        pet_context.life_stage in _PUPPY_LIFE_STAGES
        and (pet_context.size_class or "").lower() in _SMALL_SIZE_CLASSES
    ):
        flags.append(_make_flag(
            "split_into_3_meals_for_small_puppy",
            "feeding_strategy",
            "high",
        ))

    # ── monitoring ──────────────────────────────────────────────────────────
    if risk_codes & _STOOL_TRIGGER_CODES:
        flags.append(_make_flag(
            "watch_stool_quality",
            "monitoring",
            "medium",
        ))

    if pet_context.life_stage in _WEIGHT_WATCH_STAGES:
        flags.append(_make_flag(
            "monitor_body_weight_and_condition",
            "monitoring",
            "medium",
        ))

    # ── adjustment ──────────────────────────────────────────────────────────
    # Calcium: triggered by structural risk OR numeric flagging
    if risk_codes & _CALCIUM_RISK_CODES or "calcium" in flagged_nutrient_ids:
        flags.append(_make_flag(
            "increase_calcium_support",
            "adjustment",
            "high",
        ))

    if risk_codes & _CA_P_RISK_CODES:
        flags.append(_make_flag(
            "rebalance_calcium_phosphorus",
            "adjustment",
            "high",
        ))

    if risk_codes & _OMEGA3_RISK_CODES:
        flags.append(_make_flag(
            "add_omega3_support",
            "adjustment",
            "medium",
        ))

    if risk_codes & _FRUIT_RISK_CODES:
        flags.append(_make_flag(
            "reduce_fruit_proportion",
            "adjustment",
            "medium",
        ))

    return flags


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def _make_flag(code: str, flag_type: str, priority: str) -> FeedingGuidanceFlag:
    readable = CODE_TO_READABLE.get(code)
    if readable is None:
        logger.warning("No human_readable text for guidance code %r", code)
    return FeedingGuidanceFlag(
        type=flag_type,
        code=code,
        priority=priority,
        human_readable=readable,
    )
