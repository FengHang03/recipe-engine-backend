from __future__ import annotations

from typing import Dict, List, Mapping, Optional, Sequence, Union

import pandas as pd
from pydantic import BaseModel

from app.shared.contracts.enums import NutrientID
from app.shared.contracts.ingredient import IngredientProfile
from app.shared.contracts.pet import PetProfile

from app.domains.recipe_generation.contracts.constraints import NutrientConstraint
from app.domains.recipe_generation.contracts.enums import (
    RecipeGenerationMode,
    SolveStatus,
)
from app.domains.recipe_generation.contracts.recipe_spec import BeginnerDiyRecipeSpec
from app.domains.recipe_generation.contracts.request import RecipeGenerationRequest
from app.domains.recipe_generation.contracts.results import (
    RecipeGenerationResult,
    WeightedIngredient,
)

from app.domains.recipe_generation.orchestration.validators.beginner_diy_validator import (
    validate_beginner_diy_spec,
)
from app.domains.recipe_generation.engines.diy.ratio_expander import (
    compute_final_ratio_sum,
    expand_beginner_category_ratios,
)
from app.domains.recipe_generation.engines.diy.gram_estimator import (
    GramEstimationError,
    convert_supplements_to_weighted_ingredients,
    estimate_weighted_ingredients_from_expanded_ratios,
    recompute_pct_of_recipe_by_weight,
)

from app.domains.nutrient_analysis.contracts import NutrientAnalysisResult
from app.domains.nutrient_analysis.input_preparation_service import (
    NutrientAnalysisInputPreparationService,
    PreparedNutrientAnalysisInput,
)
from app.domains.nutrient_analysis.nutrient_analysis_service import (
    NutrientAnalysisService,
)


class BeginnerDiyPreviewDebugMeta(BaseModel):
    expanded_ratio_sum: float = 0.0
    target_energy_kcal: Optional[float] = None
    display_total_weight_grams: float = 0.0
    analysis_total_weight_grams: float = 0.0


