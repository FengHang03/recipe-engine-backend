from __future__ import annotations

import logging
from typing import Any, Dict, List, Literal, Optional, Tuple

from pydantic import BaseModel, Field, model_validator

from app.shared.contracts.pet import PetProfile
from app.shared.contracts.ingredient import IngredientProfile
from app.shared.contracts.enums import FoodGroup, SlotType
from app.domains.recipe_generation.contracts.recipe_spec import (
    PresetRecipeItem,
    PresetRecipeSpec,
)
from app.domains.recipe_generation.contracts.results import WeightedIngredient

logger = logging.getLogger(__name__)

_RATIO_SUM_TOLERANCE = 0.02


class PresetScalingError(ValueError):
    """Raised when preset scaling cannot be completed."""


class PresetScaleResult(BaseModel):
    # 主体食材
    core_weights: List[WeightedIngredient] = Field(default_factory=list)

    # 补剂
    supplement_weights: List[WeightedIngredient] = Field(default_factory=list)

    # 汇总（core + supplement）
    all_weights: List[WeightedIngredient] = Field(default_factory=list)

    core_total_weight_grams: float = 0.0
    supplement_total_weight_grams: float = 0.0
    total_weight_grams: float = 0.0

    core_total_kcal: float = 0.0
    supplement_total_kcal: float = 0.0
    total_kcal: float = 0.0

    used_supplements: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    debug_meta: Dict[str, Any] = Field(default_factory=dict)


class PresetWeightResolution(BaseModel):
    ingredient_id: str
    ingredient_name: Optional[str] = None
    pet_weight_kg: float

    resolved_weight_g: float
    resolution_mode: str  # exact_hit / interpolated / lower_clamp / upper_clamp / single_anchor / base_weight_fallback

    lower_anchor_weight_kg: Optional[float] = None
    lower_anchor_ingredient_weight_g: Optional[float] = None
    upper_anchor_weight_kg: Optional[float] = None
    upper_anchor_ingredient_weight_g: Optional[float] = None

    warning: Optional[str] = None


