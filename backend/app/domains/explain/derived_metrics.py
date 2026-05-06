"""
explain/derived_metrics.py
Layer 3 — ExplainDerivedMetricsBuilder

Responsibility: pure computation — no DB, no LLM, no side effects.
Derives all metrics needed by the Rule Engine and ContextBuilder.

Key design decisions:
  - pct_of_recipe is passed through from backend (already calculated).
  - grams_per_kg_bw is the only new per-ingredient calculation.
  - food_group from DB is fine-grained (e.g. "PROTEIN_MEAT", "CARB_GRAIN").
    category_totals aggregates by COARSE category for rule usability.
  - has_main_protein: slot_type == "Main Protein Slot" is primary signal;
    coarse category "protein" is the fallback.
  - All other structure_snapshot flags use canonical role_tags from enrichment layer.
"""

from __future__ import annotations

import logging
import re
from collections import defaultdict
from typing import Dict, List, Optional

from app.domains.explain.contracts.contracts import (
    CategoryTotal,
    DerivedMetrics,
    EnrichedExplainInput,
    EnrichedIngredient,
    IngredientSummary,
    IngredientSummaryItem,
    StructureSnapshot,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Coarse category mapping
# DB FoodGroup (uppercase) → explain-layer coarse category (lowercase)
# ---------------------------------------------------------------------------

_COARSE_CATEGORY_MAP: dict[str, str] = {
    # Protein sources
    "PROTEIN_MEAT":      "protein",
    "PROTEIN_FISH":      "protein",
    "PROTEIN_EGG":       "protein",
    "PROTEIN_SHELLFISH": "protein",
    # Mineral shellfish (e.g. oysters — mineral-dense, but still protein-adjacent)
    "MINERAL_SHELLFISH": "protein",
    # Organ meats
    "ORGAN":             "organ",
    # Carbohydrates
    "CARB_GRAIN":        "carb",
    "CARB_TUBER":        "carb",
    "CARB_LEGUME":       "carb",
    "CARB_OTHER":        "carb",
    # Plant / antioxidant — PLANT_BLUE may contain true fruits (berries) or
    # non-fruit blue/purple veg (beet, eggplant, red cabbage).
    # _to_coarse_category() refines this using FRUIT_BY_NAME regex.
    "PLANT_ANTIOXIDANT": "vegetable",  # default; overridden for berries below
    # Fats & oils
    "FAT_OIL":           "fat_oil",
    # Fiber
    "FIBER":             "fiber",
    # Supplements
    "SUPPLEMENT":        "supplement",
    # Treats
    "TREAT":             "treat",
    # Dairy
    "DAIRY":             "dairy",
}

_PROTEIN_COARSE_CATS = {"protein"}

# Slot type value for main protein — provided by backend on IngredientWeightInput
_SLOT_MAIN_PROTEIN_VALUES = {
    "main_protein",
    "main protein slot",
    "main_protein_slot",
}

# Canonical role tags (post-normalization from enrichment layer)
_ROLE_CALCIUM_SOURCE = "calcium_source"
_ROLE_OMEGA3_SOURCE  = "omega3_source"

# Coarse categories that indicate carbohydrate presence
_CARB_COARSE_CATS = {"carb"}

# Coarse categories that indicate vegetable presence
_VEGETABLE_COARSE_CATS = {"vegetable"}

# Coarse categories that indicate organ meat presence
_LIVER_FOOD_SUBGROUPS = {"organ_liver"}

_CALCIUM_FOOD_SUBGROUPS = {
    "supplement_calcium",
}

_CALCIUM_NAME_KEYWORDS = {
    "bone meal",
    "eggshell",
    "egg shell",
    "calcium carbonate",
    "calcium citrate",
}

# Regex to identify true fruit ingredients within PLANT_ANTIOXIDANT category.
# Applied only when food_group is PLANT_ANTIOXIDANT to distinguish
# berries (→ "fruit") from other blue/purple veg like beet or eggplant (→ "vegetable").
_FRUIT_BY_NAME = re.compile(
    r'\b(blueberr(?:y|ies)|blackberr(?:y|ies)|raspberr(?:y|ies)'
    r'|cranberr(?:y|ies)|strawberr(?:y|ies)|acai|pomegranate[s]?'
    r'|cher(?:ry|ries)|mulberr(?:y|ies)|currant[s]?|gooseberr(?:y|ies))'
    r'\b',
    re.IGNORECASE,
)

def _to_coarse_category(food_group: Optional[str], ingredient_name: str = "") -> str:
    """
    Map a fine-grained DB FoodGroup to a coarse explain-layer category.
    Unknown values fall back to "other".

    Special case — PLANT_ANTIOXIDANT:
      PLANT_BLUE covers both true berries (blueberry, raspberry…) AND
      non-fruit blue/purple vegetables (beet, eggplant, red cabbage).
      When ingredient_name matches _FRUIT_BY_NAME the coarse category is
      overridden to "fruit" so high_fruit_for_small_puppy can trigger correctly.
    """
    if not food_group:
        return "other"
    mapped = _COARSE_CATEGORY_MAP.get(food_group.upper().strip())
    if mapped is None:
        logger.debug("Unknown food_group %r — mapped to 'other'", food_group)
        return "other"
    # Refine PLANT_ANTIOXIDANT: true berries → "fruit", everything else stays "vegetable"
    if mapped == "vegetable" and ingredient_name and _FRUIT_BY_NAME.search(ingredient_name):
        return "fruit"
    return mapped


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def build(enriched: EnrichedExplainInput) -> DerivedMetrics:
    """
    Derive all metrics from EnrichedExplainInput.

    Computation order:
      1. Per-ingredient metrics
      2. Coarse category totals
      3. Supplement / non-supplement counts
      4. Ca:P ratio (from nutrient_analysis)
      5. Structure snapshot
      6. Pre-built IngredientSummary (for ContextBuilder; trimming happens in LLMService)
    """
    normalized     = enriched.normalized
    body_weight_kg = normalized.pet_context.body_weight_kg

    ingredient_metrics = _build_ingredient_metrics(
        enriched.enriched_ingredients,
        body_weight_kg,
    )
    category_totals      = _build_category_totals(ingredient_metrics)
    supplement_count     = sum(1 for m in ingredient_metrics if m.is_supplement)
    non_supplement_count = sum(1 for m in ingredient_metrics if not m.is_supplement)
    total_count          = len(ingredient_metrics)
    ca_p_ratio           = _compute_ca_p_ratio(normalized.nutrient_analysis)
    structure            = _build_structure_snapshot(ingredient_metrics)
    ingredient_summary   = _build_ingredient_summary(ingredient_metrics)

    return DerivedMetrics(
        ingredient_metrics=ingredient_metrics,
        category_totals=category_totals,
        structure_snapshot=structure,
        supplement_count=supplement_count,
        non_supplement_count=non_supplement_count,
        total_ingredients_count=total_count,
        ca_p_ratio=ca_p_ratio,
        ingredient_summary=ingredient_summary,
    )


# ---------------------------------------------------------------------------
# Per-ingredient metrics
# ---------------------------------------------------------------------------

def _build_ingredient_metrics(
    ingredients: List[EnrichedIngredient],
    body_weight_kg: float,
) -> List[EnrichedIngredient]:
    safe_bw = body_weight_kg if body_weight_kg > 0 else 1.0
    if body_weight_kg <= 0:
        logger.warning(
            "body_weight_kg=%s is invalid — defaulting to 1.0 for grams_per_kg_bw",
            body_weight_kg,
        )
    return [
        ing.model_copy(update={"grams_per_kg_bw": round(ing.weight_grams / safe_bw, 4)})
        for ing in ingredients
    ]


# ---------------------------------------------------------------------------
# Coarse category totals
# ---------------------------------------------------------------------------

def _build_category_totals(
    metrics: List[EnrichedIngredient],
) -> List[CategoryTotal]:
    """
    Aggregate total_grams and pct_of_recipe by COARSE category.
    Fine-grained DB categories (PROTEIN_MEAT, CARB_GRAIN, …) are mapped
    to coarse labels (protein, carb, …) so rule engine has manageable groups.
    """
    grams_by_cat: Dict[str, float] = defaultdict(float)
    pct_by_cat:   Dict[str, float] = defaultdict(float)

    for m in metrics:
        coarse = _to_coarse_category(m.food_group, m.ingredient_name)
        grams_by_cat[coarse] += m.weight_grams
        pct_by_cat[coarse] += float(m.pct_of_recipe or 0.0)

    return [
        CategoryTotal(
            category=cat,
            total_grams=round(grams_by_cat[cat], 2),
            pct_of_recipe=round(pct_by_cat[cat], 2),
        )
        for cat in sorted(grams_by_cat)
    ]


# ---------------------------------------------------------------------------
# Ca:P ratio
# ---------------------------------------------------------------------------

def _compute_ca_p_ratio(nutrient_analysis) -> Optional[float]:
    """
    ca_p_ratio = calcium.value / phosphorus.value
    Returns None if either value is missing or phosphorus is zero.
    """
    ca_value: Optional[float] = None
    p_value:  Optional[float] = None

    for n in nutrient_analysis:
        if n.nutrient_id == "ca_p_ratio" and n.value:
          return round(float(n.value), 3)

        if n.nutrient_id in ("calcium", "1087"):
            ca_value = n.value
        elif n.nutrient_id in ("phosphorus", "1091"):
            p_value = n.value

    if ca_value is None or p_value is None:
        logger.debug(
            "Ca:P ratio skipped — calcium=%s, phosphorus=%s", ca_value, p_value
        )
        return None

    if p_value == 0:
        logger.warning("Ca:P ratio skipped — phosphorus value is 0")
        return None

    return round(ca_value / p_value, 3)


# ---------------------------------------------------------------------------
# Structure snapshot
# ---------------------------------------------------------------------------

def _is_main_protein_slot(slot_type: Optional[str]) -> bool:
    if not slot_type:
        return False
    normalized = str(slot_type).strip().lower().replace("-", "_")
    return normalized in _SLOT_MAIN_PROTEIN_VALUES

def _is_liver(m: EnrichedIngredient) -> bool:
    subgroup = (m.food_subgroup or "").strip().lower()
    if subgroup in _LIVER_FOOD_SUBGROUPS:
        return True

    # fallback: older data may not have food_subgroup
    coarse = _to_coarse_category(m.food_group, m.ingredient_name)
    name = (m.ingredient_name or "").lower()
    return coarse == "organ" and "liver" in name

def _is_calcium_source(m: EnrichedIngredient) -> bool:
    """
    Detect calcium source from canonical role tags first, then DB subgroup/name fallback.

    Primary:
      - role_tags contains "calcium_source"

    Fallback:
      - food_subgroup == "supplement_calcium"
      - common calcium supplement names such as bone meal / eggshell powder
    """
    role_set = {str(tag).strip().lower() for tag in (m.role_tags or [])}
    if _ROLE_CALCIUM_SOURCE in role_set:
        return True

    subgroup = (m.food_subgroup or "").strip().lower()
    if subgroup in _CALCIUM_FOOD_SUBGROUPS:
        return True

    name = (m.ingredient_name or "").strip().lower()
    return any(keyword in name for keyword in _CALCIUM_NAME_KEYWORDS)

def _build_structure_snapshot(metrics: List[EnrichedIngredient]) -> StructureSnapshot:
    """
    has_main_protein:
      Primary   — slot_type == "Main Protein Slot"  (set by backend)
      Fallback  — coarse category is "protein"
                  (covers PROTEIN_MEAT / PROTEIN_FISH / PROTEIN_EGG / PROTEIN_SHELLFISH)

    has_calcium_source:
      role_tag "calcium_source" (canonical, set by enrichment layer)

    has_omega3_support:
      role_tag "omega3_source"  (covers both ALA and LC forms)

    has_carbohydrate_source:
      coarse category "carb"

    has_vegetable:
      coarse category "vegetable"

    has_liver:
      coarse category "organ"
      (DB FoodGroup "ORGAN" covers all organ meats including liver)
    """
    has_main_protein        = False
    has_calcium_source      = False
    has_omega3_support      = False
    has_carbohydrate_source = False
    has_vegetable           = False
    has_liver               = False

    for m in metrics:
        role_set = set(m.role_tags)
        coarse   = _to_coarse_category(m.food_group, m.ingredient_name)

        # Main protein: slot_type first, coarse category fallback (≥10% threshold)
        if not has_main_protein:
            if _is_main_protein_slot(m.slot_type):
                has_main_protein = True
            elif coarse in _PROTEIN_COARSE_CATS and float(m.pct_of_recipe or 0.0) >= 10:
                has_main_protein = True

        # if _ROLE_CALCIUM_SOURCE in role_set:
        #     has_calcium_source = True
        
        if _is_calcium_source(m):
            has_calcium_source = True

        if _ROLE_OMEGA3_SOURCE in role_set:
            has_omega3_support = True

        if coarse in _CARB_COARSE_CATS:
            has_carbohydrate_source = True

        if coarse in _VEGETABLE_COARSE_CATS:
            has_vegetable = True

        if _is_liver(m):
            has_liver = True

    return StructureSnapshot(
        has_main_protein=has_main_protein,
        has_calcium_source=has_calcium_source,
        has_omega3_support=has_omega3_support,
        has_carbohydrate_source=has_carbohydrate_source,
        has_vegetable=has_vegetable,
        has_liver=has_liver,
    )


# ---------------------------------------------------------------------------
# Pre-built IngredientSummary
# ---------------------------------------------------------------------------

def _build_ingredient_summary(
    metrics: List[EnrichedIngredient],
) -> IngredientSummary:
    """
    Full list sorted by pct_of_recipe descending.
    Trimming to top-N for LLM happens in LLMService.build_user_prompt() (Pass 2).
    risk_tags are included in IngredientSummaryItem but not used this sprint.
    """
    items = [
        IngredientSummaryItem(
            ingredient_name=m.ingredient_name,
            pct_of_recipe=m.pct_of_recipe,
            grams_per_kg_bw=m.grams_per_kg_bw or 0.0,
            food_group=_to_coarse_category(m.food_group, m.ingredient_name),  # coarse for LLM
            slot_type=m.slot_type,
            risk_tags=m.risk_tags,   # reserved — not used this sprint
        )
        for m in sorted(metrics, key=lambda x: float(x.pct_of_recipe or 0.0), reverse=True)
    ]
    return IngredientSummary(ingredients=items)
