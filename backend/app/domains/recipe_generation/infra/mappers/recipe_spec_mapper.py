"""
Responsibilities:
Convert external raw preset JSON into raw preset contract objects.

This file only performs mapping / transformation:
- No database access
- No pet weight resolution
- No nutrient analysis
"""

from __future__ import annotations

from typing import Any, Mapping

from app.domains.recipe_generation.contracts.recipe_spec import (
    RawPresetRecipeItem,
    RawPresetRecipeSpec,
)
from app.shared.contracts.enums import SlotType


class RecipeSpecMappingError(ValueError):
    """Raised when raw preset data cannot be mapped into a valid preset spec."""


class RecipeSpecMapper:
    """
    Mapper for converting raw preset JSON definition
    into RawPresetRecipeSpec objects.
    """

    def to_raw_preset_recipe_spec(
        self,
        raw_preset: Mapping[str, Any],
    ) -> RawPresetRecipeSpec:
        recipe_id = self._require_str(raw_preset.get("recipe_id"), "raw_preset.recipe_id")
        name = self._require_str(raw_preset.get("name"), f"Preset '{recipe_id}'.name")

        raw_items = raw_preset.get("ingredients")
        if raw_items is None:
            raise RecipeSpecMappingError(
                f"Preset '{recipe_id}' is missing 'ingredients'."
            )
        if not isinstance(raw_items, list) or len(raw_items) == 0:
            raise RecipeSpecMappingError(
                f"Preset '{recipe_id}' must contain at least one ingredient item."
            )

        items = []
        for idx, raw_item in enumerate(raw_items):
            if not isinstance(raw_item, Mapping):
                raise RecipeSpecMappingError(
                    f"Preset '{recipe_id}' item[{idx}] must be an object/dict."
                )

            fdc_id = self._require_str(
                raw_item.get("fdc_id"),
                f"Preset '{recipe_id}' item[{idx}].fdc_id",
            )

            slot_type = self._parse_slot_type(
                raw_item.get("slot_type"),
                recipe_id=recipe_id,
                item_index=idx,
            )

            try:
                item = RawPresetRecipeItem(
                    fdc_id=fdc_id,
                    slot_type=slot_type,
                    weight_curve=raw_item.get("weight_curve", []),
                    dose_tiers=raw_item.get("dose_tiers", []),
                    base_weight_g=raw_item.get("base_weight_g"),
                    base_ratio=raw_item.get("base_ratio"),
                    default_unit=raw_item.get("default_unit"),
                    grams_per_unit=raw_item.get("grams_per_unit"),
                    is_optional=bool(raw_item.get("is_optional", False)),
                    notes=raw_item.get("notes"),
                )
            except Exception as exc:
                raise RecipeSpecMappingError(
                    f"Preset '{recipe_id}' item[{idx}] is invalid."
                ) from exc

            items.append(item)

        try:
            return RawPresetRecipeSpec(
                recipe_id=recipe_id,
                name=name,
                description=raw_preset.get("description"),
                ingredients=items,
                basis_kcal=raw_preset.get("basis_kcal"),
                basis_total_weight_g=raw_preset.get("basis_total_weight_g"),
                display_basis=raw_preset.get("display_basis", "raw"),
                analysis_basis=raw_preset.get("analysis_basis", "mixed_cooked"),
                weight_resolution_mode=raw_preset.get(
                    "weight_resolution_mode",
                    "interpolate_by_pet_weight",
                ),
                notes=raw_preset.get("notes"),
                metadata=dict(raw_preset.get("metadata") or {}),
            )
        except Exception as exc:
            raise RecipeSpecMappingError(
                f"Preset '{recipe_id}' could not be mapped into RawPresetRecipeSpec."
            ) from exc

    def _parse_slot_type(
        self,
        raw_slot_type: Any,
        recipe_id: str,
        item_index: int,
    ) -> SlotType:
        if raw_slot_type is None:
            raise RecipeSpecMappingError(
                f"Preset '{recipe_id}' item[{item_index}] is missing slot_type."
            )

        if isinstance(raw_slot_type, SlotType):
            return raw_slot_type

        try:
            return SlotType(raw_slot_type)
        except Exception as exc:
            raise RecipeSpecMappingError(
                f"Preset '{recipe_id}' item[{item_index}] has invalid slot_type: {raw_slot_type!r}"
            ) from exc

    def _require_str(self, value: Any, field_name: str) -> str:
        if value is None:
            raise RecipeSpecMappingError(f"{field_name} is required.")
        result = str(value).strip()
        if not result:
            raise RecipeSpecMappingError(f"{field_name} must not be empty.")
        return result