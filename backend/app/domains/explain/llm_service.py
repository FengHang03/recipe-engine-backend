"""
explain/llm_service.py
Layer 6 — RecipeExplanationLLMService

Responsibility:
  1. build_user_prompt() — trim context + serialize for LLM (two-pass)
  2. call_llm()          — call API, parse structured JSON response
  3. generate_fallback_output() — rule-engine-based fallback when LLM fails

Pass 1 (global exclude): strip internal fields not useful to LLM
Pass 2 (per-module trim): limit list lengths, filter category_totals by key categories
"""

from __future__ import annotations

import os
import json
import logging
import re
from typing import Any

from openai import AsyncOpenAI

from app.domains.explain.contracts.contracts import (
    ExplanationPolicy,
    FeedingGuidanceOutput,
    GuidanceTextItem,
    IngredientAdjustmentIdeasOutput,
    IngredientSummaryItem,
    KeyFindingOutput,
    MetaOutput,
    NutritionInterpretationOutput,
    OverviewOutput,
    PlainLanguageTakeaway,
    RecipeExplanationContext,
    RecipeExplanationOutput,
    RiskOutput,
    StrengthOutput,
)

from app.domains.explain.rule_engine.engine import _KEY_CONCERN_MAP

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Pass 1 — global exclude: internal fields not meaningful to the LLM
# ---------------------------------------------------------------------------

_EXCLUDE_FIELDS: set[str] = {
    "nutrient_id",
    "evidence_code",
    "reason_code",
    "ratio_id",
    "recommended_action_code",
    "enrich_available",
    "food_subgroup",       # DB implementation detail
    "activity_level",      # not forwarded to LLM in MVP
    "sterilization_status",
    "reproductive_stage",
    "health_conditions",
    "allergies",
}

# ---------------------------------------------------------------------------
# Pass 2 — per-module trim settings
# ---------------------------------------------------------------------------

_MAX_INGREDIENTS_FOR_LLM = 6
_MAX_FLAGGED_NUTRIENTS   = 3
_MAX_STRENGTH_FLAGS      = 3   # mirrors ExplanationPolicy default
_MAX_RISK_FLAGS          = 4
_MAX_GUIDANCE_FLAGS      = 4

# category_totals: only forward these coarse categories to the LLM
_KEY_CATEGORIES = {"organ", "fruit", "fat_oil", "supplement", "other"}

# ingredient priority: categories that deserve a slot even if pct < 15%
_PRIORITY_CATEGORIES = {"organ", "fruit", "fat_oil"}

# ---------------------------------------------------------------------------
# LLM model
# ---------------------------------------------------------------------------

_MODEL          = "qwen3.6-plus"
_MAX_TOKENS     = 2500
_QWEN_BASE_URL  = os.getenv(
    "QWEN_BASE_URL",
    "https://dashscope-intl.aliyuncs.com/compatible-mode/v1",
)
_QWEN_MODEL     = os.getenv("QWEN_MODEL", "qwen3.6-plus")
_QWEN_EXPLAIN_API_KEY   = os.getenv("QWEN_EXPLAIN_API_KEY")

# ---------------------------------------------------------------------------
# Fallback status → headline / summary text
# ---------------------------------------------------------------------------

_STATUS_MAP: dict[str, tuple[str, str]] = {
    "reasonable":       (
        "This recipe looks nutritionally reasonable.",
        "This recipe appears nutritionally reasonable for your dog.",
    ),
    "needs_adjustment": (
        "This recipe may benefit from some adjustments.",
        "This recipe may benefit from some adjustments to better meet your dog's needs.",
    ),
    "questionable":     (
        "This recipe has some concerns to address.",
        "This recipe has concerns that should be reviewed before regular use.",
    ),
}



# ---------------------------------------------------------------------------
# Fallback: code → human-readable title for strengths and risks
# ---------------------------------------------------------------------------

_STRENGTH_CODE_TO_TITLE: dict[str, str] = {
    "strong_protein_support":         "Good protein content",
    "balanced_ca_p_ratio":            "Balanced calcium-to-phosphorus ratio",
    "clear_main_protein_present":     "Clear main protein source",
    "clear_calcium_source_present":   "Calcium source included",
    "limited_supplement_dependency":  "Minimal supplement reliance",
}

