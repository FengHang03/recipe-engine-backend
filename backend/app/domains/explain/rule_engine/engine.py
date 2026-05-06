"""
explain/rule_engine/engine.py
Layer 4 — RecipeExplanationRuleEngine (main orchestrator)

Calls all sub-modules in order, merges results, and builds the final
RuleEngineResult including FormulaReview.

Rule Engine is the SOURCE OF TRUTH.  LLM must not contradict its output.
"""

from __future__ import annotations

import logging
from typing import List

from app.domains.explain.contracts.contracts import (
    DerivedMetrics,
    EnrichedExplainInput,
    FeedingGuidanceFlag,
    FormulaReview,
    NormalizedPetContext,
    RiskFlag,
    RuleEngineResult,
    StrengthFlag,
)
from app.domains.explain.rule_engine import guidance_rules, nutrition_rules, realism_rules, structure_rules

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# FormulaReview constants
# ---------------------------------------------------------------------------

_KEY_CONCERN_MAP: dict[str, str] = {
    # Nutrient deficiency risks (from nutrition_rules)
    "low_calcium":                          "Calcium appears below the minimum requirement",
    "low_phosphorus":                       "Phosphorus appears below the minimum requirement",
    "low_protein":                          "Protein appears below the minimum requirement",
    "low_fat":                              "Fat appears below the minimum requirement",
    # Ratio risks (from nutrition_rules)
    "ca_p_ratio_below_target":              "Ca:P ratio is below the preferred range (1.0–2.0)",
    "ca_p_ratio_above_target":              "Ca:P ratio is above the preferred range (1.0–2.0)",
    # Structure risks (from structure_rules)
    "missing_calcium_source":               "No calcium source detected in this recipe",
    "missing_omega3_support":               "No omega-3 source detected in this recipe",
    "high_supplement_dependency":           "Recipe relies on a high number of supplements",
    # Realism risks (from realism_rules)
    "high_fruit_for_small_puppy":           "Fruit proportion may be high for a small/toy puppy",
    "high_fruit_proportion":                "Fruit proportion appears high for this recipe",
    "high_liver_proportion":                "Liver proportion exceeds the recommended limit",
    "ingredient_exceeds_g_per_kg_bw_limit": (
        "One or more ingredients exceed the recommended g/kg body weight limit"
    ),
}

_MAX_KEY_CONCERNS = 4


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------
def run(enriched: EnrichedExplainInput, derived: DerivedMetrics) -> RuleEngineResult:

    """
    Orchestrate all rule sub-modules and assemble RuleEngineResult.

    Execution order:
      1. nutrition_rules  → NutritionSummary + nutritional flags
      2. structure_rules  → structural flags
      3. realism_rules    → ingredient-amount flags
      4. guidance_rules   → feeding guidance flags
      5. engine           → FormulaReview (sanity_status + key_concerns)
    """
    normalized   = enriched.normalized
    pet_context  = normalized.pet_context
    nutrient_analysis = normalized.nutrient_analysis

    # 1 — Nutrition
    nutrition_summary, nutrition_strengths, nutrition_risks = nutrition_rules.run(
        nutrient_analysis=nutrient_analysis,
        derived=derived,
    )

    # 2 — Structure
    structure_strengths, structure_risks = structure_rules.run(
        snapshot=derived.structure_snapshot,
        derived=derived,
    )

    # 3 — Realism (ingredient amount)
    realism_risks = realism_rules.run(
        ingredient_metrics=derived.ingredient_metrics,
        pet_context=pet_context,
    )

    # 3b — g/kg BW check (requires enrich data — built here in engine)
    g_per_kg_enrich_map = _build_g_per_kg_map(enriched)
    g_per_kg_risks = realism_rules.check_g_per_kg_bw(
        ingredient_metrics=derived.ingredient_metrics,
        enrich_map=g_per_kg_enrich_map,
    )

    # Merge all flags
    all_strength_flags: List[StrengthFlag] = nutrition_strengths + structure_strengths
    all_risk_flags:     List[RiskFlag]     = (
        nutrition_risks + structure_risks + realism_risks + g_per_kg_risks
    )

    # 4 — Guidance
    flagged_nutrient_ids = {f.nutrient_id for f in nutrition_summary.flagged_nutrients}
    guidance_flags: List[FeedingGuidanceFlag] = guidance_rules.run(
        pet_context=pet_context,
        risk_flags=all_risk_flags,
        flagged_nutrient_ids=flagged_nutrient_ids,
    )

    # 5 — FormulaReview
    formula_review = _build_formula_review(all_risk_flags)

    # Sort flags for deterministic output
    all_strength_flags = _sort_strengths(all_strength_flags)
    all_risk_flags     = sorted(all_risk_flags, key=lambda f: f.priority)

    return RuleEngineResult(
        nutrition_summary=nutrition_summary,
        formula_review=formula_review,
        strength_flags=all_strength_flags,
        risk_flags=all_risk_flags,
        feeding_guidance_flags=guidance_flags,
        ingredient_adjustment_ideas=None,   # reserved — next sprint
    )


# ---------------------------------------------------------------------------
# FormulaReview builder
# ---------------------------------------------------------------------------

def _build_formula_review(risk_flags: List[RiskFlag]) -> FormulaReview:
    """
    sanity_status:
      any severity == "high"   → "questionable"
      any severity == "medium" → "needs_adjustment"
      otherwise                → "reasonable"

    key_concerns: top-N concerns from triggered risk flags, ordered by priority.
    """
    if any(f.severity == "high" for f in risk_flags):
        sanity_status = "questionable"
    elif any(f.severity == "medium" for f in risk_flags):
        sanity_status = "needs_adjustment"
    else:
        sanity_status = "reasonable"

    # Build key_concerns from triggered risk codes, sorted by priority
    sorted_risks = sorted(risk_flags, key=lambda f: f.priority)
    key_concerns: List[str] = []
    seen: set[str] = set()
    for rf in sorted_risks:
        if rf.code in _KEY_CONCERN_MAP and rf.code not in seen:
            key_concerns.append(_KEY_CONCERN_MAP[rf.code])
            seen.add(rf.code)
        if len(key_concerns) >= _MAX_KEY_CONCERNS:
            break

    return FormulaReview(
        sanity_status=sanity_status,
        key_concerns=key_concerns,
    )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _build_g_per_kg_map(enriched: EnrichedExplainInput) -> dict[str, float]:
    """
    Extract {ingredient_id: max_g_per_kg_bw} from EnrichedIngredient list.
    Only includes ingredients where enrich_available=True and limit is defined.
    """
    result: dict[str, float] = {}
    for ing in enriched.enriched_ingredients:
        if ing.enrich_available and ing.max_g_per_kg_bw is not None:
            result[ing.ingredient_id] = ing.max_g_per_kg_bw
    return result


_PRIORITY_ORDER = {"high": 0, "medium": 1, "low": 2}


def _sort_strengths(flags: List[StrengthFlag]) -> List[StrengthFlag]:
    return sorted(flags, key=lambda f: _PRIORITY_ORDER.get(f.priority, 9))
