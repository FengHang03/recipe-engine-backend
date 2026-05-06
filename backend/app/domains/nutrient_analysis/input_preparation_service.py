from __future__ import annotations

from typing import Dict, Iterable, List, Mapping, Optional, Sequence, Union

import pandas as pd
from pydantic import BaseModel, ConfigDict, Field

from app.shared.contracts.enums import NutrientID
from app.shared.contracts.ingredient import IngredientProfile
from app.domains.recipe_generation.contracts.constraints import NutrientConstraint
from app.domains.recipe_generation.contracts.results import WeightedIngredient
from app.domains.nutrient_analysis.contracts import (
    AnalysisIngredientItem,
    NutrientAnalysisInput,
)
from app.domains.ingredients.analysis_prep_service import (
    AnalysisPrepResult,
    AnalysisPrepService,
)


class PreparedNutrientAnalysisInput(BaseModel):
    """
    Rich prepared object for downstream nutrient analysis + debugging.

    Layers:
    - source_items: original formulation/display items
    - prep_results: per-item analysis prep conversion trace
    - analysis_items: final aggregated items used by nutrient analysis
    - analysis_input: final contract passed to nutrient_analysis_service
    """
    model_config = ConfigDict(arbitrary_types_allowed=True)

    source_items: List[AnalysisIngredientItem] = Field(default_factory=list)
    prep_results: List[AnalysisPrepResult] = Field(default_factory=list)
    analysis_items: List[AnalysisIngredientItem] = Field(default_factory=list)
    analysis_input: NutrientAnalysisInput