_RISK_CODE_TO_TITLE: dict[str, str] = {
    "low_calcium":                          "Low calcium",
    "low_phosphorus":                       "Low phosphorus",
    "low_protein":                          "Low protein",
    "low_fat":                              "Low fat",
    "ca_p_ratio_below_target":              "Ca:P ratio below target",
    "ca_p_ratio_above_target":              "Ca:P ratio above target",
    "missing_calcium_source":               "No calcium source detected",
    "missing_omega3_support":               "No omega-3 source detected",
    "high_supplement_dependency":           "High supplement dependency",
    "high_fruit_for_small_puppy":           "Fruit proportion high for small puppy",
    "high_fruit_proportion":                "Fruit proportion high",
    "high_liver_proportion":                "Liver proportion above limit",
    "ingredient_exceeds_g_per_kg_bw_limit": "Ingredient exceeds g/kg body weight limit",
}


# ---------------------------------------------------------------------------
# shape verification
# ---------------------------------------------------------------------------

_REQUIRED_TOP_LEVEL_KEYS = {
    "overview",
    "nutrition_interpretation",
    "strengths",
    "risks",
    "feeding_guidance",
    "plain_language_takeaway",
    "meta",
}


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------
def _strip_json_fences(text: str) -> str:
    text = text.strip()

    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.IGNORECASE)
        text = re.sub(r"\s*```$", "", text)

    return text.strip()


def _extract_first_json_object(text: str) -> str:
    """
    Extract the first balanced JSON object from model output.
    Handles extra prose before/after JSON.
    """
    text = _strip_json_fences(text)

    start = text.find("{")
    if start < 0:
        raise ValueError("No JSON object start found in LLM output")

    depth = 0
    in_string = False
    escape = False

    for index in range(start, len(text)):
        char = text[index]

        if in_string:
            if escape:
                escape = False
            elif char == "\\":
                escape = True
            elif char == '"':
                in_string = False
            continue

        if char == '"':
            in_string = True
        elif char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return text[start : index + 1]

    raise ValueError("No balanced JSON object found in LLM output")


def _parse_json_object_from_llm(raw_text: str) -> dict[str, Any]:
    try:
        candidate = _extract_first_json_object(raw_text)
    except Exception as exc:
        logger.warning(
            "LLM JSON extraction failed: %s. raw_prefix=%r raw_suffix=%r",
            exc,
            raw_text[:500],
            raw_text[-500:],
        )
        raise

    try:
        data = json.loads(candidate)
    except json.JSONDecodeError as exc:
        logger.warning(
            "LLM JSON parse failed: %s. candidate_chars=%s raw_prefix=%r raw_suffix=%r",
            exc,
            len(candidate),
            raw_text[:500],
            raw_text[-500:],
        )
        raise

    if not isinstance(data, dict):
        raise ValueError("LLM JSON output is not an object")

    return data

def _looks_like_valid_llm_payload(data: dict[str, Any]) -> bool:
    if not isinstance(data, dict):
        return False
    return _REQUIRED_TOP_LEVEL_KEYS.issubset(data.keys())

async def _request_llm(
    client: AsyncOpenAI,
    *,
    model: str,
    system_prompt: str,
    user_prompt: str,
    max_tokens: int,
) -> str:
    response = await client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.2,
        max_tokens=max_tokens,
        extra_body={"enable_thinking": False},
        response_format={"type": "json_object"},
    )

    return response.choices[0].message.content or ""