class PresetScaler:
    """
    Pure preset scaling engine.

    Design:
    1. Split preset items into:
       - core foods
       - supplements
    2. Scale core foods to pet_profile.daily_calories_kcal using base_ratio
       (or base_weight_g fallback for core fixed items)
    3. Compute supplements AFTER core foods
       - supplements do NOT participate in food ratio %
       - supplement grams can currently come from:
         a) base_weight_g  -> fixed grams
         b) base_ratio     -> pct of core total weight
    4. Return PresetScaleResult with core/supplement separated

    Notes:
    - No DB access
    - Ingredient profiles must already be hydrated
    - First version focuses on SCALE_PRESET
    - Future supplement strategies such as per_kg_bw / tier_by_weight can be
      added in `_resolve_supplement_weight()`
    """

    def scale_to_target_calories(
        self,
        preset: PresetRecipeSpec,
        pet_profile: PetProfile,
        ingredient_profiles: Dict[str, IngredientProfile],
    ) -> PresetScaleResult:
        target_kcal = float(pet_profile.daily_calories_kcal or 0.0)
        if target_kcal <= 0:
            raise PresetScalingError("pet_profile.daily_calories_kcal must be > 0")

        items: List[PresetRecipeItem] = list(
            getattr(preset, "items", None) or getattr(preset, "ingredients", [])
        )
        if not items:
            raise PresetScalingError(
                f"PresetRecipeSpec '{preset.recipe_id}' has no items."
            )

        core_items, supplement_items = self._split_items(items, ingredient_profiles)

        if not core_items:
            raise PresetScalingError(
                f"PresetRecipeSpec '{preset.recipe_id}' has no core food items."
            )

        warnings: List[str] = []

        core_weights, core_total_weight_g, core_total_kcal = self._scale_core_items(
            preset=preset,
            pet_profile=pet_profile,
            core_items=core_items,
            ingredient_profiles=ingredient_profiles,
            warnings=warnings,
        )

        supplement_weights, supplement_total_weight_g, supplement_total_kcal = (
            self._scale_supplement_items(
                preset=preset,
                pet_profile=pet_profile,
                supplement_items=supplement_items,
                ingredient_profiles=ingredient_profiles,
                core_total_weight_g=core_total_weight_g,
                warnings=warnings,
            )
        )

        all_weights = [*core_weights, *supplement_weights]
        total_weight_g = core_total_weight_g + supplement_total_weight_g
        total_kcal = core_total_kcal + supplement_total_kcal

        used_supplements = sorted(
            {w.ingredient_id for w in supplement_weights if w.is_supplement}
        )

        debug_meta: Dict[str, Any] = {
            "preset_recipe_id": preset.recipe_id,
            "preset_name": getattr(preset, "name", None),
            "target_kcal": round(target_kcal, 4),
            "core_item_count": len(core_items),
            "supplement_item_count": len(supplement_items),
            "core_total_weight_g": round(core_total_weight_g, 4),
            "supplement_total_weight_g": round(supplement_total_weight_g, 4),
            "total_weight_g": round(total_weight_g, 4),
            "core_total_kcal": round(core_total_kcal, 4),
            "supplement_total_kcal": round(supplement_total_kcal, 4),
            "total_kcal": round(total_kcal, 4),
            "basis_kcal": getattr(preset, "basis_kcal", None),
            "basis_total_weight_g": getattr(preset, "basis_total_weight_g", None),
        }

        return PresetScaleResult(
            core_weights=core_weights,
            supplement_weights=supplement_weights,
            all_weights=all_weights,
            core_total_weight_grams=round(core_total_weight_g, 4),
            supplement_total_weight_grams=round(supplement_total_weight_g, 4),
            total_weight_grams=round(total_weight_g, 4),
            core_total_kcal=round(core_total_kcal, 4),
            supplement_total_kcal=round(supplement_total_kcal, 4),
            total_kcal=round(total_kcal, 4),
            used_supplements=used_supplements,
            warnings=warnings,
            debug_meta=debug_meta,
        )


    # ---------------------------------------------------------------------
    # calculate core foods by weight ratio
    #----------------------------------------------------------------------
    def scale_to_target_calories_by_weight_ratio(
        self,
        preset: PresetRecipeSpec,
        pet_profile: PetProfile,
        ingredient_profiles: Dict[str, IngredientProfile],
    ) -> PresetScaleResult:
        target_kcal = float(pet_profile.daily_calories_kcal or 0.0)
        if target_kcal <= 0:
            raise PresetScalingError("pet_profile.daily_calories_kcal must be > 0")

        items: List[PresetRecipeItem] = list(
            getattr(preset, "items", None) or getattr(preset, "ingredients", [])
        )
        if not items:
            raise PresetScalingError(
                f"PresetRecipeSpec '{preset.recipe_id}' has no items."
            )

        core_items, supplement_items = self._split_items(items, ingredient_profiles)

        if not core_items:
            raise PresetScalingError(
                f"PresetRecipeSpec '{preset.recipe_id}' has no core food items."
            )

        warnings: List[str] = []

        core_weights, core_total_weight_g, core_total_kcal = (
            self._scale_core_items_by_weight_ratio(
                preset=preset,
                pet_profile=pet_profile,
                core_items=core_items,
                ingredient_profiles=ingredient_profiles,
                warnings=warnings,
            )
        )

        supplement_weights, supplement_total_weight_g, supplement_total_kcal = (
            self._scale_supplement_items(
                preset=preset,
                pet_profile=pet_profile,
                supplement_items=supplement_items,
                ingredient_profiles=ingredient_profiles,
                core_total_weight_g=core_total_weight_g,
                warnings=warnings,
            )
        )

        all_weights = [*core_weights, *supplement_weights]
        total_weight_g = core_total_weight_g + supplement_total_weight_g
        total_kcal = core_total_kcal + supplement_total_kcal

        used_supplements = sorted(
            {w.ingredient_id for w in supplement_weights if w.is_supplement}
        )

        debug_meta: Dict[str, Any] = {
            "preset_recipe_id": preset.recipe_id,
            "preset_name": getattr(preset, "name", None),
            "target_kcal": round(target_kcal, 4),
            "core_item_count": len(core_items),
            "supplement_item_count": len(supplement_items),
            "core_total_weight_g": round(core_total_weight_g, 4),
            "supplement_total_weight_g": round(supplement_total_weight_g, 4),
            "total_weight_g": round(total_weight_g, 4),
            "core_total_kcal": round(core_total_kcal, 4),
            "supplement_total_kcal": round(supplement_total_kcal, 4),
            "total_kcal": round(total_kcal, 4),
            "basis_kcal": getattr(preset, "basis_kcal", None),
            "basis_total_weight_g": getattr(preset, "basis_total_weight_g", None),
            "core_ratio_mode": "weight_ratio",
        }

        return PresetScaleResult(
            core_weights=core_weights,
            supplement_weights=supplement_weights,
            all_weights=all_weights,
            core_total_weight_grams=round(core_total_weight_g, 4),
            supplement_total_weight_grams=round(supplement_total_weight_g, 4),
            total_weight_grams=round(total_weight_g, 4),
            core_total_kcal=round(core_total_kcal, 4),
            supplement_total_kcal=round(supplement_total_kcal, 4),
            total_kcal=round(total_kcal, 4),
            used_supplements=used_supplements,
            warnings=warnings,
            debug_meta=debug_meta,
        )
        

    # ---------------------------------------------------------------------
    # calculate core foods by weight list
    #----------------------------------------------------------------------

    def resolve_preset_weights_by_pet_weight(
        self,
        preset: PresetRecipeSpec,
        pet_profile: PetProfile,
        ingredient_profiles: Dict[str, IngredientProfile],
    ) -> PresetScaleResult:
        pet_weight_kg = float(pet_profile.weight_kg or 0.0)
        if pet_weight_kg <= 0:
            raise PresetScalingError("pet_profile.weight_kg must be > 0")

        items: List[PresetRecipeItem] = list(
            getattr(preset, "items", None) or getattr(preset, "ingredients", [])
        )
        if not items:
            raise PresetScalingError(
                f"PresetRecipeSpec '{preset.recipe_id}' has no items."
            )

        core_items, supplement_items = self._split_items(items, ingredient_profiles)

        warnings: List[str] = []
        resolution_traces: List[Dict[str, Any]] = []

        core_weights, core_total_weight_g, core_total_kcal = self._resolve_items_by_pet_weight(
            items=core_items,
            pet_weight_kg=pet_weight_kg,
            ingredient_profiles=ingredient_profiles,
            warnings=warnings,
            resolution_traces=resolution_traces,
            is_supplement=False,
        )

        supplement_weights, supplement_total_weight_g, supplement_total_kcal = self._resolve_items_by_pet_weight(
            items=supplement_items,
            pet_weight_kg=pet_weight_kg,
            ingredient_profiles=ingredient_profiles,
            warnings=warnings,
            resolution_traces=resolution_traces,
            is_supplement=True,
        )

        all_weights = [*core_weights, *supplement_weights]
        total_weight_g = core_total_weight_g + supplement_total_weight_g
        total_kcal = core_total_kcal + supplement_total_kcal

        used_supplements = sorted(
            {w.ingredient_id for w in supplement_weights if w.is_supplement}
        )

        if core_total_weight_g > 0:
            for w in core_weights:
                w.pct_of_recipe = round((w.weight_grams / core_total_weight_g) * 100.0, 4)

        debug_meta: Dict[str, Any] = {
            "preset_recipe_id": preset.recipe_id,
            "preset_name": getattr(preset, "name", None),
            "pet_weight_kg": round(pet_weight_kg, 4),
            "weight_resolution_mode": getattr(preset, "weight_resolution_mode", None),
            "core_item_count": len(core_items),
            "supplement_item_count": len(supplement_items),
            "core_total_weight_g": round(core_total_weight_g, 4),
            "supplement_total_weight_g": round(supplement_total_weight_g, 4),
            "total_weight_g": round(total_weight_g, 4),
            "core_total_kcal": round(core_total_kcal, 4),
            "supplement_total_kcal": round(supplement_total_kcal, 4),
            "total_kcal": round(total_kcal, 4),
            "item_resolutions": resolution_traces,
        }

        return PresetScaleResult(
            core_weights=core_weights,
            supplement_weights=supplement_weights,
            all_weights=all_weights,
            core_total_weight_grams=round(core_total_weight_g, 4),
            supplement_total_weight_grams=round(supplement_total_weight_g, 4),
            total_weight_grams=round(total_weight_g, 4),
            core_total_kcal=round(core_total_kcal, 4),
            supplement_total_kcal=round(supplement_total_kcal, 4),
            total_kcal=round(total_kcal, 4),
            used_supplements=used_supplements,
            warnings=warnings,
            debug_meta=debug_meta,
        )

    # ------------------------------------------------------------------
    # Phase 1: split items
    # ------------------------------------------------------------------

    def _split_items(
        self,
        items: List[PresetRecipeItem],
        ingredient_profiles: Dict[str, IngredientProfile],
    ) -> Tuple[List[PresetRecipeItem], List[PresetRecipeItem]]:
        core_items: List[PresetRecipeItem] = []
        supplement_items: List[PresetRecipeItem] = []

        missing_ingredient_ids: List[str] = []

        for item in items:
            ingredient_id = item.ingredient.ingredient_id
            profile = ingredient_profiles.get(ingredient_id)

            if profile is None:
                missing_ingredient_ids.append(ingredient_id)
                continue

            if self._is_supplement(item, profile):
                supplement_items.append(item)
            else:
                core_items.append(item)

        if missing_ingredient_ids:
            raise PresetScalingError(
                "Missing ingredient profiles for preset items: "
                + ", ".join(sorted(set(missing_ingredient_ids)))
            )

        return core_items, supplement_items

    def _is_supplement(
        self,
        item: PresetRecipeItem,
        profile: IngredientProfile,
    ) -> bool:
        """
        Supplement detection priority:
        1. profile.is_supplement == True
        2. item.ingredient.food_group == SUPPLEMENT
        """
        if bool(getattr(profile, "is_supplement", False)):
            return True

        food_group: Optional[FoodGroup | str] = getattr(item.ingredient, "food_group", None)

        # enum instance
        if isinstance(food_group, FoodGroup):
            return food_group in (FoodGroup.SUPPLEMENT, FoodGroup.FAT_OIL)

        # string fallback
        if food_group is not None and str(food_group).upper() == "SUPPLEMENT":
            return True

        return False

    def _resolve_items_by_pet_weight(
        self,
        items: List[PresetRecipeItem],
        pet_weight_kg: float,
        ingredient_profiles: Dict[str, IngredientProfile],
        warnings: List[str],
        resolution_traces: List[Dict[str, Any]],
        is_supplement: bool,
    ) -> Tuple[List[WeightedIngredient], float, float]:
        if not items:
            return [], 0.0, 0.0

        weights: List[WeightedIngredient] = []
        total_weight_g = 0.0
        total_kcal = 0.0

        for item in items:
            ingredient_id = item.ingredient.ingredient_id
            profile = ingredient_profiles.get(ingredient_id)
            if profile is None:
                raise PresetScalingError(
                    f"Missing ingredient profile for preset item '{ingredient_id}'."
                )

            resolution = self._resolve_item_weight_for_pet(
                item=item,
                pet_weight_kg=pet_weight_kg,
            )

            weight_g = float(resolution.resolved_weight_g)
            if weight_g < 0:
                raise PresetScalingError(
                    f"Resolved negative weight for ingredient '{ingredient_id}'."
                )

            kcal = self._compute_item_kcal(profile, weight_g)

            total_weight_g += weight_g
            total_kcal += kcal

            weights.append(
                self._make_weighted_ingredient(
                    item=item,
                    profile=profile,
                    weight_g=weight_g,
                    pct_of_recipe=None,
                    is_supplement=is_supplement,
                )
            )

            if resolution.warning:
                warnings.append(
                    f"{ingredient_id}: {resolution.warning}"
                )

            resolution_traces.append(
                {
                    "ingredient_id": resolution.ingredient_id,
                    "ingredient_name": resolution.ingredient_name,
                    "pet_weight_kg": round(resolution.pet_weight_kg, 4),
                    "resolved_weight_g": round(resolution.resolved_weight_g, 4),
                    "resolution_mode": resolution.resolution_mode,
                    "lower_anchor": (
                        {
                            "weight_kg": round(resolution.lower_anchor_weight_kg, 4),
                            "ingredient_weight_g": round(resolution.lower_anchor_ingredient_weight_g, 4),
                        }
                        if resolution.lower_anchor_weight_kg is not None
                        and resolution.lower_anchor_ingredient_weight_g is not None
                        else None
                    ),
                    "upper_anchor": (
                        {
                            "weight_kg": round(resolution.upper_anchor_weight_kg, 4),
                            "ingredient_weight_g": round(resolution.upper_anchor_ingredient_weight_g, 4),
                        }
                        if resolution.upper_anchor_weight_kg is not None
                        and resolution.upper_anchor_ingredient_weight_g is not None
                        else None
                    ),
                    "warning": resolution.warning,
                    "is_supplement": is_supplement,
                }
            )

        return weights, total_weight_g, total_kcal

    def _resolve_item_weight_for_pet(
        self,
        item: PresetRecipeItem,
        pet_weight_kg: float,
    ) -> PresetWeightResolution:
        ingredient_id = item.ingredient.ingredient_id
        ingredient_name = (
            getattr(item.ingredient, "short_name", None)
            or getattr(item.ingredient, "description", None)
            or ingredient_id
        )

        weight_curve = list(getattr(item, "weight_curve", []) or [])

        if weight_curve:
            return self._interpolate_weight_curve(
                ingredient_id=ingredient_id,
                ingredient_name=ingredient_name,
                weight_curve=weight_curve,
                pet_weight_kg=pet_weight_kg,
            )

        if item.base_weight_g is not None:
            return PresetWeightResolution(
                ingredient_id=ingredient_id,
                ingredient_name=ingredient_name,
                pet_weight_kg=pet_weight_kg,
                resolved_weight_g=float(item.base_weight_g),
                resolution_mode="base_weight_fallback",
                warning="weight_curve missing; used legacy base_weight_g",
            )

        raise PresetScalingError(
            f"Preset item '{ingredient_id}' has neither weight_curve nor base_weight_g."
        )

    # ------------------------------------------------------------------
    # Phase 2: core foods
    # ------------------------------------------------------------------

    def _scale_core_items_by_weight_ratio(
        self,
        preset: PresetRecipeSpec,
        pet_profile: PetProfile,
        core_items: List[PresetRecipeItem],
        ingredient_profiles: Dict[str, IngredientProfile],
        warnings: List[str],
    ) -> Tuple[List[WeightedIngredient], float, float]:
        """
        Solve core ratio items by WEIGHT ratio.

        Semantics:
        - item.base_ratio means pct of core-food weight
        - fixed core items (base_weight_g with no base_ratio) are resolved first
        - remaining target kcal is used to solve a single core_total_weight_g
        for ratio items
        """
        target_kcal = float(pet_profile.daily_calories_kcal or 0.0)

        ratio_items = [item for item in core_items if item.base_ratio is not None]
        fixed_items = [item for item in core_items if item.base_ratio is None]

        if not ratio_items and not fixed_items:
            raise PresetScalingError("No resolvable core items found.")

        fixed_weights: List[WeightedIngredient] = []
        fixed_total_weight_g = 0.0
        fixed_total_kcal = 0.0

        # 1) fixed core items first
        for item in fixed_items:
            ingredient_id = item.ingredient.ingredient_id
            profile = ingredient_profiles[ingredient_id]

            if item.base_weight_g is None:
                raise PresetScalingError(
                    f"Core item '{ingredient_id}' must define base_ratio or base_weight_g."
                )

            weight_g = float(item.base_weight_g)
            if weight_g < 0:
                raise PresetScalingError(
                    f"Core item '{ingredient_id}' has negative base_weight_g."
                )

            kcal = self._compute_item_kcal(profile, weight_g)

            fixed_total_weight_g += weight_g
            fixed_total_kcal += kcal

            fixed_weights.append(
                self._make_weighted_ingredient(
                    item=item,
                    profile=profile,
                    weight_g=weight_g,
                    pct_of_recipe=None,
                    is_supplement=False,
                )
            )

        remaining_kcal = target_kcal - fixed_total_kcal
        if remaining_kcal <= 0 and ratio_items:
            raise PresetScalingError(
                f"Core fixed items already consume all target calories. "
                f"target_kcal={target_kcal:.4f}, fixed_total_kcal={fixed_total_kcal:.4f}"
            )

        ratio_weights: List[WeightedIngredient] = []
        ratio_total_weight_g = 0.0
        ratio_total_kcal = 0.0

        if ratio_items:
            self._validate_core_ratios(ratio_items, preset.recipe_id)

            raw_ratio_sum = sum(float(item.base_ratio) for item in ratio_items)
            if raw_ratio_sum <= 0:
                raise PresetScalingError(
                    f"PresetRecipeSpec '{preset.recipe_id}' has non-positive ratio sum."
                )

            normalized_ratios = {
                item.ingredient.ingredient_id: float(item.base_ratio) / raw_ratio_sum
                for item in ratio_items
            }

            if abs(raw_ratio_sum - 1.0) > _RATIO_SUM_TOLERANCE:
                warnings.append(
                    f"Core ratio sum={raw_ratio_sum:.4f}; ratios were normalized internally."
                )

            # 2) solve one total ratio-weight from target kcal
            kcal_per_gram_weighted_sum = 0.0

            for item in ratio_items:
                ingredient_id = item.ingredient.ingredient_id
                profile = ingredient_profiles[ingredient_id]

                energy_per_100g = getattr(profile, "energy_per_100g", None)
                if energy_per_100g is None or float(energy_per_100g) <= 0:
                    raise PresetScalingError(
                        f"Core ratio item '{ingredient_id}' is missing positive energy_per_100g."
                    )

                kcal_per_gram = float(energy_per_100g) / 100.0
                kcal_per_gram_weighted_sum += (
                    normalized_ratios[ingredient_id] * kcal_per_gram
                )

            if kcal_per_gram_weighted_sum <= 0:
                raise PresetScalingError(
                    f"PresetRecipeSpec '{preset.recipe_id}' produced non-positive "
                    "weighted kcal-per-gram sum for ratio items."
                )

            solved_ratio_total_weight_g = remaining_kcal / kcal_per_gram_weighted_sum

            if solved_ratio_total_weight_g <= 0:
                raise PresetScalingError(
                    f"PresetRecipeSpec '{preset.recipe_id}' produced non-positive "
                    "ratio total weight."
                )

            # 3) distribute grams by normalized weight ratios
            for item in ratio_items:
                ingredient_id = item.ingredient.ingredient_id
                profile = ingredient_profiles[ingredient_id]

                weight_g = solved_ratio_total_weight_g * normalized_ratios[ingredient_id]
                kcal = self._compute_item_kcal(profile, weight_g)

                ratio_total_weight_g += weight_g
                ratio_total_kcal += kcal

                ratio_weights.append(
                    self._make_weighted_ingredient(
                        item=item,
                        profile=profile,
                        weight_g=weight_g,
                        pct_of_recipe=None,
                        is_supplement=False,
                    )
                )

        core_weights = [*fixed_weights, *ratio_weights]
        core_total_weight_g = fixed_total_weight_g + ratio_total_weight_g
        core_total_kcal = fixed_total_kcal + ratio_total_kcal

        if core_total_weight_g <= 0:
            raise PresetScalingError("Core foods produced non-positive total weight.")

        # pct_of_recipe is computed only within core foods
        for w in core_weights:
            w.pct_of_recipe = round((w.weight_grams / core_total_weight_g) * 100.0, 4)

        if target_kcal > 0:
            realized_ratio = core_total_kcal / target_kcal
            if realized_ratio < 0.95 or realized_ratio > 1.05:
                warnings.append(
                    f"Core total kcal ({core_total_kcal:.2f}) deviates from target "
                    f"({target_kcal:.2f})."
                )

        return core_weights, core_total_weight_g, core_total_kcal


    def _scale_core_items(
        self,
        preset: PresetRecipeSpec,
        pet_profile: PetProfile,
        core_items: List[PresetRecipeItem],
        ingredient_profiles: Dict[str, IngredientProfile],
        warnings: List[str],
    ) -> Tuple[List[WeightedIngredient], float, float]:
        """
        Core foods are scaled to target calories.

        Rules:
        - ratio items:
            weight is solved from calorie allocation by base_ratio
        - fixed core items:
            currently allowed via base_weight_g
            their kcal is first reserved from target_kcal
        - ratio items are normalized only inside ratio group
        - supplements are excluded entirely from this stage
        """
        target_kcal = float(pet_profile.daily_calories_kcal or 0.0)

        ratio_items = [item for item in core_items if item.base_ratio is not None]
        fixed_items = [item for item in core_items if item.base_ratio is None]

        if not ratio_items and not fixed_items:
            raise PresetScalingError("No resolvable core items found.")

        fixed_weights: List[WeightedIngredient] = []
        fixed_total_weight_g = 0.0
        fixed_total_kcal = 0.0

        # 1) Resolve fixed core items first
        for item in fixed_items:
            ingredient_id = item.ingredient.ingredient_id
            profile = ingredient_profiles[ingredient_id]

            if item.base_weight_g is None:
                raise PresetScalingError(
                    f"Core item '{ingredient_id}' must define base_ratio or base_weight_g."
                )

            weight_g = float(item.base_weight_g)
            if weight_g < 0:
                raise PresetScalingError(
                    f"Core item '{ingredient_id}' has negative base_weight_g."
                )

            kcal = self._compute_item_kcal(profile, weight_g)

            fixed_total_weight_g += weight_g
            fixed_total_kcal += kcal

            fixed_weights.append(
                self._make_weighted_ingredient(
                    item=item,
                    profile=profile,
                    weight_g=weight_g,
                    pct_of_recipe=None,  # filled later against core total only
                    is_supplement=False,
                )
            )

        remaining_kcal = target_kcal - fixed_total_kcal
        if remaining_kcal <= 0 and ratio_items:
            raise PresetScalingError(
                f"Core fixed items already consume all target calories. "
                f"target_kcal={target_kcal:.4f}, fixed_total_kcal={fixed_total_kcal:.4f}"
            )

        # 2) Resolve ratio core items by calorie allocation
        ratio_weights: List[WeightedIngredient] = []
        ratio_total_weight_g = 0.0
        ratio_total_kcal = 0.0

        if ratio_items:
            self._validate_core_ratios(ratio_items, preset.recipe_id)

            raw_ratio_sum = sum(float(item.base_ratio) for item in ratio_items)
            if raw_ratio_sum <= 0:
                raise PresetScalingError(
                    f"PresetRecipeSpec '{preset.recipe_id}' has non-positive ratio sum."
                )

            normalized_ratios = {
                item.ingredient.ingredient_id: float(item.base_ratio) / raw_ratio_sum
                for item in ratio_items
            }

            if abs(raw_ratio_sum - 1.0) > _RATIO_SUM_TOLERANCE:
                warnings.append(
                    f"Core ratio sum={raw_ratio_sum:.4f}; ratios were normalized internally."
                )

            for item in ratio_items:
                ingredient_id = item.ingredient.ingredient_id
                profile = ingredient_profiles[ingredient_id]

                energy_per_100g = getattr(profile, "energy_per_100g", None)
                if energy_per_100g is None or float(energy_per_100g) <= 0:
                    raise PresetScalingError(
                        f"Core ratio item '{ingredient_id}' is missing positive energy_per_100g."
                    )

                allocated_kcal = remaining_kcal * normalized_ratios[ingredient_id]
                weight_g = (allocated_kcal / float(energy_per_100g)) * 100.0

                if weight_g < 0:
                    raise PresetScalingError(
                        f"Core ratio item '{ingredient_id}' produced negative weight."
                    )

                kcal = self._compute_item_kcal(profile, weight_g)

                ratio_total_weight_g += weight_g
                ratio_total_kcal += kcal

                ratio_weights.append(
                    self._make_weighted_ingredient(
                        item=item,
                        profile=profile,
                        weight_g=weight_g,
                        pct_of_recipe=None,  # filled later against core total only
                        is_supplement=False,
                    )
                )

        core_weights = [*fixed_weights, *ratio_weights]
        core_total_weight_g = fixed_total_weight_g + ratio_total_weight_g
        core_total_kcal = fixed_total_kcal + ratio_total_kcal

        if core_total_weight_g <= 0:
            raise PresetScalingError("Core foods produced non-positive total weight.")

        # only core foods participate in food ratio %
        for w in core_weights:
            w.pct_of_recipe = round((w.weight_grams / core_total_weight_g) * 100.0, 4)

        # scale sanity warnings
        if target_kcal > 0:
            realized_ratio = core_total_kcal / target_kcal
            if realized_ratio < 0.95 or realized_ratio > 1.05:
                warnings.append(
                    f"Core total kcal ({core_total_kcal:.2f}) deviates from target "
                    f"({target_kcal:.2f})."
                )

        return core_weights, core_total_weight_g, core_total_kcal

    def _validate_core_ratios(
        self,
        ratio_items: List[PresetRecipeItem],
        recipe_id: str,
    ) -> None:
        missing = [
            item.ingredient.ingredient_id
            for item in ratio_items
            if item.base_ratio is None
        ]
        if missing:
            raise PresetScalingError(
                f"PresetRecipeSpec '{recipe_id}': missing base_ratio for core ratio items: {missing}"
            )

        non_positive = [
            item.ingredient.ingredient_id
            for item in ratio_items
            if item.base_ratio is not None and float(item.base_ratio) <= 0
        ]
        if non_positive:
            raise PresetScalingError(
                f"PresetRecipeSpec '{recipe_id}': non-positive base_ratio for items: {non_positive}"
            )

    # ------------------------------------------------------------------
    # Phase 3: supplements
    # ------------------------------------------------------------------

    def _scale_supplement_items(
        self,
        preset: PresetRecipeSpec,
        pet_profile: PetProfile,
        supplement_items: List[PresetRecipeItem],
        ingredient_profiles: Dict[str, IngredientProfile],
        core_total_weight_g: float,
        warnings: List[str],
    ) -> Tuple[List[WeightedIngredient], float, float]:
        """
        Supplements are computed AFTER core foods.

        Current support:
        - if base_weight_g is provided -> fixed grams
        - elif base_ratio is provided -> interpret as pct_of_core_weight
          e.g. 0.003 => 0.3% of core total weight

        Future extensions:
        - per_kg_bw
        - tier_by_weight
        - nutrient-gap driven dosing
        """
        if not supplement_items:
            return [], 0.0, 0.0

        weights: List[WeightedIngredient] = []
        total_weight_g = 0.0
        total_kcal = 0.0

        for item in supplement_items:
            ingredient_id = item.ingredient.ingredient_id
            profile = ingredient_profiles[ingredient_id]

            weight_g = self._resolve_supplement_weight(
                item=item,
                pet_profile=pet_profile,
                core_total_weight_g=core_total_weight_g,
            )

            if weight_g < 0:
                raise PresetScalingError(
                    f"Supplement item '{ingredient_id}' produced negative weight."
                )

            kcal = self._compute_item_kcal(profile, weight_g)

            total_weight_g += weight_g
            total_kcal += kcal

            weights.append(
                self._make_weighted_ingredient(
                    item=item,
                    profile=profile,
                    weight_g=weight_g,
                    pct_of_recipe=None,  # supplements do not count in food %
                    is_supplement=True,
                )
            )

        if total_weight_g > 0 and core_total_weight_g > 0:
            supplement_pct_vs_core = (total_weight_g / core_total_weight_g) * 100.0
            if supplement_pct_vs_core > 10:
                warnings.append(
                    f"Supplements total {supplement_pct_vs_core:.2f}% of core food weight, which is unusually high."
                )

        return weights, total_weight_g, total_kcal

    def _resolve_supplement_weight(
        self,
        item: PresetRecipeItem,
        pet_profile: PetProfile,
        core_total_weight_g: float,
    ) -> float:
        """
        Current supplement resolution priority:
        1. base_weight_g -> fixed grams
        2. base_ratio    -> pct_of_core_weight

        Example:
        - base_weight_g=5.0   => 5g fixed
        - base_ratio=0.003    => 0.3% of core food total weight
        """
        if item.base_weight_g is not None:
            return float(item.base_weight_g)

        if item.base_ratio is not None:
            if core_total_weight_g <= 0:
                raise PresetScalingError(
                    f"Cannot resolve supplement '{item.ingredient.ingredient_id}' "
                    "by base_ratio because core_total_weight_g <= 0."
                )
            return float(item.base_ratio) * float(core_total_weight_g)

        raise PresetScalingError(
            f"Supplement item '{item.ingredient.ingredient_id}' must define "
            "base_weight_g or base_ratio."
        )

    # ------------------------------------------------------------------
    # Shared helpers
    # ------------------------------------------------------------------

    def _compute_item_kcal(
        self,
        ingredient: IngredientProfile,
        weight_g: float,
    ) -> float:
        energy_per_100g = getattr(ingredient, "energy_per_100g", None)
        if energy_per_100g is None:
            return 0.0
        return (float(weight_g) / 100.0) * float(energy_per_100g)

    def _make_weighted_ingredient(
        self,
        item: PresetRecipeItem,
        profile: IngredientProfile,
        weight_g: float,
        pct_of_recipe: Optional[float],
        is_supplement: bool,
    ) -> WeightedIngredient:
        return WeightedIngredient(
            ingredient_id=profile.ingredient_id,
            ingredient_name=(
                getattr(profile, "short_name", None)
                or getattr(profile, "description", None)
                or profile.ingredient_id
            ),
            short_name=getattr(profile, "short_name", None),
            slot_type=item.slot_type,
            weight_grams=round(float(weight_g), 4),
            pct_of_recipe=pct_of_recipe,
            is_supplement=bool(is_supplement),
            was_user_locked=False,
        )

    def _interpolate_weight_curve(
        self,
        ingredient_id: str,
        ingredient_name: Optional[str],
        weight_curve: List[Any],
        pet_weight_kg: float,
    ) -> PresetWeightResolution:
        points = sorted(
            weight_curve,
            key=lambda p: float(p.weight_kg),
        )

        if not points:
            raise PresetScalingError(
                f"Ingredient '{ingredient_id}' has an empty weight_curve."
            )

        # 基础校验
        seen_weights = set()
        for p in points:
            w = float(p.weight_kg)
            g = float(p.ingredient_weight_g)
            if w <= 0:
                raise PresetScalingError(
                    f"Ingredient '{ingredient_id}' has non-positive anchor weight_kg={w}."
                )
            if g < 0:
                raise PresetScalingError(
                    f"Ingredient '{ingredient_id}' has negative ingredient_weight_g={g}."
                )
            if w in seen_weights:
                raise PresetScalingError(
                    f"Ingredient '{ingredient_id}' has duplicated anchor weight_kg={w}."
                )
            seen_weights.add(w)

        if len(points) == 1:
            p = points[0]
            return PresetWeightResolution(
                ingredient_id=ingredient_id,
                ingredient_name=ingredient_name,
                pet_weight_kg=pet_weight_kg,
                resolved_weight_g=float(p.ingredient_weight_g),
                resolution_mode="single_anchor",
                lower_anchor_weight_kg=float(p.weight_kg),
                lower_anchor_ingredient_weight_g=float(p.ingredient_weight_g),
                warning="only one anchor point; interpolation not applied",
            )

        # exact hit
        for p in points:
            if abs(float(p.weight_kg) - pet_weight_kg) < 1e-9:
                return PresetWeightResolution(
                    ingredient_id=ingredient_id,
                    ingredient_name=ingredient_name,
                    pet_weight_kg=pet_weight_kg,
                    resolved_weight_g=float(p.ingredient_weight_g),
                    resolution_mode="exact_hit",
                    lower_anchor_weight_kg=float(p.weight_kg),
                    lower_anchor_ingredient_weight_g=float(p.ingredient_weight_g),
                )

        # lower clamp
        if pet_weight_kg < float(points[0].weight_kg):
            p = points[0]
            return PresetWeightResolution(
                ingredient_id=ingredient_id,
                ingredient_name=ingredient_name,
                pet_weight_kg=pet_weight_kg,
                resolved_weight_g=float(p.ingredient_weight_g),
                resolution_mode="lower_clamp",
                lower_anchor_weight_kg=float(p.weight_kg),
                lower_anchor_ingredient_weight_g=float(p.ingredient_weight_g),
                warning="pet weight below minimum anchor; clamped to minimum anchor",
            )

        # upper clamp
        if pet_weight_kg > float(points[-1].weight_kg):
            p = points[-1]
            return PresetWeightResolution(
                ingredient_id=ingredient_id,
                ingredient_name=ingredient_name,
                pet_weight_kg=pet_weight_kg,
                resolved_weight_g=float(p.ingredient_weight_g),
                resolution_mode="upper_clamp",
                lower_anchor_weight_kg=float(p.weight_kg),
                lower_anchor_ingredient_weight_g=float(p.ingredient_weight_g),
                warning="pet weight above maximum anchor; clamped to maximum anchor",
            )

        # interpolation
        for lower, upper in zip(points[:-1], points[1:]):
            lower_w = float(lower.weight_kg)
            upper_w = float(upper.weight_kg)

            if lower_w <= pet_weight_kg <= upper_w:
                lower_g = float(lower.ingredient_weight_g)
                upper_g = float(upper.ingredient_weight_g)

                if abs(upper_w - lower_w) < 1e-9:
                    resolved_g = lower_g
                else:
                    alpha = (pet_weight_kg - lower_w) / (upper_w - lower_w)
                    resolved_g = lower_g + alpha * (upper_g - lower_g)

                return PresetWeightResolution(
                    ingredient_id=ingredient_id,
                    ingredient_name=ingredient_name,
                    pet_weight_kg=pet_weight_kg,
                    resolved_weight_g=float(resolved_g),
                    resolution_mode="interpolated",
                    lower_anchor_weight_kg=lower_w,
                    lower_anchor_ingredient_weight_g=lower_g,
                    upper_anchor_weight_kg=upper_w,
                    upper_anchor_ingredient_weight_g=upper_g,
                )

        raise PresetScalingError(
            f"Failed to resolve weight curve for ingredient '{ingredient_id}'."
    )

    