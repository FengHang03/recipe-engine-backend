"""
explain/context_builder.py
Layer 5 — RecipeExplanationContextBuilder

Responsibility: assemble RecipeExplanationContext from upstream layer outputs.
No business logic, no trimming, no judgment.

Trimming and internal-field exclusion happen in LLMService.build_user_prompt()
to keep the two layers' responsibilities clearly separated:
  - ContextBuilder  → complete, faithful assembly
  - LLMService      → trim + exclude for token efficiency
"""

from __future__ import annotations

import logging

from app.domains.explain.contracts.contracts import (
    DerivedMetrics,
    ExplanationPolicy,
    NormalizedExplainInput,
    RecipeExplanationContext,
    RuleEngineResult,
)

logger = logging.getLogger(__name__)


def _resolve_policy(policy: ExplanationPolicy | None) -> ExplanationPolicy:
    return policy or ExplanationPolicy()


def build_context(
    normalized: NormalizedExplainInput,
    derived: DerivedMetrics,
    rule_result: RuleEngineResult,
    policy: ExplanationPolicy | None = None,
) -> RecipeExplanationContext:
    """
    Assemble RecipeExplanationContext from the outputs of Layers 1–4.

    All fields are passed through as-is — no filtering, no reordering.
    The full ingredient_summary (all ingredients, all category_totals) is
    included; LLMService.build_user_prompt() trims it for the prompt.

    Args:
        normalized:  output of Layer 1 (Normalizer)
        derived:     output of Layer 3 (DerivedMetricsBuilder)
        rule_result: output of Layer 4 (RuleEngine)
        policy:      ExplanationPolicy — defaults to ExplanationPolicy() if None
    """
    policy = _resolve_policy(policy)

    logger.debug(
    "Building RecipeExplanationContext: recipe_id=%s, strengths=%d, risks=%d, guidance=%d, ingredients=%d",
    normalized.recipe_context.recipe_id,
    len(rule_result.strength_flags),
    len(rule_result.risk_flags),
    len(rule_result.feeding_guidance_flags),
    len(derived.ingredient_summary.ingredients),
)

    return RecipeExplanationContext(
        pet_context=normalized.pet_context,
        recipe_context=normalized.recipe_context,
        nutrition_summary=rule_result.nutrition_summary,
        ingredient_summary=derived.ingredient_summary,
        category_totals=derived.category_totals,
        structure_snapshot=derived.structure_snapshot,
        formula_review=rule_result.formula_review,
        strength_flags=rule_result.strength_flags,
        risk_flags=rule_result.risk_flags,
        feeding_guidance_flags=rule_result.feeding_guidance_flags,
        explanation_policy=policy,
    )