async def call_llm(context: RecipeExplanationContext) -> RecipeExplanationOutput:
    """
    Build prompt, call LLM, parse response.
    Falls back to generate_fallback_output() on any failure.
    """
    try:
        system_prompt = _build_system_prompt(context.explanation_policy)
        user_prompt   = _build_user_prompt(context)

        api_key = os.getenv("QWEN_EXPLAIN_API_KEY")
        if not api_key:
            raise ValueError("QWEN_EXPLAIN_API_KEY is not configured")

        client = AsyncOpenAI(
            api_key=api_key,
            base_url=os.getenv(
                "QWEN_BASE_URL",
                "https://dashscope-intl.aliyuncs.com/compatible-mode/v1",
            ),
        )

        logger.info(
            "LLM request: recipe_id=%s model=%s prompt_chars=%s",
            context.recipe_context.recipe_id,
            os.getenv("QWEN_MODEL", "qwen3.6-plus"),
            len(user_prompt),
        )

        response = await client.chat.completions.create(
            model=os.getenv("QWEN_MODEL", "qwen3.6-plus"),
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.2,
            max_tokens=_MAX_TOKENS,
            extra_body={"enable_thinking": False},
            response_format={"type": "json_object"}
        )

        choice = response.choices[0]
        raw = choice.message.content or ""

        finish_reason = getattr(choice, "finish_reason", None)
        if finish_reason and finish_reason not in {"stop", "tool_calls"}:
            logger.warning(
                "LLM response finish_reason=%s recipe_id=%s raw_suffix=%r",
                finish_reason,
                context.recipe_context.recipe_id,
                raw[-500:],
            )

        data = _parse_json_object_from_llm(raw)

        if not _looks_like_valid_llm_payload(data):
            logger.warning(
                "LLM payload missing required top-level fields: keys=%s raw_prefix=%r",
                sorted(data.keys()),
                raw[:500],
            )
            raise ValueError("LLM payload missing required top-level fields")

        return _parse_llm_response(data, context)

    except Exception as exc:
        logger.warning("LLM call failed: %s — using fallback output", exc)
        return generate_fallback_output(context)


# ---------------------------------------------------------------------------
# System prompt
# ---------------------------------------------------------------------------

def _build_system_prompt(policy: ExplanationPolicy) -> str:
    return (
        "You are an experimental dog recipe analysis assistant helping explain a homemade recipe.\n\n"
        "GOAL:\n"
        "Provide a useful, practical, structured explanation based on the provided ingredients, nutrient findings, and formula summary.\n\n"
        "RULES (non-negotiable):\n"
        "1. Use explicit ingredient list items and nutrient findings as primary evidence.\n"
        "2. If an ingredient is explicitly present, do NOT say it is missing.\n"
        "3. You may infer likely functional roles from ingredient names and common usage, but phrase uncertain points carefully.\n"
        "4. You may suggest recipe improvement directions, but present them as exploratory or conditional suggestions, not verified final instructions.\n"
        "5. Do NOT make medical diagnoses or clinical treatment claims.\n"
        "6. Do NOT invent nutrients, ingredients, or facts that are not supported by the context.\n"
        "7. Do NOT claim the recipe is fully balanced for long-term feeding unless the provided context clearly supports it.\n"
        "8. If rule-based flags are present, use them as important signals, but you may also reason directly from ingredient and nutrient data.\n"
        f"9. Follow explanation_policy strictly: max_strengths={policy.max_strengths}, "
        f"max_risks={policy.max_risks}, max_guidance_items={policy.max_guidance_items}.\n"
        "10. For playful_comment, write one short, witty, light roast. It may be humorous, but must be kind, non-shaming, and grounded in the provided recipe context. Do NOT exaggerate danger or make medical claims.\n"
        "11. Return ONLY valid JSON matching the exact schema provided. No markdown fences, no preamble, no trailing text."
    )


# ---------------------------------------------------------------------------
# User prompt: two-pass trim + serialise
# ---------------------------------------------------------------------------