class BeginnerDiyPreviewService:
    """
    End-to-end builder for Beginner DIY preview.

    Responsibilities
    ----------------
    1. validate beginner spec
    2. expand effective category ratios
    3. estimate display/formulation weights for food ingredients
    4. append supplements for nutrient analysis
    5. prepare nutrient-analysis input
    6. run nutrient analysis
    7. build RecipeGenerationResult

    Notes
    -----
    - Supplements do NOT contribute to recipe percentage or display total weight.
    - Supplements DO contribute to nutrient analysis.
    """

    def __init__(
        self,
        input_preparation_service: NutrientAnalysisInputPreparationService,
        nutrient_analysis_service: NutrientAnalysisService,
    ):
        self.input_preparation_service = input_preparation_service
        self.nutrient_analysis_service = nutrient_analysis_service

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def build_preview(
        self,
        request: RecipeGenerationRequest,
        ingredient_profiles: Dict[str, IngredientProfile],
        ingredient_nutrients_df: pd.DataFrame,
        nutrient_metadata_df: pd.DataFrame,
        nutrient_constraints: Optional[
            Mapping[Union[NutrientID, str, int], NutrientConstraint]
        ] = None,
    ) -> RecipeGenerationResult:
        beginner_spec = self._require_beginner_spec(request)
        pet_profile = request.pet_profile

        try:
            validate_beginner_diy_spec(beginner_spec)
        except Exception as exc:
            return self._build_error_result(
                mode=request.mode,
                recipe_id=beginner_spec.recipe_id,
                message=f"beginner DIY validation failed: {exc}",
            )

        try:
            target_energy_kcal = self._resolve_target_energy_kcal(
                spec=beginner_spec,
                pet_profile=pet_profile,
            )
        except Exception as exc:
            return self._build_error_result(
                mode=request.mode,
                recipe_id=beginner_spec.recipe_id,
                message=f"failed to resolve target energy: {exc}",
            )

        expanded_items = expand_beginner_category_ratios(beginner_spec)
        expanded_ratio_sum = compute_final_ratio_sum(expanded_items)

        if expanded_ratio_sum <= 0:
            return self._build_error_result(
                mode=request.mode,
                recipe_id=beginner_spec.recipe_id,
                message="expanded beginner DIY ratio sum is zero",
            )

        try:
            food_display_weights = estimate_weighted_ingredients_from_expanded_ratios(
                expanded_items=expanded_items,
                ingredient_profiles=ingredient_profiles,
                target_energy_kcal=target_energy_kcal,
            )
        except GramEstimationError as exc:
            return self._build_error_result(
                mode=request.mode,
                recipe_id=beginner_spec.recipe_id,
                message=f"gram estimation failed: {exc}",
            )

        # Only food ingredients participate in pct_of_recipe / display total weight
        food_display_weights = recompute_pct_of_recipe_by_weight(food_display_weights)

        supplement_weights = convert_supplements_to_weighted_ingredients(
            supplements=beginner_spec.supplements,
            ingredient_profiles=ingredient_profiles,
        )

        # Supplements should not contribute to recipe percentage
        supplement_display_weights = self._clear_pct_of_recipe(supplement_weights)

        # Nutrient analysis uses both food + supplements
        analysis_weights = [*food_display_weights, *supplement_display_weights]

        try:
            prepared_analysis = self.input_preparation_service.prepare_from_weighted_ingredients(
                weights=analysis_weights,
                ingredient_profiles=ingredient_profiles,
                ingredient_nutrients_df=ingredient_nutrients_df,
                nutrient_metadata_df=nutrient_metadata_df,
                nutrient_constraints=nutrient_constraints,
                target_energy_kcal=target_energy_kcal,
                default_output_basis="per_recipe",
            )

        except Exception as exc:
            return self._build_error_result(
                mode=request.mode,
                recipe_id=beginner_spec.recipe_id,
                message=f"failed to prepare nutrient analysis input: {exc}",
            )

        try:
            nutrient_analysis_result = self.nutrient_analysis_service.analyze(
                prepared_analysis.analysis_input
            )
        except Exception as exc:
            return self._build_error_result(
                mode=request.mode,
                recipe_id=beginner_spec.recipe_id,
                message=f"nutrient analysis failed: {exc}",
            )

        result_weights = [*food_display_weights, *supplement_display_weights]

        return self._build_success_result(
            request=request,
            beginner_spec=beginner_spec,
            result_weights=result_weights,
            prepared_analysis=prepared_analysis,
            nutrient_analysis_result=nutrient_analysis_result,
            target_energy_kcal=target_energy_kcal,
            expanded_ratio_sum=expanded_ratio_sum,
        )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _require_beginner_spec(
        self,
        request: RecipeGenerationRequest,
    ) -> BeginnerDiyRecipeSpec:
        beginner_spec = getattr(request, "beginner_diy_spec", None)
        if beginner_spec is None:
            raise ValueError(
                "request.beginner_diy_spec is required for Beginner DIY preview"
            )
        return beginner_spec

    def _resolve_target_energy_kcal(
        self,
        spec: BeginnerDiyRecipeSpec,
        pet_profile: PetProfile,
    ) -> float:
        if spec.target_energy_kcal is not None and spec.target_energy_kcal > 0:
            return float(spec.target_energy_kcal)

        if (
            pet_profile is not None
            and getattr(pet_profile, "daily_calories_kcal", None) is not None
            and float(pet_profile.daily_calories_kcal) > 0
        ):
            return float(pet_profile.daily_calories_kcal)

        raise ValueError(
            "target_energy_kcal is missing and pet_profile.daily_calories_kcal is invalid"
        )

    def _clear_pct_of_recipe(
        self,
        weights: Sequence[WeightedIngredient],
    ) -> List[WeightedIngredient]:
        result: List[WeightedIngredient] = []

        for weight in weights:
            copied = weight.model_copy(deep=True)
            copied.pct_of_recipe = None
            result.append(copied)

        return result

    def _build_success_result(
        self,
        request: RecipeGenerationRequest,
        beginner_spec: BeginnerDiyRecipeSpec,
        result_weights: Sequence[WeightedIngredient],
        prepared_analysis: PreparedNutrientAnalysisInput,
        nutrient_analysis_result: NutrientAnalysisResult,
        target_energy_kcal: float,
        expanded_ratio_sum: float,
    ) -> RecipeGenerationResult:
        display_total_weight_grams = sum(
            float(w.weight_grams)
            for w in result_weights
            if w.weight_grams is not None and not getattr(w, "is_supplement", False)
        )
        analysis_total_weight_grams = sum(
            float(item.weight_g) for item in prepared_analysis.analysis_items
        )

        debug_meta = BeginnerDiyPreviewDebugMeta(
            expanded_ratio_sum=round(float(expanded_ratio_sum), 6),
            target_energy_kcal=round(float(target_energy_kcal), 6),
            display_total_weight_grams=round(float(display_total_weight_grams), 6),
            analysis_total_weight_grams=round(float(analysis_total_weight_grams), 6),
        ).model_dump()

        debug_meta["source_items"] = [
            item.model_dump() for item in prepared_analysis.source_items
        ]
        debug_meta["prep_results"] = [
            item.model_dump() for item in prepared_analysis.prep_results
        ]
        debug_meta["analysis_items"] = [
            item.model_dump() for item in prepared_analysis.analysis_items
        ]
        debug_meta["nutrient_analysis_debug_meta"] = nutrient_analysis_result.debug_meta

        explanation_payload = {
            "mode": request.mode.value if hasattr(request.mode, "value") else str(request.mode),
            "recipe_id": beginner_spec.recipe_id,
            "display_context": beginner_spec.display_context,
            "notes": beginner_spec.notes,
            "categories": [
                {
                    "category_key": category.category_key,
                    "category_ratio": category.category_ratio,
                    "is_active": category.is_active,
                    "ingredients": [
                        {
                            "ingredient_id": item.ingredient.ingredient_id,
                            "ingredient_name": item.ingredient.description,
                            "internal_ratio": item.internal_ratio,
                        }
                        for item in category.ingredients
                    ],
                }
                for category in beginner_spec.categories
            ],
            "supplements": [
                {
                    "ingredient_id": supplement.ingredient.ingredient_id,
                    "ingredient_name": supplement.ingredient.description,
                    "grams": supplement.grams,
                }
                for supplement in beginner_spec.supplements
            ],
            "nutrient_analysis_warnings": nutrient_analysis_result.warnings,
        }

        used_supplements = [
            supplement.ingredient.description or supplement.ingredient.ingredient_id
            for supplement in beginner_spec.supplements
        ]

        warnings: List[str] = []
        warnings.extend(nutrient_analysis_result.warnings)

        return RecipeGenerationResult(
            mode=request.mode,
            status=SolveStatus.FEASIBLE,
            source_type="beginner_diy_preview",
            recipe_id=beginner_spec.recipe_id,
            source_recipe_id=beginner_spec.recipe_id,
            total_weight_grams=round(float(display_total_weight_grams), 6),
            weights=list(result_weights),
            nutrient_analysis=list(nutrient_analysis_result.analyses),
            used_supplements=used_supplements,
            warnings=warnings,
            explanation_payload=explanation_payload,
            debug_meta=debug_meta,
        )

    def _build_error_result(
        self,
        mode: RecipeGenerationMode,
        recipe_id: Optional[str],
        message: str,
    ) -> RecipeGenerationResult:
        return RecipeGenerationResult(
            mode=mode,
            status=SolveStatus.ERROR,
            source_type="beginner_diy_preview",
            recipe_id=recipe_id,
            source_recipe_id=recipe_id,
            weights=[],
            nutrient_analysis=[],
            warnings=[message],
            explanation_payload={
                "mode": mode.value if hasattr(mode, "value") else str(mode),
                "error": message,
            },
            debug_meta={"error": message},
        )

        