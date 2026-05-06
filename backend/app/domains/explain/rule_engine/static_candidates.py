"""
explain/rule_engine/static_candidates.py

Static candidate ingredient lists for optimization hints.
Reserved for next sprint — not used in current MVP.

Activation plan (next sprint):
  - RecipeExplanationContext.improvement_suggestions: List[IngredientAdjustmentIdea]
  - RecipeExplanationOutput.ingredient_adjustment_ideas populated from LLM output
"""

from __future__ import annotations

# Canonical role → candidate ingredient names
STATIC_CANDIDATES: dict[str, list[str]] = {
    "calcium_source": [
        "Eggshell Powder",
        "Bone Meal",
        "Sardine (with bones)",
        "Plain Yogurt",
    ],
    "omega3_source": [
        "Salmon",
        "Sardine",
        "Mackerel",
        "Fish Oil",
        "Flaxseed Oil",
    ],
    "main_protein": [
        "Chicken Breast",
        "Turkey (ground)",
        "Beef (lean)",
        "Lamb",
        "Salmon",
    ],
    "vitamin_b12_source": [
        "Beef Liver",
        "Chicken Liver",
        "Sardine",
        "Egg",
    ],
    "zinc_source": [
        "Beef",
        "Pumpkin Seeds",
        "Chicken",
    ],
}

# recommended_action_code → candidate_key mapping
ACTION_TO_CANDIDATE: dict[str, str] = {
    "increase_calcium_support":      "calcium_source",
    "rebalance_calcium_phosphorus":  "calcium_source",
    "add_omega3_support":            "omega3_source",
    "add_main_protein":              "main_protein",
}
