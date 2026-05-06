"""
explain/enrichment.py
Layer 2 — ExplainEnrichmentService

Responsibility:
- Read ingredient metadata from IngredientRepository / IngredientDataCache
- Convert raw ingredient tags into canonical explain-layer role/risk/note tags
- No workflow logic, no rule judgment, no LLM work
"""

from __future__ import annotations

import logging
from typing import Dict, List, Optional, Sequence

from app.domains.ingredients.infra.ingredient_repository import IngredientRepository
from app.domains.explain.contracts.contracts import (
    EnrichedExplainInput,
    EnrichedIngredient,
    NormalizedExplainInput,
    NormalizedIngredient,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Tag normalization maps
# ---------------------------------------------------------------------------

_ROLE_TAG_MAP: dict[str, str] = {
    "role_omega3_ala": "omega3_source",
    "role_omega3_lc": "omega3_source",
    "role_omega6_la": "omega6_source",
    "role_calcium": "calcium_source",
    "role_iron": "iron_source",
    "role_zinc": "zinc_source",
    "role_iodine": "iodine_source",
    "role_vita": "vitamin_a_source",
    "role_vitd": "vitamin_d_source",
    "role_vit_b1": "vitamin_b1_source",
    "role_vit_b12": "vitamin_b12_source",
    "role_choline": "choline_source",
    "role_fiber_source": "fiber_source",
}

_RISK_TAG_MAP: dict[str, str] = {
    "risk_high_copper": "risk_high_copper",
    "risk_high_iodine": "risk_high_iodine",
    "risk_high_selenium": "risk_high_selenium",
    "risk_high_sodium": "risk_high_sodium",
    "risk_high_vit_a": "risk_high_vit_a",
    "risk_high_vit_d": "risk_high_vit_d",
}


def _normalize_role_tag(raw: str) -> Optional[str]:
    key = str(raw).strip().lower()
    canonical = _ROLE_TAG_MAP.get(key)
    if canonical is None:
        logger.debug("Unknown role tag %r — dropped from explain layer", raw)
    return canonical


def _normalize_risk_tag(raw: str) -> Optional[str]:
    key = str(raw).strip().lower()
    canonical = _RISK_TAG_MAP.get(key)
    if canonical is None:
        logger.debug("Unknown risk tag %r — dropped from explain layer", raw)
    return canonical


def _normalize_role_tags(raw_tags: List[str]) -> List[str]:
    result: List[str] = []
    seen: set[str] = set()
    for raw in raw_tags:
        canonical = _normalize_role_tag(raw)
        if canonical and canonical not in seen:
            result.append(canonical)
            seen.add(canonical)
    return result


def _normalize_risk_tags(raw_tags: List[str]) -> List[str]:
    result: List[str] = []
    seen: set[str] = set()
    for raw in raw_tags:
        canonical = _normalize_risk_tag(raw)
        if canonical and canonical not in seen:
            result.append(canonical)
            seen.add(canonical)
    return result


# ---------------------------------------------------------------------------
# Internal data container
# ---------------------------------------------------------------------------

class _EnrichData:
    __slots__ = (
        "food_group",
        "food_subgroup",
        "max_g_per_kg_bw",
        "max_pct_kcal",
        "raw_role_tags",
        "raw_risk_tags",
        "raw_note_tags",
    )

    def __init__(self) -> None:
        self.food_group: Optional[str] = None
        self.food_subgroup: Optional[str] = None
        self.max_g_per_kg_bw: Optional[float] = None
        self.max_pct_kcal: Optional[float] = None
        self.raw_role_tags: List[str] = []
        self.raw_risk_tags: List[str] = []
        self.raw_note_tags: List[str] = []


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def enrich(
    normalized: NormalizedExplainInput,
    ingredient_repository: IngredientRepository,
) -> EnrichedExplainInput:
    ingredient_ids = list(dict.fromkeys(i.ingredient_id for i in normalized.ingredients))

    if not ingredient_ids:
        return EnrichedExplainInput(
            normalized=normalized,
            enriched_ingredients=[],
        )

    enrich_map = _fetch_enrich_data(
        ingredient_ids=ingredient_ids,
        ingredient_repository=ingredient_repository,
    )

    enriched = [
        _build_enriched_ingredient(ing, enrich_map.get(ing.ingredient_id))
        for ing in normalized.ingredients
    ]

    return EnrichedExplainInput(
        normalized=normalized,
        enriched_ingredients=enriched,
    )


# ---------------------------------------------------------------------------
# Repository / cache fetch
# ---------------------------------------------------------------------------

def _fetch_enrich_data(
    ingredient_ids: Sequence[str],
    ingredient_repository: IngredientRepository,
) -> Dict[str, _EnrichData]:
    result: Dict[str, _EnrichData] = {}

    try:
        profiles = ingredient_repository.get_ingredient_profiles_by_ids(ingredient_ids)
    except Exception as exc:
        logger.warning(
            "IngredientRepository profile lookup failed: %s — all ingredients will be unenriched",
            exc,
        )
        return result

    data_cache = getattr(ingredient_repository, "data_cache", None)

    for ingredient_id in ingredient_ids:
        profile = profiles.get(str(ingredient_id))
        if profile is None:
            continue

        d = _EnrichData()
        fg = profile.food_group
        d.food_group = fg.value if hasattr(fg, "value") else (str(fg) if fg is not None else None)
        fsg = profile.food_subgroup
        d.food_subgroup = fsg.value if hasattr(fsg, "value") else (str(fsg) if fsg is not None else None)
        d.max_g_per_kg_bw = profile.max_g_per_kg_bw
        d.max_pct_kcal = profile.max_pct_kcal

        raw_tags = []
        if data_cache is not None:
            raw_tags = data_cache.get_tags(ingredient_id)
        else:
            raw_tags = list(getattr(profile, "tags", []) or [])

        for tag in raw_tags:
            tag_norm = str(tag).strip()
            if not tag_norm:
                continue
            lower = tag_norm.lower()
            if lower.startswith("role_"):
                d.raw_role_tags.append(tag_norm)
            elif lower.startswith("risk_"):
                d.raw_risk_tags.append(tag_norm)
            else:
                d.raw_note_tags.append(tag_norm)

        result[str(ingredient_id)] = d

    return result


# ---------------------------------------------------------------------------
# Assembly
# ---------------------------------------------------------------------------

def _build_enriched_ingredient(
    ing: NormalizedIngredient,
    data: Optional[_EnrichData],
) -> EnrichedIngredient:
    if data is None:
        logger.warning(
            "No enrich data found for ingredient_id=%r (%r) — using defaults",
            ing.ingredient_id,
            ing.ingredient_name,
        )
        return EnrichedIngredient(
            ingredient_id=ing.ingredient_id,
            ingredient_name=ing.ingredient_name,
            weight_grams=ing.weight_grams,
            pct_of_recipe=ing.pct_of_recipe,
            is_supplement=ing.is_supplement,
            slot_type=ing.slot_type,
            enrich_available=False,
        )

    return EnrichedIngredient(
        ingredient_id=ing.ingredient_id,
        ingredient_name=ing.ingredient_name,
        weight_grams=ing.weight_grams,
        pct_of_recipe=ing.pct_of_recipe,
        is_supplement=ing.is_supplement,
        slot_type=ing.slot_type,
        food_group=data.food_group,
        food_subgroup=data.food_subgroup,
        max_g_per_kg_bw=data.max_g_per_kg_bw,
        max_pct_kcal=data.max_pct_kcal,
        role_tags=_normalize_role_tags(data.raw_role_tags),
        risk_tags=_normalize_risk_tags(data.raw_risk_tags),
        note_tags=list(data.raw_note_tags),
        enrich_available=True,
    )