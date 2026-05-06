from __future__ import annotations

import logging
import re
import pandas as pd

from .regex_patterns import DiversityPatterns, RegexPatterns, _COOKED_PAT, _RAW_PAT, _SUPPLEMENT_PAT

logger = logging.getLogger(__name__)


def infer_food_category(description: str) -> str:
    try:
        if not isinstance(description, str) or not description.strip():
            return "OTHER"

        desc_lower = description.strip().lower()

        if desc_lower in RegexPatterns.EXCEPTIONS:
            return RegexPatterns.EXCEPTIONS[desc_lower]

        if RegexPatterns.PROCESSED.search(desc_lower):
            return "SUPPLEMENT"
        if RegexPatterns.FAT_OIL.search(desc_lower):
            return "FAT_OIL"
        if RegexPatterns.ORGAN.search(desc_lower):
            return "ORGAN"
        if RegexPatterns.MINERAL_SHELLFISH.search(desc_lower):
            return "MINERAL_SHELLFISH"
        if RegexPatterns.PROTEIN_SHELLFISH.search(desc_lower):
            return "PROTEIN_SHELLFISH"
        if RegexPatterns.FISH_OILY.search(desc_lower) or RegexPatterns.FISH_LEAN.search(desc_lower):
            return "PROTEIN_FISH"
        if RegexPatterns.EGG.search(desc_lower):
            return "PROTEIN_EGG"
        if RegexPatterns.MEAT.search(desc_lower):
            return "PROTEIN_MEAT"
        if RegexPatterns.CARB_TUBER.search(desc_lower):
            return "CARB_TUBER"
        if RegexPatterns.CARB_GRAIN.search(desc_lower):
            return "CARB_GRAIN"
        if RegexPatterns.LEGUME.search(desc_lower):
            return "CARB_OTHER"
        if RegexPatterns.FIBER.search(desc_lower):
            return "FIBER"
        if RegexPatterns.VEGETABLE.search(desc_lower):
            return "PLANT_ANTIOXIDANT"
        if RegexPatterns.BERRY.search(desc_lower):
            return "PLANT_ANTIOXIDANT"

        return "OTHER"

    except Exception as e:
        logger.warning("Error inferring food category for %r: %s", description, e)
        return "OTHER"


def get_category_hint_from_id(
    category_id: int,
    description: str,
    fat_g_100g: float | None = None,
) -> str | None:
    try:
        if not isinstance(description, str) or not description.strip():
            return None

        desc_lower = description.strip().lower()

        if category_id == 1:
            return "PROTEIN_EGG" if "egg" in desc_lower else "DAIRY"
        if category_id == 4:
            return "FAT_OIL"
        if category_id in (5, 10, 13, 17):
            return "ORGAN" if RegexPatterns.ORGAN.search(desc_lower) else "PROTEIN_MEAT"
        if category_id == 11:
            return "CARB_TUBER" if RegexPatterns.CARB_TUBER.search(desc_lower) else "PLANT_ANTIOXIDANT"
        if category_id == 12:
            return "TREATS"
        if category_id == 15:
            if RegexPatterns.MINERAL_SHELLFISH.search(desc_lower):
                return "MINERAL_SHELLFISH"
            if RegexPatterns.PROTEIN_SHELLFISH.search(desc_lower):
                return "PROTEIN_SHELLFISH"
            if RegexPatterns.FISH_OILY.search(desc_lower) or RegexPatterns.FISH_LEAN.search(desc_lower):
                return "PROTEIN_FISH"
        if category_id == 16 and RegexPatterns.LEGUME.search(desc_lower):
            return "CARB_LEGUME"
        if category_id == 20 and RegexPatterns.CARB_GRAIN.search(desc_lower):
            return "CARB_GRAIN"
        if category_id == 21:
            return "SUPPLEMENT"

        return None

    except Exception as e:
        logger.warning("Error in get_category_hint_from_id(%s, %r): %s", category_id, description, e)
        return None


def get_diversity_tag(row: pd.Series) -> str | None:
    desc = str(row.get("description", "")).lower()
    cat_id = row.get("food_category_id")

    if cat_id in [4, 12, 16, 20]:
        return None

    if cat_id == 13:
        return "div_protein_ruminant"

    if cat_id == 5:
        if DiversityPatterns.WATERFOWL.search(desc):
            return "div_protein_waterfowl"
        return "div_protein_poultry"

    if cat_id == 15:
        if DiversityPatterns.SHELLFISH.search(desc):
            return "div_protein_marine_shellfish"
        return "div_protein_marine_fish"

    if cat_id == 17:
        if DiversityPatterns.PORK.search(desc):
            return "div_protein_pork"
        if DiversityPatterns.EXOTIC.search(desc):
            if "rabbit" in desc or "hare" in desc or "kangaroo" in desc:
                return "div_protein_exotic"
            return "div_protein_ruminant"
        return "div_protein_ruminant"

    if cat_id == 1:
        if DiversityPatterns.EGG.search(desc):
            return "div_protein_egg"
        return None

    if cat_id == 10:
        return "div_protein_pork"

    if cat_id in [9, 11]:
        if "blueberr" in desc or "cranberr" in desc or "raspberr" in desc or "blackberr" in desc:
            return "div_plant_berry"
        if "spinach" in desc or "kale" in desc or "collard" in desc:
            return "div_plant_leafy_green"
        if "carrot" in desc or "pumpkin" in desc or "sweet potato" in desc:
            return "div_plant_orange"
        return "div_plant_other"

    return None


def infer_prep_state(description: str, food_category_id: int | None) -> str:
    desc = (description or "").strip().lower()

    if food_category_id == 21 or food_category_id == 4 or _SUPPLEMENT_PAT.search(desc):
        return "supplement"
    if _COOKED_PAT.search(desc):
        return "cooked"
    if _RAW_PAT.search(desc):
        return "raw"
    return "raw"

def normalize_for_raw_match(description: str) -> str:
    desc = (description or "").lower()

    removable_terms = [
        "raw", "cooked", "boiled", "steamed", "roasted", "baked", "fried",
        "broiled", "grilled", "braised", "poached", "stewed", "drained",
        "with skin", "without skin",
    ]

    for term in removable_terms:
        desc = desc.replace(term, "")

    desc = re.sub(r"\s+", " ", desc).strip(" ,")
    return desc

