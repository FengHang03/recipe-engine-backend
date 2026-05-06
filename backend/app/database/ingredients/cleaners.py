from __future__ import annotations

import pandas as pd


COOKING_KEYWORDS = {
    "cooked",
    "boiled",
    "drained",
    "steamed",
    "raw",
    "without skin",
    "braised",
    "simmered",
    "baked",
    "fried",
    "grilled",
    "roasted",
    "roast",
    "sauteed",
    "stir-fried",
    "poached",
    "smoked",
    "cured",
    "pickled",
    "canned",
    "frozen",
    "fresh",
    "dried",
    "dehydrated",
    "powdered",
    "crumbles",
    "minced",
    "chopped",
    "sliced",
    "diced",
    "shredded",
    "ground",
    "domesticated",
    "whole",
    "peeled",
    "unpeeled",
    "conventional",
    "fortified",
    "enriched",
    "natural",
    "artificial",
    "dry",
    "heat",
    "broiled",
    "stewed",
    "includes",
    "patty",
    "farmed",
    "without salt",
    "with salt",
    "salt",
    "dry heat",
    "cold pressed",
    "variety meats and by-products",
    "mollusks",
    "crustaceans",
    "fish",
    "mixed species",
    "broilers or fryers",
    "composite of trimmed retail cuts",
    'trimmed to 1/8" fat',
    "choice",
    'trimmed to 0" fat',
    "pearled",
    "all varieties",
    "salad or cooking",
    "(approx. 65%)",
    "(approx. 75%)",
    "(approx. 85%)",
    "(approx. 95%)",
    "linoleic",
    "high oleic",
    "pan-browned",
    "chuck for stew",
    "all classes",
    "atlantic",
    "pacific",
    "grades",
    "tenderloin",
}

KEEP_TERMS = {
    "sweet potato",
    "sweet corn",
    "sweet pepper",
    "sweet onion",
    "blue crab",
    "blue mussels",
    "yellow squash",
    "yellow corn",
}


def get_short_name(description: str | None) -> str:
    if description is None or pd.isna(description):
        return ""

    parts = [part.strip() for part in str(description).split(",")]
    kept_parts: list[str] = []

    for part in parts:
        lower = part.lower()

        if any(keep_term in lower for keep_term in KEEP_TERMS):
            kept_parts.append(part)
            continue

        if not any(keyword in lower for keyword in COOKING_KEYWORDS):
            kept_parts.append(part)

    return " ".join(kept_parts).strip()