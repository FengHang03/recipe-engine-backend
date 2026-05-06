

def _build_display_weights_from_resolved_preset(
    self,
    preset: PresetRecipeSpec,
) -> List:
    """
    Convert resolved preset items into frontend/result display weights.

    Uses:
    - item.resolved_weight_g as raw display grams
    """
    from app.domains.recipe_generation.contracts.results import WeightedIngredient

    weights: List[WeightedIngredient] = []

    for item in preset.ingredients:
        resolved_weight_g = getattr(item, "resolved_weight_g", None)
        if resolved_weight_g is None:
            raise RecipeSpecMappingError(
                f"Preset '{preset.recipe_id}' contains unresolved item: "
                f"{item.ingredient.short_name or item.ingredient.ingredient_id}"
            )

        is_supplement = bool(item.has_dose_tiers)

        weights.append(
            WeightedIngredient(
                ingredient_id=item.ingredient.ingredient_id,
                ingredient_name=item.ingredient.short_name or item.ingredient.description,
                short_name=item.ingredient.short_name,
                slot_type=item.slot_type,
                weight_grams=round(float(resolved_weight_g), 6),
                pct_of_recipe=None,
                is_supplement=is_supplement,
                was_user_locked=False,
            )
        )

    total_weight = sum(w.weight_grams for w in weights)
    if total_weight > 1e-9:
        for w in weights:
            w.pct_of_recipe = round((w.weight_grams / total_weight) * 100.0, 4)

    return weights