def _build_user_prompt(context: RecipeExplanationContext) -> str:
    """
    Pass 1: exclude internal fields globally via _exclude_internal().
    Pass 2: per-module trimming of list lengths and category filtering.
    """
    policy = context.explanation_policy

    # ── Pet (minimal fields for LLM) ────────────────────────────────────────
    pet = {
        "species":             context.pet_context.species,
        "life_stage":          context.pet_context.life_stage,
        "age_months":          context.pet_context.age_months,
        "body_weight_kg":      context.pet_context.body_weight_kg,
        "size_class":          context.pet_context.size_class,
        "daily_calories_kcal":context.pet_context.daily_calories_kcal,
    }

    # ── Recipe (minimal fields for LLM) ─────────────────────────────────────
    recipe = {
        "recipe_id":          context.recipe_context.recipe_id,
        "total_weight_grams": context.recipe_context.total_weight_grams,
        "used_supplements":   context.recipe_context.used_supplements,
    }

    # ── Nutrition summary ────────────────────────────────────────────────────
    nutrition = {
        "level1_findings": [
            _exclude_internal(f.model_dump())
            for f in context.nutrition_summary.level1_findings
        ],
        "flagged_nutrients": [
            _exclude_internal(f.model_dump())
            for f in sorted(
                context.nutrition_summary.flagged_nutrients,
                key=lambda x: 0 if x.severity == "high" else 1,
            )[:_MAX_FLAGGED_NUTRIENTS]
        ],
        "ratio_findings": [
            _exclude_internal(f.model_dump())
            for f in context.nutrition_summary.ratio_findings
        ],
    }

    # ── Ingredient summary ───────────────────────────────────────────────────
    top_ingredients = _trim_ingredients(context.ingredient_summary.ingredients)
    key_cat_totals  = [
        ct.model_dump()
        for ct in context.category_totals
        if ct.category in _KEY_CATEGORIES
    ]
    ingredient_summary = {
        "top_ingredients":   [_exclude_internal(i.model_dump()) for i in top_ingredients],
        "category_totals":   key_cat_totals,
        "structure_snapshot": context.structure_snapshot.model_dump(),
    }

    # ── Formula review ───────────────────────────────────────────────────────
    formula = context.formula_review.model_dump()

    # ── Flags (trimmed, internal fields excluded) ────────────────────────────
    strengths = [
        _exclude_internal(f.model_dump())
        for f in sorted(
            context.strength_flags,
            key=lambda f: ({"high": 0, "medium": 1, "low": 2}.get(f.priority, 9)),
        )[:_MAX_STRENGTH_FLAGS]
    ]
    risks = [
        _exclude_internal(f.model_dump())
        for f in sorted(
            context.risk_flags,
            key=lambda f: (0 if f.severity == "high" else 1, f.priority),
        )[:_MAX_RISK_FLAGS]
    ]
    guidance = [
        _exclude_internal(f.model_dump())
        for f in sorted(
            context.feeding_guidance_flags,
            key=lambda f: ({"high": 0, "medium": 1, "low": 2}.get(f.priority, 9)),
        )[:_MAX_GUIDANCE_FLAGS]
    ]

    # ── JSON schema instruction ──────────────────────────────────────────────
    schema_instruction = _json_schema_instruction()

    prompt = (
        f"Analyze this dog recipe.\n\n"
        f"[PET]\n{json.dumps(pet, indent=2)}\n\n"
        f"[RECIPE]\n{json.dumps(recipe, indent=2)}\n\n"
        f"[NUTRITION]\n{json.dumps(nutrition, indent=2)}\n\n"
        f"[INGREDIENTS]\n{json.dumps(ingredient_summary, indent=2)}\n\n"
        f"[FORMULA REVIEW]\n{json.dumps(formula, indent=2)}\n\n"
        f"[STRENGTHS] ({len(strengths)} flags)\n{json.dumps(strengths, indent=2)}\n\n"
        f"[RISKS] ({len(risks)} flags)\n{json.dumps(risks, indent=2)}\n\n"
        f"[FEEDING GUIDANCE] ({len(guidance)} flags)\n{json.dumps(guidance, indent=2)}\n\n"
        f"{schema_instruction}"
    )
    return prompt


def _trim_ingredients(
    items: list[IngredientSummaryItem],
) -> list[IngredientSummaryItem]:
    """
    Keep up to _MAX_INGREDIENTS_FOR_LLM items using priority rules:
      1. pct_of_recipe > 15%  (dominant ingredients)
      2. food_group in _PRIORITY_CATEGORIES (organ, fruit, fat_oil)
      3. Fill remainder by pct_of_recipe descending
    """
    selected: list[IngredientSummaryItem] = []
    seen_names: set[str] = set()

    def _add(item: IngredientSummaryItem) -> None:
        if item.ingredient_name not in seen_names and len(selected) < _MAX_INGREDIENTS_FOR_LLM:
            selected.append(item)
            seen_names.add(item.ingredient_name)

    # Pass 1: dominant by pct
    for item in items:
        if (item.pct_of_recipe or 0.0) > 15:
            _add(item)

    # Pass 2: priority categories
    for item in items:
        if (item.food_group or "").lower() in _PRIORITY_CATEGORIES:
            _add(item)

    # Pass 3: fill by pct descending (already sorted by derived_metrics)
    for item in items:
        _add(item)

    return selected


