from __future__ import annotations

import logging
import time
import uuid
from typing import Dict, List, Optional, Sequence, Tuple
from fractions import Fraction

from app.shared.contracts.ingredient import IngredientProfile, IngredientRef
from app.shared.contracts.enums import FoodGroup
from app.domains.recipe_generation.contracts.enums import (
    RecipeGenerationMode,
    SolveStatus,
)
from app.domains.recipe_generation.contracts.recipe_spec import (
    PresetRecipeItem, PresetRecipeSpec,
    PresetRecipeRef, RawPresetRecipeSpec, RawPresetRecipeItem,
)
from app.domains.recipe_generation.contracts.request import RecipeGenerationRequest
from app.domains.recipe_generation.contracts.results import (
    RecipeGenerationResult,
    WeightedIngredient,
)
from app.domains.recipe_generation.orchestration.validators.request_validator import (
    RecipeRequestValidator,
    RecipeRequestValidationError,
)
from app.domains.recipe_generation.orchestration.explain_payload_builder import (
    ExplainPayloadBuilder,
)
from app.domains.recipe_generation.engines.l2.l2_engine import L2Engine
from app.domains.recipe_generation.engines.scaling.preset_scaler import (
    PresetScaler,
    PresetScalingError,
)
from app.domains.nutrient_analysis.nutrient_analysis_service import (
    NutrientAnalysisService,
)
from app.domains.nutrient_analysis.input_preparation_service import (
    NutrientAnalysisInputPreparationService,
)
from app.domains.recipe_generation.infra.mappers.recipe_spec_mapper import (
    RecipeSpecMapper,
    RecipeSpecMappingError,
)
from app.domains.recipe_generation.infra.repositories.preset_recipe_repository import (
    PresetRecipeRepository,
)
from app.domains.ingredients.infra.ingredient_nutrients_repository import (
    IngredientNutrientsRepository,
)
from app.domains.ingredients.infra.ingredient_repository import (
    IngredientRepository,
)
from app.domains.recipe_generation.engines.diy.beginner_diy_preview import (
    BeginnerDiyPreviewService,
)
from app.domains.recipe_generation.contracts.aafco_config import AAFCO_STANDARDS
from app.shared.contracts.enums import LifeStage

logger = logging.getLogger(__name__)