class NutrientAnalysisInputPreparationService:
    """
    Bridge from recipe_generation outputs to nutrient_analysis input.

    Responsibilities
    ----------------
    1. Convert WeightedIngredient -> AnalysisIngredientItem
    2. Run analysis prep conversion (raw/cooked/as_is policy)
    3. Aggregate converted items into final analysis items
    4. Slice ingredient_nutrients_df to only required ingredient_ids
    5. Normalize nutrient_constraints into NutrientID-keyed dict
    6. Build NutrientAnalysisInput

    Non-responsibilities
    --------------------
    - ratio expansion
    - gram estimation
    - nutrient analysis calculation
    - repository access
    """

    REQUIRED_INGREDIENT_NUTRIENT_COLUMNS = {
        "ingredient_id",
        "nutrient_id",
        "amount_per_100g",
    }

    REQUIRED_NUTRIENT_METADATA_COLUMNS = {
        "nutrient_id",
        "name",
        "unit_name",
    }

    def __init__(
        self,
        analysis_prep_service: Optional[AnalysisPrepService] = None,
    ):
        self.analysis_prep_service = analysis_prep_service or AnalysisPrepService()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def prepare_from_weighted_ingredients(
        self,
        weights: Sequence[WeightedIngredient],
        ingredient_profiles: Dict[str, IngredientProfile],
        ingredient_nutrients_df: pd.DataFrame,
        nutrient_metadata_df: pd.DataFrame,
        nutrient_constraints: Optional[
            Mapping[Union[NutrientID, str, int], NutrientConstraint]
        ] = None,
        target_energy_kcal: Optional[float] = None,
        default_output_basis: str = "per_recipe",
    ) -> PreparedNutrientAnalysisInput:
        """
        Main entry point for recipe_generation -> nutrient_analysis bridging.
        """
        self._validate_dataframes(
            ingredient_nutrients_df=ingredient_nutrients_df,
            nutrient_metadata_df=nutrient_metadata_df,
        )

        source_items = self._weighted_ingredients_to_source_items(weights)

        return self.prepare_from_analysis_items(
            source_items=source_items,
            ingredient_profiles=ingredient_profiles,
            ingredient_nutrients_df=ingredient_nutrients_df,
            nutrient_metadata_df=nutrient_metadata_df,
            nutrient_constraints=nutrient_constraints,
            target_energy_kcal=target_energy_kcal,
            default_output_basis=default_output_basis,
        )

    def prepare_from_analysis_items(
        self,
        source_items: Sequence[AnalysisIngredientItem],
        ingredient_profiles: Dict[str, IngredientProfile],
        ingredient_nutrients_df: pd.DataFrame,
        nutrient_metadata_df: pd.DataFrame,
        nutrient_constraints: Optional[
            Mapping[Union[NutrientID, str, int], NutrientConstraint]
        ] = None,
        target_energy_kcal: Optional[float] = None,
        default_output_basis: str = "per_recipe",
    ) -> PreparedNutrientAnalysisInput:
        """
        Alternate entry point if caller already has AnalysisIngredientItem.
        """
        self._validate_dataframes(
            ingredient_nutrients_df=ingredient_nutrients_df,
            nutrient_metadata_df=nutrient_metadata_df,
        )

        prep_results = self.analysis_prep_service.convert_items(
            items=list(source_items),
            ingredient_profiles=ingredient_profiles,
        )

        analysis_items = self.analysis_prep_service.to_analysis_items(prep_results)

        filtered_ingredient_nutrients_df = self._filter_ingredient_nutrients_df(
            ingredient_nutrients_df=ingredient_nutrients_df,
            analysis_items=analysis_items,
        )

        normalized_constraints = self._normalize_constraints(nutrient_constraints)

        analysis_input = NutrientAnalysisInput(
            items=analysis_items,
            ingredient_nutrients_df=filtered_ingredient_nutrients_df,
            nutrient_metadata_df=nutrient_metadata_df.copy(),
            nutrient_constraints=normalized_constraints,
            target_energy_kcal=target_energy_kcal,
            default_output_basis=default_output_basis,
        )

        return PreparedNutrientAnalysisInput(
            source_items=list(source_items),
            prep_results=prep_results,
            analysis_items=analysis_items,
            analysis_input=analysis_input,
        )

    # ------------------------------------------------------------------
    # Internal converters
    # ------------------------------------------------------------------

    def _weighted_ingredients_to_source_items(
        self,
        weights: Sequence[WeightedIngredient],
    ) -> List[AnalysisIngredientItem]:
        """
        Convert recipe_generation WeightedIngredient rows into minimal
        analysis-preparation items.

        Notes:
        - weight_grams=None rows are skipped
        - negative weights are rejected
        """
        items: List[AnalysisIngredientItem] = []

        for weight in weights:
            if weight.weight_grams is None:
                continue

            weight_g = float(weight.weight_grams)
            if weight_g < 0:
                raise ValueError(
                    f"WeightedIngredient '{weight.ingredient_id}' has negative weight_grams={weight.weight_grams}"
                )

            items.append(
                AnalysisIngredientItem(
                    ingredient_id=weight.ingredient_id,
                    weight_g=round(weight_g, 6),
                )
            )

        return items

    def _filter_ingredient_nutrients_df(
        self,
        ingredient_nutrients_df: pd.DataFrame,
        analysis_items: Sequence[AnalysisIngredientItem],
    ) -> pd.DataFrame:
        """
        Keep only rows needed for the final analysis ingredient_ids.
        """
        analysis_ingredient_ids = {str(item.ingredient_id) for item in analysis_items}
        if not analysis_ingredient_ids:
            return ingredient_nutrients_df.iloc[0:0].copy()

        working_df = ingredient_nutrients_df.copy()
        working_df["ingredient_id"] = working_df["ingredient_id"].astype(str)

        filtered = working_df[
            working_df["ingredient_id"].isin(analysis_ingredient_ids)
        ].copy()

        return filtered

    def _normalize_constraints(
        self,
        nutrient_constraints: Optional[
            Mapping[Union[NutrientID, str, int], NutrientConstraint]
        ],
    ) -> Optional[dict[NutrientID, NutrientConstraint]]:
        """
        NutrientAnalysisInput expects:
            dict[NutrientID, NutrientConstraint] | None

        Normalize mixed keys into NutrientID-keyed dict where possible.

        Notes:
        - string/int keys that map to NutrientID are converted
        - non-enum derived keys like 'CA_P_RATIO' are skipped here
          and can be handled later in the nutrient analysis layer if needed
        """
        if not nutrient_constraints:
            return None

        normalized: dict[NutrientID, NutrientConstraint] = {}

        for key, constraint in nutrient_constraints.items():
            if isinstance(key, NutrientID):
                normalized[key] = constraint
                continue

            try:
                nutrient_enum = NutrientID(int(str(key)))
                normalized[nutrient_enum] = constraint
            except Exception:
                # Skip non-NutrientID keys such as derived metrics
                continue

        return normalized or None

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------

    def _validate_dataframes(
        self,
        ingredient_nutrients_df: pd.DataFrame,
        nutrient_metadata_df: pd.DataFrame,
    ) -> None:
        ingredient_cols = set(map(str, ingredient_nutrients_df.columns))
        metadata_cols = set(map(str, nutrient_metadata_df.columns))

        missing_ingredient_cols = (
            self.REQUIRED_INGREDIENT_NUTRIENT_COLUMNS - ingredient_cols
        )
        if missing_ingredient_cols:
            raise ValueError(
                "ingredient_nutrients_df missing required columns: "
                + ", ".join(sorted(missing_ingredient_cols))
            )

        missing_metadata_cols = (
            self.REQUIRED_NUTRIENT_METADATA_COLUMNS - metadata_cols
        )
        if missing_metadata_cols:
            raise ValueError(
                "nutrient_metadata_df missing required columns: "
                + ", ".join(sorted(missing_metadata_cols))
            )

            