def _exclude_internal(d: dict[str, Any]) -> dict[str, Any]:
    """Remove internal-only fields from a serialized dict (Pass 1)."""
    return {k: v for k, v in d.items() if k not in _EXCLUDE_FIELDS}


def _clean_optional_text(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _json_schema_instruction() -> str:
    return """\
Return ONLY one valid JSON object. Keep every text field short.
Hard limits:
- overview.summary: max 2 short sentences
- playful_comment: max 1 short sentence
- nutrition_interpretation.overall_assessment: max 2 short sentences
- key_findings: max 3 items
- strengths: max 2 items
- risks: max 3 items
- each feeding_guidance list: max 2 items
- plain_language_takeaway.for_pet_parent: max 2 short sentences

Required JSON shape:
{
  "overview": {
    "status": "reasonable|needs_adjustment|questionable",
    "headline": "short title",
    "summary": "short summary",
    "confidence": "high|medium|low"
  },
  "playful_comment": "short friendly roast",
  "nutrition_interpretation": {
    "overall_assessment": "short assessment",
    "key_findings": [
      {
        "title": "...",
        "status": "strong|adequate|low|high|normal|borderline|abnormal",
        "importance": "high|medium|low",
        "message": "..."
      }
    ]
  },
  "strengths": [
    {
      "title": "...",
      "summary": "...",
      "why_it_matters": "..."
    }
  ],
  "risks": [
    {
      "severity": "high|medium",
      "title": "...",
      "summary": "...",
      "why_it_matters": "...",
      "suggested_fix": "..."
    }
  ],
  "feeding_guidance": {
    "feeding_strategy": [{"text": "..."}],
    "monitoring_points": [{"text": "..."}],
    "adjustments_to_consider": [{"text": "..."}]
  },
  "plain_language_takeaway": {
    "for_pet_parent": "short user-facing takeaway"
  },
  "meta": {
    "confidence": "high|medium|low"
  }
}"""


# ---------------------------------------------------------------------------
# Response parser
# ---------------------------------------------------------------------------

def _parse_llm_response(
    data: dict[str, Any],
    context: RecipeExplanationContext,
) -> RecipeExplanationOutput:
    """
    Construct RecipeExplanationOutput from parsed LLM JSON.
    confidence is read from meta and synced to overview.
    """
    confidence = data.get("meta", {}).get("confidence", "medium")

    ov_raw = data.get("overview", {})
    overview = OverviewOutput(
        status=ov_raw.get("status", context.formula_review.sanity_status),
        headline=ov_raw.get("headline", ""),
        summary=ov_raw.get("summary", ""),
        confidence=confidence,              # synced from meta
    )

    ni_raw = data.get("nutrition_interpretation", {})
    nutrition_interpretation = NutritionInterpretationOutput(
        overall_assessment=ni_raw.get("overall_assessment", ""),
        key_findings=[
            KeyFindingOutput(
                title=kf.get("title", ""),
                status=kf.get("status", ""),
                importance=kf.get("importance", "medium"),
                message=kf.get("message", ""),
            )
            for kf in ni_raw.get("key_findings", [])
        ],
    )

    strengths = [
        StrengthOutput(
            title=s.get("title", ""),
            summary=s.get("summary", ""),
            why_it_matters=s.get("why_it_matters"),
        )
        for s in data.get("strengths", [])
    ]

    risks = [
        RiskOutput(
            severity=r.get("severity", "medium"),
            title=r.get("title", ""),
            summary=r.get("summary", ""),
            why_it_matters=r.get("why_it_matters"),
            suggested_fix=r.get("suggested_fix"),
        )
        for r in data.get("risks", [])
    ]

    fg_raw = data.get("feeding_guidance", {})
    feeding_guidance = FeedingGuidanceOutput(
        feeding_strategy=[
            GuidanceTextItem(text=i.get("text", ""))
            for i in fg_raw.get("feeding_strategy", [])
        ],
        monitoring_points=[
            GuidanceTextItem(text=i.get("text", ""))
            for i in fg_raw.get("monitoring_points", [])
        ],
        adjustments_to_consider=[
            GuidanceTextItem(text=i.get("text", ""))
            for i in fg_raw.get("adjustments_to_consider", [])
        ],
    )

    takeaway_raw = data.get("plain_language_takeaway", {})
    plain_language_takeaway = PlainLanguageTakeaway(
        for_pet_parent=takeaway_raw.get("for_pet_parent", "")
    )

    playful_comment = _clean_optional_text(data.get("playful_comment"))
    if playful_comment is None:
        playful_comment = _build_fallback_playful_comment(context)

    return RecipeExplanationOutput(
        schema_version="1.0",
        recipe_id=context.recipe_context.recipe_id,
        overview=overview,
        playful_comment=playful_comment,
        nutrition_interpretation=nutrition_interpretation,
        strengths=strengths,
        risks=risks,
        feeding_guidance=feeding_guidance,
        plain_language_takeaway=plain_language_takeaway,
        ingredient_adjustment_ideas=IngredientAdjustmentIdeasOutput(),  # reserved
        meta=MetaOutput(
            confidence=confidence,          # synced from overview
            generated_from="rule_grounded_llm",
            fallback_used=False,
        ),
    )


# ---------------------------------------------------------------------------
# Fallback output
# ---------------------------------------------------------------------------

def generate_fallback_output(
    context: RecipeExplanationContext,
) -> RecipeExplanationOutput:
    """
    Build a rule-engine-based output without LLM.
    Used when the LLM call fails for any reason.
    Always sets meta.fallback_used = True.
    """
    policy        = context.explanation_policy
    sanity_status = context.formula_review.sanity_status
    key_concerns  = context.formula_review.key_concerns

    headline, summary = _STATUS_MAP.get(
        sanity_status, _STATUS_MAP["needs_adjustment"]
    )

    # overview
    overview = OverviewOutput(
        status=sanity_status,
        headline=headline,
        summary=summary,
        confidence="low",   # synced with meta.confidence
    )

    # nutrition_interpretation — populate key_findings from rule engine facts
    concern_text = "; ".join(key_concerns) if key_concerns else "No major concerns identified."
    nutrition_interpretation = NutritionInterpretationOutput(
        overall_assessment=f"Based on nutritional analysis: {concern_text}",
        key_findings=_build_fallback_key_findings(context),
    )

    # strengths — sorted by priority, readable title
    strengths = [
        StrengthOutput(
            title=_STRENGTH_CODE_TO_TITLE.get(f.code, f.code),
            summary="Identified as a nutritional strength.",
        )
        for f in sorted(
            context.strength_flags,
            key=lambda f: ({"high": 0, "medium": 1, "low": 2}.get(f.priority, 9)),
        )[: policy.max_strengths]
    ]

    # risks — severity first, then priority; readable title + concern summary
    risks = [
        RiskOutput(
            severity=f.severity,
            title=_RISK_CODE_TO_TITLE.get(f.code, f.code),
            summary=_KEY_CONCERN_MAP.get(f.code, f"Risk identified: {f.code}"),
        )
        for f in sorted(
            context.risk_flags,
            key=lambda x: (0 if x.severity == "high" else 1, x.priority),
        )[: policy.max_risks]
    ]

    # feeding_guidance — split by flag type
    feeding_strategy        = []
    monitoring_points       = []
    adjustments_to_consider = []
    for f in context.feeding_guidance_flags[: policy.max_guidance_items]:
        text = f.human_readable or f.code
        item = GuidanceTextItem(text=text)
        if f.type == "feeding_strategy":
            feeding_strategy.append(item)
        elif f.type == "monitoring":
            monitoring_points.append(item)
        else:
            adjustments_to_consider.append(item)

    feeding_guidance = FeedingGuidanceOutput(
        feeding_strategy=feeding_strategy,
        monitoring_points=monitoring_points,
        adjustments_to_consider=adjustments_to_consider,
    )

    return RecipeExplanationOutput(
        schema_version="1.0",
        recipe_id=context.recipe_context.recipe_id,
        overview=overview,
        playful_comment=_build_fallback_playful_comment(context),
        nutrition_interpretation=nutrition_interpretation,
        strengths=strengths,
        risks=risks,
        feeding_guidance=feeding_guidance,
        plain_language_takeaway=PlainLanguageTakeaway(for_pet_parent=summary),
        ingredient_adjustment_ideas=IngredientAdjustmentIdeasOutput(),
        meta=MetaOutput(
            confidence="low",
            generated_from="rule_grounded_llm",
            fallback_used=True,
        ),
    )


def _build_fallback_key_findings(
    context: RecipeExplanationContext,
    max_findings: int = 3,
) -> list[KeyFindingOutput]:
    """
    Build up to max_findings KeyFindingOutput entries from rule-engine facts,
    without requiring LLM. Sources in priority order:
      1. flagged_nutrients  (status "low" or "high" — most important issues)
      2. ratio_findings     (ca_p_ratio status)
      3. level1_findings    (adequate / strong — positive signals)
    """
    findings: list[KeyFindingOutput] = []

    # 1 — flagged nutrients (problems first)
    for fn in sorted(
        context.nutrition_summary.flagged_nutrients,
        key=lambda x: 0 if x.severity == "high" else 1,
    ):
        if len(findings) >= max_findings:
            break
        findings.append(KeyFindingOutput(
            title=fn.display_name,
            status=fn.status,
            importance=fn.severity,
            message=(
                f"{fn.display_name} appears {fn.status}"
                + (f" (value: {fn.value} {fn.unit or ''})" if fn.value is not None else "")
                + "."
            ),
        ))

    # 2 — ratio findings (borderline / abnormal)
    for rf in context.nutrition_summary.ratio_findings:
        if len(findings) >= max_findings:
            break
        if rf.status != "normal":
            findings.append(KeyFindingOutput(
                title=rf.display_name,
                status=rf.status,
                importance=rf.severity,
                message=(
                    f"{rf.display_name} is {rf.status}"
                    + (f" (value: {rf.value:.2f})" if rf.value is not None else "")
                    + f". Target range: {rf.min_target}–{rf.max_target}."
                ),
            ))

    # 3 — level1 positives (fill remaining slots)
    for lf in context.nutrition_summary.level1_findings:
        if len(findings) >= max_findings:
            break
        if lf.status in ("strong", "adequate"):
            findings.append(KeyFindingOutput(
                title=lf.display_name,
                status=lf.status,
                importance=lf.priority,
                message=f"{lf.display_name} is {lf.status}."
                + (f" (value: {lf.value} {lf.unit or ''})" if lf.value is not None else ""),
            ))

    return findings

def _build_fallback_playful_comment(context: RecipeExplanationContext) -> str:
    """
    Deterministic, safe fallback playful comment.
    Kept light and non-medical; never invents unsupported facts.
    """
    status = context.formula_review.sanity_status
    has_risks = bool(context.risk_flags)
    has_strengths = bool(context.strength_flags)

    risk_codes = {f.code for f in context.risk_flags}
    strength_codes = {f.code for f in context.strength_flags}

    if "missing_calcium_source" in risk_codes or "low_calcium" in risk_codes:
        return (
            "This bowl has good intentions, but calcium looks like it missed the meeting invite."
        )

    if "ca_p_ratio_below_target" in risk_codes or "ca_p_ratio_above_target" in risk_codes:
        return (
            "The recipe is trying to be balanced, but the calcium-phosphorus ratio is still negotiating terms."
        )

    if "missing_omega3_support" in risk_codes:
        return (
            "A decent bowl overall, but omega-3 support may be off doing a side quest."
        )

    if "high_liver_proportion" in risk_codes:
        return (
            "The liver showed up with main-character energy; it may need a smaller role."
        )

    if status == "reasonable" and has_strengths and not has_risks:
        return (
            "Honestly, this recipe came prepared. Annoyingly responsible, in the best way."
        )

    if status == "questionable":
        return (
            "This recipe has potential, but it should not be left alone with a nutrition label just yet."
        )

    if status == "needs_adjustment":
        return (
            "Not a disaster, just a recipe that could use a little nutrition adult supervision."
        )

    return (
        "A promising bowl with a few details still politely asking for attention."
    )