class RecipeGenerationService:
    """
    Unified orchestration entry point for recipe generation.

    Current supported modes:
    - OPTIMIZE_FIXED_SET
    - SCALE_PRESET

    Responsibilities:
    1. Validate request
    2. Route by mode
    3. Load required data via repositories/loaders
    4. Call the correct engine / builder
    5. Normalize into RecipeGenerationResult
    6. Build explain payload

    Out of scope:
    - No direct DB SQL here
    - No LP formulation here
    - No raw preset storage here
    """

    def __init__(
        self,
        ingredient_repository: IngredientRepository,
        ingredient_nutrients_repository: IngredientNutrientsRepository,
        preset_recipe_repository: PresetRecipeRepository,
        recipe_spec_mapper: RecipeSpecMapper,
        preset_scaler: PresetScaler,
        nutrient_analysis_service: NutrientAnalysisService,
        nutrient_analysis_input_preparation_service: NutrientAnalysisInputPreparationService,
        beginner_diy_preview_service: BeginnerDiyPreviewService,
        l2_engine: Optional[L2Engine] = None,
        request_validator: Optional[RecipeRequestValidator] = None,
        explain_payload_builder: Optional[ExplainPayloadBuilder] = None,
    ) -> None:
        self._ingredient_repository = ingredient_repository
        self._ingredient_nutrients_repository = ingredient_nutrients_repository
        self._preset_recipe_repository = preset_recipe_repository
        self._recipe_spec_mapper = recipe_spec_mapper
        self._preset_scaler = preset_scaler
        self._nutrient_analysis_service = nutrient_analysis_service
        self._input_preparation_service = nutrient_analysis_input_preparation_service
        self._beginner_diy_preview_service = beginner_diy_preview_service
        self._l2_engine = l2_engine
        self._request_validator = request_validator or RecipeRequestValidator()
        self._explain_payload_builder = explain_payload_builder or ExplainPayloadBuilder()

    # ------------------------------------------------------------------
    # Public entrypoint
    # ------------------------------------------------------------------

    async def generate(self, request: RecipeGenerationRequest) -> RecipeGenerationResult:
        if not getattr(request, "request_id", None):
            request.request_id = str(uuid.uuid4())

        started_at = time.perf_counter()

        try:
            self._request_validator.validate(request)
            result = await self._dispatch(request)
        except (
            RecipeRequestValidationError,
            RecipeSpecMappingError,
            PresetScalingError,
            ValueError,
        ) as exc:
            logger.warning("Recipe generation failed request_id=%s: %s", request.request_id, exc)
            result = self._make_error_result(request, str(exc))
        except NotImplementedError as exc:
            logger.error("Not implemented request_id=%s: %s", request.request_id, exc)
            result = self._make_error_result(request, str(exc))
        except Exception as exc:
            logger.exception("Unexpected error request_id=%s: %s", request.request_id, exc)
            result = self._make_error_result(request, f"Internal error: {exc}")

        if getattr(result, "solve_time_seconds", None) is None:
            result.solve_time_seconds = round(time.perf_counter() - started_at, 6)

        try:
            result.explanation_payload = self._explain_payload_builder.build(
                request.pet_profile,
                result,
            )
        except Exception as exc:
            logger.warning(
                "Explain payload build failed request_id=%s: %s",
                request.request_id,
                exc,
            )

        return result

    # ------------------------------------------------------------------
    # Dispatch
    # ------------------------------------------------------------------

    async def _dispatch(self, request: RecipeGenerationRequest) -> RecipeGenerationResult:
        if request.mode == RecipeGenerationMode.SCALE_PRESET:
            return await self._generate_scaled_preset(request)

        if request.mode == RecipeGenerationMode.OPTIMIZE_FIXED_SET:
            return await self._generate_fixed_set(request)

        if request.mode == RecipeGenerationMode.BEGINNER_DIY_PREVIEW:
            return await self._generate_beginner_diy_preview(request)

        if request.mode == RecipeGenerationMode.OPTIMIZE_USER_DEFINED:
            raise NotImplementedError("OPTIMIZE_USER_DEFINED is not yet implemented.")

        if request.mode == RecipeGenerationMode.PRESET_WITH_TOLERANCE:
            raise NotImplementedError("PRESET_WITH_TOLERANCE is not yet implemented.")

        raise NotImplementedError(f"Mode '{request.mode.value}' is not implemented.")

    # ------------------------------------------------------------------
    # OPTIMIZE_FIXED_SET
    # ------------------------------------------------------------------

    async def _generate_fixed_set(
        self,
        request: RecipeGenerationRequest,
    ) -> RecipeGenerationResult:
        assert request.combination_spec is not None
        if self._l2_engine is None:
            raise NotImplementedError("L2Engine is not configured.")

        combination = request.combination_spec
        started_at = time.perf_counter()

        ingredient_ids = combination.get_ingredient_ids()
        supplement_ids = self._get_supplement_ids(request)
        all_ids = self._dedupe_preserve_order(ingredient_ids + supplement_ids)

        ingredient_profiles = self._load_ingredient_profiles(all_ids)

        supplement_profiles = [
            ingredient_profiles[item_id]
            for item_id in supplement_ids
            if item_id in ingredient_profiles
        ]

        result = self._l2_engine.optimize_fixed_set(
            pet_profile=request.pet_profile,
            combination_spec=combination,
            supplement_toolkit=supplement_profiles,
        )

        if not getattr(result, "solve_time_seconds", None):
            result.solve_time_seconds = round(time.perf_counter() - started_at, 6)

        if not getattr(result, "recipe_id", None):
            result.recipe_id = combination.recipe_id

        self._apply_source_fields(
            result=result,
            source_type="combination",
            source_recipe_id=combination.recipe_id,
        )

        return result

    # ------------------------------------------------------------------
    # SCALE_PRESET
    # ------------------------------------------------------------------

    async def _generate_scaled_preset(
        self,
        request: RecipeGenerationRequest,
    ) -> RecipeGenerationResult:
        """
        SCALE_PRESET flow (unified nutrient-analysis version):

        1. Resolve raw preset -> mapped preset -> pet-resolved preset
        2. Build display weights from resolved raw grams
        3. Prepare unified nutrient analysis input from display weights
        4. Run nutrient analysis via NutrientAnalysisInput
        5. Build RecipeGenerationResult
        """
        assert request.preset_recipe_spec is not None

        started_at = time.perf_counter()

        # 1) resolve preset spec + hydrate ingredient profiles
        preset, ingredient_profiles = self._resolve_full_preset_spec(request)

        # 2) display weights (raw grams for frontend/result)
        display_weights = self._build_display_weights_from_resolved_preset(preset)

        total_weight_g = round(
            sum(float(w.weight_grams) for w in display_weights),
            6,
        )

        ingredient_nutrients_df = self._ingredient_nutrients_repository.get_nutrition_long_df()
        nutrient_metadata_df = self._ingredient_nutrients_repository.get_nutrient_metadata_df()

        # Prefer preset basis_kcal when available; otherwise fall back to pet energy
        target_energy_kcal = None
        if getattr(preset, "basis_kcal", None) is not None:
            target_energy_kcal = float(preset.basis_kcal)
        elif getattr(request.pet_profile, "daily_calories_kcal", None) is not None:
            target_energy_kcal = float(request.pet_profile.daily_calories_kcal)

        try:
            prepared_analysis = self._input_preparation_service.prepare_from_weighted_ingredients(
                weights=display_weights,
                ingredient_profiles=ingredient_profiles,
                ingredient_nutrients_df=ingredient_nutrients_df,
                nutrient_metadata_df=nutrient_metadata_df,
                nutrient_constraints=None,
                target_energy_kcal=target_energy_kcal,
                default_output_basis="per_recipe",
            )
        except Exception as exc:
            raise ValueError(f"failed to prepare preset nutrient analysis input: {exc}") from exc

        try:
            nutrient_analysis_result = self._nutrient_analysis_service.analyze(
                prepared_analysis.analysis_input
            )
        except Exception as exc:
            raise ValueError(f"preset nutrient analysis failed: {exc}") from exc

        warnings: List[str] = []
        warnings.extend(
            self._build_supplement_ratio_warnings(
                weights=display_weights,
                total_weight_g=total_weight_g,
            )
        )
        warnings.extend(nutrient_analysis_result.warnings)
        warnings = self._dedupe_preserve_order(warnings)

        result_kwargs = {
            "mode": RecipeGenerationMode.SCALE_PRESET,
            "status": SolveStatus.FEASIBLE,
            "recipe_id": f"scaled_{preset.recipe_id}",
            "total_weight_grams": total_weight_g,
            "weights": display_weights,
            "nutrient_analysis": list(nutrient_analysis_result.analyses),
            "used_supplements": [
                w.ingredient_id for w in display_weights if getattr(w, "is_supplement", False)
            ],
            "warnings": warnings,
            "debug_meta": {
                "generated_by": "preset_resolved_service_flow",
                "request_id": request.request_id,
                "requested_by": getattr(request, "requested_by", None),
                "preset_recipe_id": preset.recipe_id,
                "pet_weight_kg": float(request.pet_profile.weight_kg or 0.0),
                "analysis_debug": {
                    "source_items": [item.model_dump() for item in prepared_analysis.source_items],
                    "prep_results": [item.model_dump() for item in prepared_analysis.prep_results],
                    "analysis_items": [item.model_dump() for item in prepared_analysis.analysis_items],
                    "nutrient_analysis_debug_meta": nutrient_analysis_result.debug_meta,
                },
            },
            "solve_time_seconds": round(time.perf_counter() - started_at, 6),
        }

        result_kwargs.update(
            self._build_source_kwargs(
                source_type="preset",
                source_recipe_id=preset.recipe_id,
            )
        )

        return RecipeGenerationResult(**result_kwargs)

    # ------------------------------------------------------------------
    # BEGINNER DIY PREVIEW
    # ------------------------------------------------------------------

    async def _generate_beginner_diy_preview(
        self,
        request: RecipeGenerationRequest,
    ) -> RecipeGenerationResult:
        beginner_spec = getattr(request, "beginner_diy_spec", None)
        if beginner_spec is None:
            raise RecipeRequestValidationError(
                "beginner_diy_spec is required for BEGINNER_DIY_PREVIEW."
            )

        ingredient_ids = self._collect_beginner_diy_ingredient_ids(beginner_spec)
        ingredient_profiles = self._load_beginner_diy_analysis_ingredient_profiles(ingredient_ids)

        ingredient_nutrients_df = self._ingredient_nutrients_repository.get_nutrition_long_df()
        nutrient_metadata_df = self._ingredient_nutrients_repository.get_nutrient_metadata_df()
        nutrient_constraints = self._resolve_beginner_diy_nutrient_constraints(request)

        return self._beginner_diy_preview_service.build_preview(
            request=request,
            ingredient_profiles=ingredient_profiles,
            ingredient_nutrients_df=ingredient_nutrients_df,
            nutrient_metadata_df=nutrient_metadata_df,
            nutrient_constraints=nutrient_constraints,
        )

    # ------------------------------------------------------------------
    # Formal preset resolution
    # ------------------------------------------------------------------

    def _resolve_full_preset_spec(
        self,
        request: RecipeGenerationRequest,
    ) -> Tuple[PresetRecipeSpec, Dict[str, IngredientProfile]]:
        """
        Resolve a full PresetRecipeSpec plus hydrated ingredient profiles.

        Flow:
        1. Read raw preset JSON from repository by recipe_id
        2. Collect raw fdc_id values from preset ingredients
        3. Hydrate IngredientProfile objects by fdc_id
        4. Map raw preset JSON -> PresetRecipeSpec
        5. Resolve each item to current pet-specific raw grams
        6. Return resolved PresetRecipeSpec + ingredient profiles keyed by ingredient_id
        """
        preset_ref = request.preset_recipe_spec
        if preset_ref is None:
            raise RecipeRequestValidationError("preset_recipe_spec is required.")

        base_recipe_id = getattr(preset_ref, "recipe_id", None)
        if not base_recipe_id:
            raise RecipeRequestValidationError(
                "preset_recipe_spec.recipe_id is required for SCALE_PRESET."
            )

        recipe_id = self._resolve_preset_recipe_id_for_pet(
            base_recipe_id=base_recipe_id,
            request=request,
        )

        raw_preset_dict = self._load_raw_preset(recipe_id)
        raw_preset = self._recipe_spec_mapper.to_raw_preset_recipe_spec(raw_preset_dict)

        fdc_ids = self._dedupe_preserve_order([item.fdc_id for item in raw_preset.ingredients])
        ingredient_profiles_by_fdc_id = self._load_ingredient_profiles_by_fdc_ids(fdc_ids)

        missing_fdc_ids = [
            fdc_id for fdc_id in fdc_ids
            if fdc_id not in ingredient_profiles_by_fdc_id
        ]
        if missing_fdc_ids:
            raise RecipeSpecMappingError(
                f"Preset '{recipe_id}' references unknown fdc_id(s): "
                + ", ".join(sorted(set(missing_fdc_ids)))
            )

        pet_weight_kg = float(request.pet_profile.weight_kg or 0.0)
        if pet_weight_kg <= 0:
            raise RecipeRequestValidationError(
                "pet_profile.weight_kg must be > 0 for SCALE_PRESET."
            )

        resolved_preset = self._resolve_preset_items_for_pet(
            raw_preset=raw_preset,
            pet_weight_kg=pet_weight_kg,
            ingredient_profiles_by_fdc_id=ingredient_profiles_by_fdc_id,
        )

        ingredient_profiles_by_ingredient_id: Dict[str, IngredientProfile] = {}
        for profile in ingredient_profiles_by_fdc_id.values():
            ingredient_profiles_by_ingredient_id[str(profile.ingredient_id)] = profile

        ingredient_profiles_by_ingredient_id = self._augment_profiles_with_cooked_partners(
            ingredient_profiles_by_ingredient_id
        )

        return resolved_preset, ingredient_profiles_by_ingredient_id


    def _resolve_preset_recipe_id_for_pet(
        self,
        base_recipe_id: str,
        request: RecipeGenerationRequest,
    ) -> str:
        """
        Resolve preset recipe variant by pet life stage.

        Strategy:
        - puppy -> prefer "<base_recipe_id>_puppy"
        - otherwise -> prefer "<base_recipe_id>_adult"
        - if variant does not exist -> fallback to base_recipe_id
        """
        life_stage = str(getattr(request.pet_profile, "life_stage", "") or "").lower()

        def _stage_to_suffix(stage: str) -> Optional[str]:
            if "puppy" in stage or "growth" in stage:
                return "puppy"
            if "senior" in stage:
                return "senior"
            if "adult" in stage or "maintenance" in stage:
                return "adult"
            return None

        suffix = _stage_to_suffix(life_stage)

        if suffix:
            candidate = f"{base_recipe_id}_{suffix}"
            if (
                hasattr(self._preset_recipe_repository, "has_recipe")
                and self._preset_recipe_repository.has_recipe(candidate)
            ):
                return candidate

        adult_candidate = f"{base_recipe_id}_adult"
        if (
            hasattr(self._preset_recipe_repository, "has_recipe")
            and self._preset_recipe_repository.has_recipe(adult_candidate)
        ):
            return adult_candidate

        # 3) 最后 fallback 到 base
        return base_recipe_id


    # ------------------------------------------------------------------
    # Build display weights / analysis inputs
    # ------------------------------------------------------------------

    def _build_display_weights_from_resolved_preset(
        self,
        preset: PresetRecipeSpec,
    ) -> List[WeightedIngredient]:
        """
        Convert resolved preset items into display/result weights.

        Conventions:
        - display weight = resolved raw grams
        - pct_of_recipe computed on total raw display grams
        - supplement detection no longer depends on raw preset fields
        """
        weights: List[WeightedIngredient] = []

        for item in preset.ingredients:
            resolved_weight_g = getattr(item, "resolved_weight_g", None)
            if resolved_weight_g is None:
                raise RecipeSpecMappingError(
                    f"Preset '{preset.recipe_id}' contains unresolved item: "
                    f"{item.ingredient.short_name or item.ingredient.ingredient_id}"
                )

            slot_str = str(item.slot_type).upper()
            prep_state = str(getattr(item.ingredient, "prep_state", "") or "").lower()
            food_group = str(getattr(item.ingredient, "food_group", "") or "").upper()

            is_supplement = (
                prep_state == "supplement"
                or food_group == "SUPPLEMENT"
                or "SUPPLEMENT" in slot_str
            )

            display_unit = getattr(item, "resolved_unit", None) or "g"

            if display_unit == "g":
                display_amount = round(float(resolved_weight_g), 6)
            else:
                grams_per_unit = getattr(item, "grams_per_unit", None)
                if grams_per_unit and float(grams_per_unit) > 0:
                    display_amount = round(float(resolved_weight_g) / float(grams_per_unit), 6)
                else:
                    display_amount = None

            display_amount_text = self._format_display_amount_text(
                amount=display_amount,
                unit=display_unit,
            )

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

                    display_amount=display_amount,
                    display_unit=display_unit,
                    display_amount_text=display_amount_text,
                )
            )

        total_weight = sum(w.weight_grams for w in weights)
        if total_weight > 1e-9:
            for w in weights:
                w.pct_of_recipe = round((w.weight_grams / total_weight) * 100.0, 4)

        return weights

    def _build_analysis_inputs_for_preset(
        self,
        preset: PresetRecipeSpec,
        display_weights: Sequence[WeightedIngredient],
        ingredient_profiles: Dict[str, IngredientProfile],
    ) -> Tuple[
        List[WeightedIngredient],
        Dict[str, IngredientProfile],
        Dict[str, object],
    ]:
        """
        Build nutrient-analysis inputs from display weights.

        Rules:
        - supplements: keep raw grams / same profile
        - fruit: keep raw grams / same profile
        - other foods:
            raw_weight * yield_factor -> cooked_weight
            and switch to cooked profile when available
            otherwise fallback to raw profile
        """
        analysis_weights: List[WeightedIngredient] = []
        analysis_profiles: Dict[str, IngredientProfile] = {}
        analysis_debug: Dict[str, object] = {
            "analysis_basis": preset.analysis_basis,
            "conversion_mode": "mixed_cooked",
            "items": [],
            "fallbacks": [],
        }

        for weight in display_weights:
            display_ingredient_id = str(weight.ingredient_id)
            raw_profile = ingredient_profiles.get(display_ingredient_id)
            if raw_profile is None:
                raise RecipeSpecMappingError(
                    f"Missing ingredient profile for display ingredient_id={display_ingredient_id}"
                )

            raw_weight_g = float(weight.weight_grams)

            prep_state = str(getattr(raw_profile, "prep_state", "") or "").lower()
            food_group = str(getattr(raw_profile, "food_group", "") or "").upper()
            food_subgroup = str(getattr(raw_profile, "food_subgroup", "") or "").upper()
            short_name = str(getattr(raw_profile, "short_name", "") or "").lower()
            description = str(getattr(raw_profile, "description", "") or "").lower()
            tags = [str(t).lower() for t in (getattr(raw_profile, "tags", []) or [])]

            is_supplement = (
                bool(getattr(raw_profile, "is_supplement", False))
                or prep_state == "supplement"
                or food_group == "SUPPLEMENT"
                or "SUPPLEMENT" in food_subgroup
            )

            is_fruit = (
                "FRUIT" in food_group
                or "FRUIT" in food_subgroup
                or any(k in short_name for k in [
                    "blueberry", "cranberry", "raspberry", "strawberry",
                    "blackberry", "apple", "banana", "pear"
                ])
                or any(k in description for k in [
                    "blueberry", "cranberry", "raspberry", "strawberry",
                    "blackberry", "apple", "banana", "pear"
                ])
                or any("fruit" in t for t in tags)
            )

            # Case 1: supplement -> keep raw
            if is_supplement:
                analysis_profile = raw_profile
                analysis_weight_g = raw_weight_g
                mode = "supplement_raw"

            # Case 2: fruit -> keep raw
            elif is_fruit:
                analysis_profile = raw_profile
                analysis_weight_g = raw_weight_g
                mode = "fruit_raw"

            # Case 3: normal food -> try cooked conversion
            else:
                raw_equivalent_fdc_id = getattr(raw_profile, "raw_equivalent_fdc_id", None)
                yield_factor = getattr(raw_profile, "yield_factor", None)

                cooked_profile = None
                if raw_equivalent_fdc_id is not None:
                    repo = self._ingredient_repository
                    if hasattr(repo, "get_cooked_profile_by_raw_equivalent_fdc_id"):
                        cooked_profile = repo.get_cooked_profile_by_raw_equivalent_fdc_id(
                            str(raw_equivalent_fdc_id)
                        )

                if cooked_profile is None:
                    analysis_profile = raw_profile
                    analysis_weight_g = raw_weight_g
                    mode = "raw_fallback_no_cooked_profile"
                    analysis_debug["fallbacks"].append({
                        "display_ingredient_id": display_ingredient_id,
                        "reason": "no_cooked_profile_found",
                    })

                elif yield_factor is None or float(yield_factor) <= 0:
                    analysis_profile = raw_profile
                    analysis_weight_g = raw_weight_g
                    mode = "raw_fallback_invalid_yield_factor"
                    analysis_debug["fallbacks"].append({
                        "display_ingredient_id": display_ingredient_id,
                        "reason": "missing_or_invalid_yield_factor",
                    })

                else:
                    analysis_profile = cooked_profile
                    analysis_weight_g = raw_weight_g * float(yield_factor)
                    mode = "cooked_profile"

            analysis_weight = weight.model_copy(
                update={
                    "ingredient_id": str(analysis_profile.ingredient_id),
                    "ingredient_name": getattr(analysis_profile, "short_name", None)
                    or getattr(analysis_profile, "description", None)
                    or weight.ingredient_name,
                    "weight_grams": round(float(analysis_weight_g), 6),
                }
            )

            analysis_weights.append(analysis_weight)
            analysis_profiles[str(analysis_profile.ingredient_id)] = analysis_profile

            analysis_debug["items"].append(
                {
                    "display_ingredient_id": display_ingredient_id,
                    "analysis_ingredient_id": str(analysis_profile.ingredient_id),
                    "display_weight_g": round(raw_weight_g, 6),
                    "analysis_weight_g": round(float(analysis_weight_g), 6),
                    "display_profile_prep_state": getattr(raw_profile, "prep_state", None),
                    "analysis_profile_prep_state": getattr(analysis_profile, "prep_state", None),
                    "yield_factor": getattr(raw_profile, "yield_factor", None),
                    "mode": mode,
                }
            )

        return analysis_weights, analysis_profiles, analysis_debug


    def _should_keep_raw_for_analysis(
        self,
        profile: IngredientProfile,
    ) -> Tuple[bool, str]:
        """
        Decide whether this ingredient should stay raw for analysis.

        Rules:
        - supplements stay raw
        - fruit stays raw
        - others prefer cooked conversion when possible
        """
        if self._is_supplement_profile(profile):
            return True, "supplement_raw"

        if self._is_fruit_profile(profile):
            return True, "fruit_raw"

        return False, "convert_if_possible"


    def _resolve_best_analysis_profile(
        self,
        raw_profile: IngredientProfile,
    ) -> Tuple[IngredientProfile, str]:
        """
        Try to switch from raw profile -> cooked profile for nutrient analysis.

        Returns:
            (profile_to_use, mode)

        mode:
        - cooked_profile
        - raw_fallback_no_raw_equivalent
        - raw_fallback_no_cooked_profile
        """
        raw_equivalent_fdc_id = getattr(raw_profile, "raw_equivalent_fdc_id", None)
        if raw_equivalent_fdc_id is None:
            return raw_profile, "raw_fallback_no_raw_equivalent"

        cooked_profile = self._lookup_cooked_profile_by_raw_fdc_id(raw_equivalent_fdc_id)
        if cooked_profile is None:
            return raw_profile, "raw_fallback_no_cooked_profile"

        return cooked_profile, "cooked_profile"

    
    def _lookup_cooked_profile_by_raw_fdc_id(
        self,
        raw_equivalent_fdc_id: str | int,
    ) -> Optional[IngredientProfile]:
        """
        Look up cooked profile by raw_equivalent_fdc_id.

        Preferred repository API:
        - get_cooked_profile_by_raw_equivalent_fdc_id(raw_equivalent_fdc_id)

        Transitional fallback:
        - return None if repository does not yet support it
        """
        repo = self._ingredient_repository

        if hasattr(repo, "get_cooked_profile_by_raw_equivalent_fdc_id"):
            return repo.get_cooked_profile_by_raw_equivalent_fdc_id(str(raw_equivalent_fdc_id))

        if hasattr(repo, "find_cooked_profile_by_raw_equivalent_fdc_id"):
            return repo.find_cooked_profile_by_raw_equivalent_fdc_id(str(raw_equivalent_fdc_id))

        # Transitional fallback
        return None

    
    # 如果你的项目中有 FoodGroup 枚举，需要导入（没有则忽略，函数内已兼容）
    # from app.domains.recipe_generation.domain.enums import FoodGroup

    def _is_supplement_profile(self, profile: IngredientProfile) -> bool:
        # 安全获取食材的 prep_state 和 food_group（字典get取值，避免键不存在报错）
        prep_state = str(getattr(profile, "prep_state", "")).lower()
        food_group = getattr(profile, "food_group", None)
        
        # 严格按照你要求的逻辑判断
        is_supplement = (
            prep_state == "supplement"
            or food_group == FoodGroup.SUPPLEMENT
            or food_group == FoodGroup.FAT_OIL
            or "SUPPLEMENT" in profile.food_group
        )
        return is_supplement


    def _is_fruit_profile(self, profile: IngredientProfile) -> bool:
        food_group = str(getattr(profile, "food_group", "") or "").upper()
        food_subgroup = str(getattr(profile, "food_subgroup", "") or "").upper()
        short_name = str(getattr(profile, "short_name", "") or "").lower()
        description = str(getattr(profile, "description", "") or "").lower()
        tags = [str(t).lower() for t in (getattr(profile, "tags", []) or [])]

        # 定义水果关键词列表
        FRUIT_KEYWORDS: List[str] = [
            "blueberry", "cranberry", "raspberry", "strawberry",
            "blackberry", "apple", "banana", "pear"
        ]

        # 完全复刻参考代码的水果判断逻辑
        is_fruit = (
            "FRUIT" in food_group
            or "FRUIT" in food_subgroup
            or any(keyword in short_name for keyword in FRUIT_KEYWORDS)
            or any(keyword in description for keyword in FRUIT_KEYWORDS)
            or any("fruit" in tag for tag in tags)
        )
        return is_fruit
        

    def _augment_profiles_with_cooked_partners(
        self,
        profiles_by_ingredient_id: Dict[str, IngredientProfile],
    ) -> Dict[str, IngredientProfile]:
        """
        Add cooked partner profiles for any raw ingredient profiles.

        Why:
        - display/formulation often uses raw ingredients
        - nutrient analysis may want cooked basis
        - analysis_prep_service can only convert raw -> cooked if the cooked partner
        profile is present in ingredient_profiles
        """
        if not profiles_by_ingredient_id:
            return profiles_by_ingredient_id

        repo = self._ingredient_repository
        if repo is None or not hasattr(repo, "get_cooked_profile_by_raw_equivalent_fdc_id"):
            return profiles_by_ingredient_id

        augmented = dict(profiles_by_ingredient_id)

        for profile in list(profiles_by_ingredient_id.values()):
            raw_prep_state = getattr(profile, "prep_state", None)
            if raw_prep_state is None:
                prep_state = ""
            elif hasattr(raw_prep_state, "value"):
                prep_state = str(raw_prep_state.value).strip().lower()
            else:
                prep_state = str(raw_prep_state).strip().lower()

            if prep_state != "raw":
                continue

            raw_equivalent_fdc_id = getattr(profile, "raw_equivalent_fdc_id", None)
            if raw_equivalent_fdc_id is None:
                continue

            cooked_profile = repo.get_cooked_profile_by_raw_equivalent_fdc_id(
                str(raw_equivalent_fdc_id)
            )
            if cooked_profile is None:
                continue

            augmented[str(cooked_profile.ingredient_id)] = cooked_profile

        return augmented

    # ------------------------------------------------------------------
    # Pet-weight resolution helpers
    # ------------------------------------------------------------------

    def _resolve_preset_items_for_pet(
        self,
        raw_preset: RawPresetRecipeSpec,
        pet_weight_kg: float,
        ingredient_profiles_by_fdc_id: Dict[str, IngredientProfile],
    ) -> PresetRecipeSpec:
        """
        Convert RawPresetRecipeSpec -> resolved PresetRecipeSpec
        """
        if pet_weight_kg <= 0:
            raise RecipeSpecMappingError("pet_weight_kg must be > 0.")

        resolved_items: List[PresetRecipeItem] = []

        for idx, raw_item in enumerate(raw_preset.ingredients):
            profile = ingredient_profiles_by_fdc_id.get(str(raw_item.fdc_id))
            if profile is None:
                raise RecipeSpecMappingError(
                    f"Missing hydrated IngredientProfile for fdc_id={raw_item.fdc_id}"
                )

            resolved_weight_g: Optional[float] = None
            resolved_unit: Optional[str] = None
            resolution_mode: Optional[str] = None
            resolution_note: Optional[str] = None

            if raw_item.has_dose_tiers:
                resolved_weight_g, resolved_unit, resolution_mode = self._resolve_dose_tiers_for_pet(
                    raw_item=raw_item,
                    pet_weight_kg=pet_weight_kg,
                    recipe_id=raw_preset.recipe_id,
                    item_index=idx,
                )
            elif raw_item.has_weight_curve:
                resolved_weight_g, resolution_mode = self._resolve_weight_curve_for_pet(
                    raw_item=raw_item,
                    pet_weight_kg=pet_weight_kg,
                    recipe_id=raw_preset.recipe_id,
                    item_index=idx,
                )
                resolved_unit = "g"
            elif raw_item.base_weight_g is not None:
                resolved_weight_g = float(raw_item.base_weight_g)
                resolved_unit = "g"
                resolution_mode = "base_weight_fallback"
            else:
                raise RecipeSpecMappingError(
                    f"Preset '{raw_preset.recipe_id}' item[{idx}] (fdc_id={raw_item.fdc_id}) "
                    f"cannot be resolved for pet weight."
                )

            if resolved_weight_g is None or resolved_weight_g < 0:
                raise RecipeSpecMappingError(
                    f"Preset '{raw_preset.recipe_id}' item[{idx}] resolved to invalid weight."
                )

            resolved_items.append(
                PresetRecipeItem(
                    ingredient=self._to_ingredient_ref(profile),
                    slot_type=raw_item.slot_type,
                    base_weight_g=raw_item.base_weight_g,
                    base_ratio=raw_item.base_ratio,
                    default_unit=raw_item.default_unit,
                    grams_per_unit=raw_item.grams_per_unit,
                    is_optional=raw_item.is_optional,
                    notes=raw_item.notes,
                    resolved_weight_g=round(float(resolved_weight_g), 6),
                    resolved_unit=resolved_unit,
                    resolution_mode=resolution_mode,
                    resolution_note=resolution_note,
                )
            )

        return PresetRecipeSpec(
            recipe_id=raw_preset.recipe_id,
            name=raw_preset.name,
            description=raw_preset.description,
            ingredients=resolved_items,
            basis_kcal=raw_preset.basis_kcal,
            basis_total_weight_g=raw_preset.basis_total_weight_g,
            display_basis=raw_preset.display_basis,
            analysis_basis=raw_preset.analysis_basis,
            weight_resolution_mode=raw_preset.weight_resolution_mode,
            notes=raw_preset.notes,
            metadata=raw_preset.metadata,
        )

    def _resolve_weight_curve_for_pet(
        self,
        raw_item: RawPresetRecipeItem,
        pet_weight_kg: float,
        recipe_id: str,
        item_index: int,
    ) -> Tuple[float, str]:
        points = list(raw_item.weight_curve or [])
        if not points:
            raise RecipeSpecMappingError(
                f"Preset '{recipe_id}' item[{item_index}] has no weight_curve."
            )

        points = sorted(points, key=lambda p: float(p.weight_kg))

        if len(points) == 1:
            return float(points[0].ingredient_weight_g), "single_anchor"

        for point in points:
            if abs(float(point.weight_kg) - pet_weight_kg) < 1e-9:
                return float(point.ingredient_weight_g), "exact_hit"

        if pet_weight_kg < float(points[0].weight_kg):
            return float(points[0].ingredient_weight_g), "lower_clamp"

        if pet_weight_kg > float(points[-1].weight_kg):
            return float(points[-1].ingredient_weight_g), "upper_clamp"

        for lower, upper in zip(points[:-1], points[1:]):
            lower_w = float(lower.weight_kg)
            upper_w = float(upper.weight_kg)

            if lower_w <= pet_weight_kg <= upper_w:
                lower_g = float(lower.ingredient_weight_g)
                upper_g = float(upper.ingredient_weight_g)

                if abs(upper_w - lower_w) < 1e-12:
                    return lower_g, "exact_hit"

                ratio = (pet_weight_kg - lower_w) / (upper_w - lower_w)
                resolved = lower_g + ratio * (upper_g - lower_g)
                return resolved, "interpolated"

        raise RecipeSpecMappingError(
            f"Preset '{recipe_id}' item[{item_index}] failed to resolve weight_curve."
        )

    def _resolve_dose_tiers_for_pet(
        self,
        raw_item: RawPresetRecipeItem,
        pet_weight_kg: float,
        recipe_id: str,
        item_index: int,
    ) -> Tuple[float, str, str]:
        tiers = list(raw_item.dose_tiers or [])
        if not tiers:
            raise RecipeSpecMappingError(
                f"Preset '{recipe_id}' item[{item_index}] has no dose_tiers."
            )

        matched_tier = None
        for tier in tiers:
            if float(tier.min_weight_kg) <= pet_weight_kg <= float(tier.max_weight_kg):
                matched_tier = tier
                break

        if matched_tier is None:
            tiers = sorted(tiers, key=lambda t: (float(t.min_weight_kg), float(t.max_weight_kg)))
            if pet_weight_kg < float(tiers[0].min_weight_kg):
                matched_tier = tiers[0]
                resolution_mode = "tier_lower_clamp"
            else:
                matched_tier = tiers[-1]
                resolution_mode = "tier_upper_clamp"
        else:
            resolution_mode = "tier_match"

        amount = float(matched_tier.amount)
        unit = str(matched_tier.unit)

        if unit == "g":
            return amount, unit, resolution_mode

        grams_per_unit = raw_item.grams_per_unit
        if grams_per_unit is None or float(grams_per_unit) <= 0:
            raise RecipeSpecMappingError(
                f"Preset '{recipe_id}' item[{item_index}] uses unit '{unit}' "
                f"but grams_per_unit is missing or invalid."
            )

        resolved_weight_g = amount * float(grams_per_unit)
        return resolved_weight_g, unit, resolution_mode


    def _resolve_beginner_diy_nutrient_constraints(
        self,
        request: RecipeGenerationRequest,
    ):
        pet_profile = getattr(request, "pet_profile", None)
        life_stage = getattr(pet_profile, "life_stage", None)

        if life_stage == LifeStage.DOG_PUPPY:
            return AAFCO_STANDARDS.get(LifeStage.DOG_PUPPY, {})

        if life_stage == LifeStage.DOG_ADULT:
            return AAFCO_STANDARDS.get(LifeStage.DOG_ADULT, {})

        # Current fallback:
        # senior / unknown -> adult maintenance standard
        return AAFCO_STANDARDS.get(LifeStage.DOG_ADULT, {})

    # ------------------------------------------------------------------
    # Repository / loading helpers
    # ------------------------------------------------------------------

    def _load_raw_preset(self, recipe_id: str) -> dict:
        """
        Load raw preset definition from repository.

        """
        repo = self._preset_recipe_repository

        if hasattr(repo, "get_raw_preset"):
            return repo.get_raw_preset(recipe_id)

        if hasattr(repo, "get_preset_recipe"):
            return repo.get_preset_recipe(recipe_id)

        if hasattr(repo, "get_preset_definition"):
            return repo.get_preset_definition(recipe_id)

        raise AttributeError(
            "PresetRecipeRepository must implement one of: "
            "'get_raw_preset', 'get_preset_recipe', or 'get_preset_definition'."
        )

    def _load_ingredient_profiles(
        self,
        ingredient_ids: Sequence[str],
    ) -> Dict[str, IngredientProfile]:
        if hasattr(self._ingredient_repository, "get_ingredient_profiles_by_ids"):
            return self._ingredient_repository.get_ingredient_profiles_by_ids(ingredient_ids)

        if hasattr(self._ingredient_repository, "get_profiles_by_ids"):
            return self._ingredient_repository.get_profiles_by_ids(ingredient_ids)

        raise AttributeError(
            "IngredientRepository must implement either "
            "'get_ingredient_profiles_by_ids' or 'get_profiles_by_ids'."
        )

    def _load_beginner_diy_analysis_ingredient_profiles(
        self,
        ingredient_ids: Sequence[str],
    ) -> Dict[str, IngredientProfile]:
        """
        Load selected ingredient profiles plus any cooked partner profiles needed
        for raw -> cooked nutrient analysis conversion.
        """
        profiles = self._load_ingredient_profiles(ingredient_ids)

        if not profiles:
            return profiles

        repo = self._ingredient_repository

        if repo is None or not hasattr(repo, "get_cooked_profile_by_raw_equivalent_fdc_id"):
            return profiles

        additional_profiles: Dict[str, IngredientProfile] = {}

        for profile in list(profiles.values()):
            raw_prep_state = getattr(profile, "prep_state", None)

            if raw_prep_state is None:
                prep_state = ""
            elif hasattr(raw_prep_state, "value"):
                prep_state = str(raw_prep_state.value).strip().lower()
            else:
                prep_state = str(raw_prep_state).strip().lower()

            raw_equivalent_fdc_id = getattr(profile, "raw_equivalent_fdc_id", None)

            if prep_state != "raw":
                continue
            if raw_equivalent_fdc_id is None:
                continue

            cooked_profile = repo.get_cooked_profile_by_raw_equivalent_fdc_id(
                str(raw_equivalent_fdc_id)
            )

            if cooked_profile is None:
                continue

            additional_profiles[str(cooked_profile.ingredient_id)] = cooked_profile

        if additional_profiles:
            profiles.update(additional_profiles)
        return profiles

    def _load_ingredient_profiles_by_fdc_ids(
        self,
        fdc_ids: Sequence[str],
    ) -> Dict[str, IngredientProfile]:
        if hasattr(self._ingredient_repository, "get_ingredient_profiles_by_fdc_ids"):
            return self._ingredient_repository.get_ingredient_profiles_by_fdc_ids(fdc_ids)

        if hasattr(self._ingredient_repository, "get_profiles_by_fdc_ids"):
            return self._ingredient_repository.get_profiles_by_fdc_ids(fdc_ids)

        raise AttributeError(
            "IngredientRepository must implement either "
            "'get_ingredient_profiles_by_fdc_ids' or 'get_profiles_by_fdc_ids'."
        )

    def _get_preset_items(self, preset) -> List:
        items = getattr(preset, "items", None)
        if items is None:
            items = getattr(preset, "ingredients", None)
        return list(items or [])

    def _get_supplement_ids(self, request: RecipeGenerationRequest) -> List[str]:
        toolkit_ids = getattr(request, "supplement_toolkit_ids", None)
        if toolkit_ids is None:
            toolkit_ids = getattr(request, "supplement_toolkit", [])
        return list(toolkit_ids or [])

    # ------------------------------------------------------------------
    # Result / warning helpers
    # ------------------------------------------------------------------

    def _build_supplement_ratio_warnings(
        self,
        weights: Sequence[WeightedIngredient],
        total_weight_g: float,
    ) -> List[str]:
        if total_weight_g <= 1e-9:
            return []

        total_supp = sum(
            w.weight_grams for w in weights if getattr(w, "is_supplement", False)
        )
        supp_ratio = total_supp / total_weight_g

        if supp_ratio > 0.05:
            return [
                f"Supplement ratio is {supp_ratio:.1%}, which exceeds the 5% guideline."
            ]
        return []

    def _build_source_kwargs(
        self,
        source_type: str,
        source_recipe_id: str,
    ) -> Dict[str, object]:
        model_fields = getattr(RecipeGenerationResult, "model_fields", {}) or {}
        kwargs: Dict[str, object] = {}

        if "source_type" in model_fields:
            kwargs["source_type"] = source_type

        if "source_recipe_id" in model_fields:
            kwargs["source_recipe_id"] = source_recipe_id

        if source_type == "preset" and "preset_recipe_id" in model_fields:
            kwargs["preset_recipe_id"] = source_recipe_id

        return kwargs

    def _apply_source_fields(
        self,
        result: RecipeGenerationResult,
        source_type: str,
        source_recipe_id: str,
    ) -> None:
        if hasattr(result, "source_type"):
            setattr(result, "source_type", source_type)

        if hasattr(result, "source_recipe_id"):
            setattr(result, "source_recipe_id", source_recipe_id)

        if source_type == "preset" and hasattr(result, "preset_recipe_id"):
            setattr(result, "preset_recipe_id", source_recipe_id)


    def _to_ingredient_ref(self, profile: IngredientProfile):
        if hasattr(profile, "to_ref"):
            return profile.to_ref()
        return IngredientRef.model_validate(profile)

    
    def _format_display_amount_text(
        self,
        amount: Optional[float],
        unit: Optional[str],
    ) -> Optional[str]:
        if amount is None or unit is None:
            return None

        # g 直接显示数字
        if unit == "g":
            if float(amount).is_integer():
                return f"{int(amount)} g"
            return f"{round(float(amount), 2)} g"

        # tsp / cap / tab 优先分数化
        frac = Fraction(float(amount)).limit_denominator(8)

        if frac.denominator == 1:
            amount_text = f"{frac.numerator}"
        else:
            amount_text = f"{frac.numerator}/{frac.denominator}"

        return f"{amount_text} {unit}"

    # ------------------------------------------------------------------
    # Generic helpers
    # ------------------------------------------------------------------

    def _collect_beginner_diy_ingredient_ids(
        self,
        beginner_spec,
    ) -> List[str]:
        ids: List[str] = []

        for category in getattr(beginner_spec, "categories", []) or []:
            for item in getattr(category, "ingredients", []) or []:
                ingredient = getattr(item, "ingredient", None)
                ingredient_id = getattr(ingredient, "ingredient_id", None)
                if ingredient_id:
                    ids.append(str(ingredient_id))

        for supplement in getattr(beginner_spec, "supplements", []) or []:
            ingredient = getattr(supplement, "ingredient", None)
            ingredient_id = getattr(ingredient, "ingredient_id", None)
            if ingredient_id:
                ids.append(str(ingredient_id))

        return self._dedupe_preserve_order(ids)

        
    @staticmethod
    def _dedupe_preserve_order(values: Sequence[str]) -> List[str]:
        seen = set()
        result: List[str] = []
        for value in values:
            if value in seen:
                continue
            seen.add(value)
            result.append(value)
        return result

    @staticmethod
    def _make_error_result(
        request: RecipeGenerationRequest,
        message: str,
    ) -> RecipeGenerationResult:
        result_kwargs = {
            "mode": request.mode,
            "status": SolveStatus.ERROR,
            "recipe_id": None,
            "weights": [],
            "nutrient_analysis": [],
            "warnings": [message],
            "debug_meta": {
                "request_id": getattr(request, "request_id", None),
                "requested_by": getattr(request, "requested_by", None),
            },
        }
        return RecipeGenerationResult(**result_kwargs)