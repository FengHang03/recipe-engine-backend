"""
explain/router.py
FastAPI router for POST /recipes/explain

Orchestrates the full pipeline:
  Layer 0: adapter
  Layer 1: normalize
  Layer 2: enrich  (ingredient_repository / cache)
  Layer 3: build_derived_metrics
  Layer 4: run_rule_engine
  Layer 5: build_context
  Layer 6: call_llm  (async API — falls back automatically)

Error handling:
  - LLM failure     -> 200 + meta.fallback_used=True  (handled inside call_llm)
  - Pipeline failure -> 500
  - Request validation failure -> 422 (FastAPI automatic)
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException, Request
from starlette.concurrency import run_in_threadpool

from app.domains.explain.adapter import (
    ExplainRecipeApiRequest,
    adapt_to_explain_request,
)
from app.domains.explain.context_builder import build_context
from app.domains.explain.derived_metrics import build as build_derived_metrics
from app.domains.explain.enrichment import enrich
from app.domains.explain.llm_service import call_llm
from app.domains.explain.contracts.contracts import (
    ExplanationPolicy,
    RecipeExplanationOutput,
)
from app.domains.explain.normalizer import normalize
from app.domains.explain.rule_engine import run_rule_engine

logger = logging.getLogger(__name__)

router = APIRouter(tags=["explain"])


@router.post(
    "/recipes/explain",
    response_model=RecipeExplanationOutput,
    summary="AI recipe explanation",
    description=(
        "Analyze a generated recipe for a specific dog and return a structured "
        "explanation including nutritional assessment, strengths, risks, and "
        "feeding guidance. LLM failure returns HTTP 200 with fallback_used=true."
    ),
)
async def explain_recipe(
    payload: ExplainRecipeApiRequest,
    request: Request,
) -> RecipeExplanationOutput:
    """
    Full pipeline:
      frontend payload
        -> adapter
        -> normalize
        -> enrich
        -> derive
        -> rule_engine
        -> context
        -> llm
    """
    ingredient_repository = getattr(request.app.state, "ingredient_repository", None)
    if ingredient_repository is None:
        logger.error("explain_recipe: ingredient_repository missing on app.state")
        raise HTTPException(
            status_code=500,
            detail="Ingredient repository is not available",
        )

    try:
        # Layer 0 — adapt frontend payload to internal explain request
        explain_request = adapt_to_explain_request(payload)

        # Layer 1 — normalize
        normalized = normalize(explain_request)
        logger.debug(
            "explain_recipe: normalized recipe_id=%s life_stage=%s ingredient_count=%d",
            normalized.recipe_context.recipe_id,
            normalized.pet_context.life_stage,
            len(normalized.ingredients),
        )

        # Layer 2 — enrich from ingredient repository / cache
        enriched = await run_in_threadpool(
            enrich,
            normalized,
            ingredient_repository,
        )

        unenriched = sum(
            1 for i in enriched.enriched_ingredients if not i.enrich_available
        )
        if unenriched:
            logger.warning(
                "explain_recipe: %d ingredient(s) could not be enriched",
                unenriched,
            )

        # Layer 3 — derive metrics
        derived = build_derived_metrics(enriched)

        # Layer 4 — rule engine
        rule_result = run_rule_engine(enriched, derived)
        logger.debug(
            "explain_recipe: rule_engine complete — sanity_status=%s strengths=%d risks=%d guidance=%d",
            rule_result.formula_review.sanity_status,
            len(rule_result.strength_flags),
            len(rule_result.risk_flags),
            len(rule_result.feeding_guidance_flags),
        )

        # Layer 5 — context
        context = build_context(
            normalized,
            derived,
            rule_result,
            ExplanationPolicy(),
        )

        # Layer 6 — LLM
        output = await call_llm(context)

        if output.meta.fallback_used:
            logger.warning(
                "explain_recipe: LLM failed — returning fallback for recipe_id=%s",
                normalized.recipe_context.recipe_id,
            )

        return output

    except Exception as exc:
        recipe_id = "unknown"
        try:
            recipe = getattr(payload, "recipe", None)
            if isinstance(recipe, dict):
                recipe_id = recipe.get("recipe_id", "unknown")
            else:
                recipe_id = getattr(recipe, "recipe_id", "unknown")
        except Exception:
            pass

        logger.exception(
            "explain_recipe: pipeline error for recipe_id=%s: %s",
            recipe_id,
            exc,
        )
        raise HTTPException(
            status_code=500,
            detail="Recipe explanation failed",
        ) from exc
        