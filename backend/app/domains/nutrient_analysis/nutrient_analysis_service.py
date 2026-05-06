from __future__ import annotations

"""
nutrient_analysis_service.py

Shared nutrient analysis service based on ingredient amounts + nutrient dataframes.

Purpose
-------
- Aggregate recipe nutrient totals from ingredient_nutrients_df
- Keep unit and basis separate during computation
- Normalize to target basis when needed
- Convert into target units for comparison
- Return structured NutrientAnalysis rows

Boundary
--------
This service is intentionally independent from:
- WeightedIngredient
- PetProfile
- IngredientProfile
- recipe_generation workflow logic
"""

from typing import Dict, List, Mapping, Optional, Set, Tuple, Union

import pandas as pd

from app.shared.contracts.enums import NutrientID, NUTRIENT_METADATA
from app.shared.contracts.nutrition import NutrientAnalysis
from app.domains.recipe_generation.contracts.constraints import NutrientConstraint
from app.domains.nutrient_analysis.contracts import (
    AnalysisIngredientItem,
    NutrientAnalysisInput,
    NutrientAnalysisResult,
)
from app.domains.nutrient_analysis.unit_converter import NutrientUnitConverter


DERIVED_CA_P_RATIO = "CA_P_RATIO"
DERIVED_N6_N3_RATIO = "N6_N3_RATIO"
DERIVED_EPA_DHA_SUM = "EPA_DHA_SUM"

_DERIVED_NUTRIENT_METADATA = {
    DERIVED_CA_P_RATIO: {
        "name": "Calcium:Phosphorus Ratio",
        "unit": "ratio",
        "basis": "ratio",
    },
    DERIVED_N6_N3_RATIO: {
        "name": "Omega-6:Omega-3 Ratio",
        "unit": "ratio",
        "basis": "ratio",
    },
    DERIVED_EPA_DHA_SUM: {
        "name": "EPA + DHA",
        "unit": "g",
        "basis": "per_recipe",
    },
}

_PER_RECIPE_BASIS_VALUES = {"per_recipe", "absolute", "recipe_total"}
_PER_1000_KCAL_BASIS_VALUES = {"per_1000_kcal", "1000kcal", "per_1000kcal"}
_RATIO_BASIS_VALUES = {"ratio"}


class NutrientAnalysisService:
    """
    Shared nutrient analysis service.

    Responsibilities
    ----------------
    1. Aggregate absolute per-recipe nutrient totals
    2. Resolve target basis per nutrient
    3. Normalize values to target basis when needed
    4. Convert values into target units when needed
    5. Build NutrientAnalysis rows

    Non-responsibilities
    --------------------
    - repository access
    - cooked/raw basis decisions
    - preset / beginner diy orchestration
    """

    def analyze(self, analysis_input: NutrientAnalysisInput) -> NutrientAnalysisResult:
        self._validate_input_df(analysis_input.ingredient_nutrients_df)
        self._validate_metadata_df(analysis_input.nutrient_metadata_df)

        raw_totals, raw_unit_by_nutrient = self._aggregate_raw_totals(
            items=analysis_input.items,
            ingredient_nutrients_df=analysis_input.ingredient_nutrients_df,
            nutrient_metadata_df=analysis_input.nutrient_metadata_df,
        )

        if not raw_totals:
            return NutrientAnalysisResult(
                totals_raw_value={},
                totals_display_value={},
                raw_unit_by_nutrient={},
                display_unit_by_nutrient={},
                display_basis_by_nutrient={},
                analyses=[],
                used_target_calories_kcal=None,
                warnings=["No nutrient totals could be computed."],
                debug_meta={"item_count": len(analysis_input.items)},
            )

        raw_totals, raw_unit_by_nutrient = self._append_derived_metrics(
            totals=raw_totals,
            raw_unit_by_nutrient=raw_unit_by_nutrient,
        )

        nutrient_meta_by_id = self._build_nutrient_meta_map(analysis_input.nutrient_metadata_df)
        used_target_calories_kcal = self._resolve_target_calories_kcal(
            analysis_input=analysis_input,
            raw_totals=raw_totals,
        )

        display_totals: Dict[str, Optional[float]] = {}
        display_unit_by_nutrient: Dict[str, str] = {}
        display_basis_by_nutrient: Dict[str, str] = {}

        analysis_keys = self._collect_analysis_keys(
            totals=raw_totals,
            nutrient_constraints=analysis_input.nutrient_constraints,
        )

        warnings: List[str] = []

        for nutrient_key in analysis_keys:
            raw_value = raw_totals.get(nutrient_key)
            source_unit = raw_unit_by_nutrient.get(nutrient_key, "")
            target_unit = self._resolve_target_unit(
                nutrient_key=nutrient_key,
                nutrient_constraints=analysis_input.nutrient_constraints,
                fallback_unit=source_unit,
            )
            target_basis = self._resolve_target_basis(
                nutrient_key=nutrient_key,
                nutrient_constraints=analysis_input.nutrient_constraints,
                default_output_basis=analysis_input.default_output_basis,
            )

            display_unit_by_nutrient[nutrient_key] = target_unit
            display_basis_by_nutrient[nutrient_key] = target_basis

            if raw_value is None:
                display_totals[nutrient_key] = None
                continue

            try:
                value_after_basis = self._normalize_value_to_basis(
                    nutrient_key=nutrient_key,
                    value=float(raw_value),
                    target_basis=target_basis,
                    target_calories_kcal=used_target_calories_kcal,
                )
            except ValueError as exc:
                display_totals[nutrient_key] = None
                warnings.append(f"{nutrient_key}: {exc}")
                continue

            value_after_unit = self._convert_value_to_target_unit(
                nutrient_key=nutrient_key,
                value=value_after_basis,
                source_unit=source_unit,
                target_unit=target_unit,
            )

            display_totals[nutrient_key] = value_after_unit

        analyses = self._build_analyses(
            totals_display_value=display_totals,
            raw_unit_by_nutrient=raw_unit_by_nutrient,
            display_unit_by_nutrient=display_unit_by_nutrient,
            display_basis_by_nutrient=display_basis_by_nutrient,
            nutrient_meta_by_id=nutrient_meta_by_id,
            nutrient_constraints=analysis_input.nutrient_constraints,
        )

        return NutrientAnalysisResult(
            totals_raw_value=raw_totals,
            totals_display_value=display_totals,
            raw_unit_by_nutrient=raw_unit_by_nutrient,
            display_unit_by_nutrient=display_unit_by_nutrient,
            display_basis_by_nutrient=display_basis_by_nutrient,
            analyses=analyses,
            used_target_calories_kcal=used_target_calories_kcal,
            warnings=warnings,
            debug_meta={
                "item_count": len(analysis_input.items),
                "aggregated_nutrient_count": len(raw_totals),
            },
        )

    # ------------------------------------------------------------------
    # aggregation
    # ------------------------------------------------------------------

    def _aggregate_raw_totals(
        self,
        items: List[AnalysisIngredientItem],
        ingredient_nutrients_df: pd.DataFrame,
        nutrient_metadata_df: pd.DataFrame,
    ) -> Tuple[Dict[str, float], Dict[str, str]]:
        """
        Aggregate absolute per-recipe nutrient totals.

        ingredient_nutrients_df columns:
            ingredient_id, nutrient_id, amount_per_100g

        nutrient_metadata_df columns:
            nutrient_id, name, unit_name
        """
        if not items:
            return {}, {}

        items_df = pd.DataFrame(
            [{"ingredient_id": item.ingredient_id, "weight_g": float(item.weight_g)} for item in items]
        )

        merged = ingredient_nutrients_df.merge(
            items_df,
            on="ingredient_id",
            how="inner",
        )

        if merged.empty:
            return {}, {}

        metadata_df = nutrient_metadata_df.copy()
        metadata_df["nutrient_key"] = metadata_df["nutrient_id"].apply(self._normalize_nutrient_key)

        merged = merged.copy()
        merged["nutrient_key"] = merged["nutrient_id"].apply(self._normalize_nutrient_key)
        merged["amount_per_100g"] = pd.to_numeric(merged["amount_per_100g"], errors="coerce").fillna(0.0)
        merged["weight_g"] = pd.to_numeric(merged["weight_g"], errors="coerce").fillna(0.0)
        merged["recipe_total"] = merged["amount_per_100g"] * merged["weight_g"] / 100.0

        totals_df = (
            merged.groupby("nutrient_key", as_index=False)["recipe_total"]
            .sum()
        )

        raw_totals = {
            str(row["nutrient_key"]): float(row["recipe_total"])
            for row in totals_df.to_dict(orient="records")
        }

        unit_by_nutrient = {
            str(row["nutrient_key"]): str(row.get("unit_name", "")).strip().lower()
            for row in metadata_df.to_dict(orient="records")
        }

        return raw_totals, unit_by_nutrient

    def _resolve_target_calories_kcal(
        self,
        analysis_input: NutrientAnalysisInput,
        raw_totals: Dict[str, Optional[float]],
    ) -> float:
        """
        Resolve recipe kcal denominator.

        Priority:
        1. Explicit target_calories_kcal from caller
        2. ENERGY nutrient total from raw_totals
        """
        if analysis_input.target_energy_kcal is not None and analysis_input.target_energy_kcal > 0:
            return float(analysis_input.target_energy_kcal)

        energy_keys = {
            self._normalize_nutrient_key(NutrientID.ENERGY),
            "1008",
        }

        for energy_key in energy_keys:
            value = raw_totals.get(energy_key)
            if value is not None and value > 0:
                return float(value)

        return 0.0

    # ------------------------------------------------------------------
    # normalization + conversion
    # ------------------------------------------------------------------

    def _normalize_value_to_basis(
        self,
        nutrient_key: str,
        value: float,
        target_basis: str,
        target_calories_kcal: Optional[float],
    ) -> float:
        normalized_basis = self._normalize_basis_name(target_basis)

        if nutrient_key in _DERIVED_NUTRIENT_METADATA:
            if normalized_basis in _RATIO_BASIS_VALUES or normalized_basis in _PER_RECIPE_BASIS_VALUES:
                return float(value)
            return float(value)

        if normalized_basis in _PER_RECIPE_BASIS_VALUES:
            return float(value)

        if normalized_basis in _PER_1000_KCAL_BASIS_VALUES:
            return NutrientUnitConverter.normalize_per_1000_kcal(
                value=float(value),
                target_calories_kcal=float(target_calories_kcal or 0.0),
            )

        if normalized_basis in _RATIO_BASIS_VALUES:
            return float(value)

        raise ValueError(f"Unsupported target basis: {target_basis}")

    def _convert_value_to_target_unit(
        self,
        nutrient_key: str,
        value: float,
        source_unit: str,
        target_unit: str,
    ) -> float:
        if nutrient_key in _DERIVED_NUTRIENT_METADATA:
            return float(value)
        
        if (source_unit or "").strip().lower() == (target_unit or "").strip().lower():
            return float(value)

        return NutrientUnitConverter.convert_value(
            value=float(value),
            nutrient_id=nutrient_key,
            from_unit=source_unit,
            to_unit=target_unit,
        )

    # ------------------------------------------------------------------
    # analysis row building
    # ------------------------------------------------------------------

    def _build_analyses(
        self,
        totals_display_value: Dict[str, Optional[float]],
        raw_unit_by_nutrient: Dict[str, str],
        display_unit_by_nutrient: Dict[str, str],
        display_basis_by_nutrient: Dict[str, str],
        nutrient_meta_by_id: Dict[str, Dict[str, str]],
        nutrient_constraints: Optional[Mapping[Union[NutrientID, str, int], NutrientConstraint]],
    ) -> List[NutrientAnalysis]:
        analyses: List[NutrientAnalysis] = []

        analysis_keys = self._collect_analysis_keys(
            totals=totals_display_value,
            nutrient_constraints=nutrient_constraints,
        )

        for nutrient_key in analysis_keys:
            display_value = totals_display_value.get(nutrient_key)
            constraint = self._get_constraint(nutrient_constraints, nutrient_key)

            min_required = constraint.min if constraint else None
            max_allowed = None
            if constraint:
                max_allowed = (
                    constraint.max_hard
                    if getattr(constraint, "max_hard", None) is not None
                    else constraint.max
                )
            ideal_target = constraint.ideal if constraint else None

            meets_min = True
            if min_required is not None:
                meets_min = (display_value is not None) and (display_value >= float(min_required))

            meets_max = True
            if max_allowed is not None:
                meets_max = (display_value is not None) and (display_value <= float(max_allowed))

            deviation_from_ideal = None
            if ideal_target is not None and display_value is not None:
                deviation_from_ideal = round(display_value - float(ideal_target), 6)

            nutrient_meta = self._get_nutrient_metadata(
                nutrient_key=nutrient_key,
                nutrient_meta_by_id=nutrient_meta_by_id,
            )
            nutrient_name = nutrient_meta.get("name", nutrient_key)

            display_unit = display_unit_by_nutrient.get(
                nutrient_key,
                raw_unit_by_nutrient.get(nutrient_key, ""),
            )
            display_basis = display_basis_by_nutrient.get(nutrient_key, "per_recipe")
            display_unit_label = self._format_unit_with_basis(
                unit=display_unit,
                basis=display_basis,
            )

            analyses.append(
                NutrientAnalysis(
                    nutrient_id=nutrient_key,
                    nutrient_name=nutrient_name,
                    value=round(display_value, 6) if display_value is not None else 0.0,
                    unit=display_unit_label,
                    min_required=min_required,
                    max_allowed=max_allowed,
                    ideal_target=ideal_target,
                    meets_min=meets_min,
                    meets_max=meets_max,
                    deviation_from_ideal=deviation_from_ideal,
                )
            )

        return analyses

    # ------------------------------------------------------------------
    # derived metrics
    # ------------------------------------------------------------------

    def _append_derived_metrics(
        self,
        totals: Dict[str, float],
        raw_unit_by_nutrient: Dict[str, str],
    ) -> Tuple[Dict[str, Optional[float]], Dict[str, str]]:
        enriched: Dict[str, Optional[float]] = dict(totals)
        enriched_units: Dict[str, str] = dict(raw_unit_by_nutrient)

        ca = enriched.get(self._normalize_nutrient_key(NutrientID.CALCIUM), 0.0) or 0.0
        p = enriched.get(self._normalize_nutrient_key(NutrientID.PHOSPHORUS), 0.0) or 0.0
        enriched[DERIVED_CA_P_RATIO] = (ca / p) if p > 1e-9 else None
        enriched_units[DERIVED_CA_P_RATIO] = "ratio"

        la = enriched.get(self._normalize_nutrient_key(NutrientID.LA), 0.0) or 0.0
        ara = enriched.get(self._normalize_nutrient_key(NutrientID.ARA), 0.0) or 0.0
        ala = enriched.get(self._normalize_nutrient_key(NutrientID.ALA), 0.0) or 0.0
        epa_key = self._normalize_nutrient_key(NutrientID.EPA)
        dha_key = self._normalize_nutrient_key(NutrientID.DHA)
        epa = enriched.get(epa_key, 0.0) or 0.0
        dha = enriched.get(dha_key, 0.0) or 0.0

        total_n6 = la + ara
        total_n3 = ala + epa + dha

        enriched[DERIVED_N6_N3_RATIO] = (total_n6 / total_n3) if total_n3 > 1e-9 else None
        enriched_units[DERIVED_N6_N3_RATIO] = "ratio"

        enriched[DERIVED_EPA_DHA_SUM] = epa + dha
        enriched_units[DERIVED_EPA_DHA_SUM] = (
            raw_unit_by_nutrient.get(epa_key)
            or raw_unit_by_nutrient.get(dha_key)
            or "g"
        )

        return enriched, enriched_units

    # ------------------------------------------------------------------
    # metadata / constraints
    # ------------------------------------------------------------------

    def _build_nutrient_meta_map(self, nutrient_metadata_df: pd.DataFrame) -> Dict[str, Dict[str, str]]:
        df = nutrient_metadata_df.copy()
        df["nutrient_key"] = df["nutrient_id"].apply(self._normalize_nutrient_key)

        result: Dict[str, Dict[str, str]] = {}
        for row in df.to_dict(orient="records"):
            result[str(row["nutrient_key"])] = {
                "name": str(row.get("name", "")).strip(),
                "unit": str(row.get("unit_name", "")).strip().lower(),
            }
        return result

    def _collect_analysis_keys(
        self,
        totals: Dict[str, Optional[float]],
        nutrient_constraints: Optional[Mapping[Union[NutrientID, str, int], NutrientConstraint]],
    ) -> List[str]:
        keys: Set[str] = set(totals.keys())

        if nutrient_constraints:
            for key in nutrient_constraints.keys():
                keys.add(self._normalize_nutrient_key(key))

        return sorted(keys)

    def _resolve_target_unit(
        self,
        nutrient_key: str,
        nutrient_constraints: Optional[Mapping[Union[NutrientID, str, int], NutrientConstraint]],
        fallback_unit: str,
    ) -> str:
        if nutrient_key in _DERIVED_NUTRIENT_METADATA:
            return _DERIVED_NUTRIENT_METADATA[nutrient_key]["unit"]

        constraint = self._get_constraint(nutrient_constraints, nutrient_key)
        if constraint and getattr(constraint, "unit", None):
            return str(constraint.unit).strip().lower()

        return (fallback_unit or "").strip().lower()

    def _resolve_target_basis(
        self,
        nutrient_key: str,
        nutrient_constraints: Optional[Mapping[Union[NutrientID, str, int], NutrientConstraint]],
        default_output_basis: str,
    ) -> str:
        if nutrient_key in _DERIVED_NUTRIENT_METADATA:
            return _DERIVED_NUTRIENT_METADATA[nutrient_key]["basis"]

        constraint = self._get_constraint(nutrient_constraints, nutrient_key)
        if constraint and getattr(constraint, "basis", None):
            return self._normalize_basis_name(str(constraint.basis))

        return self._normalize_basis_name(default_output_basis)

    def _get_constraint(
        self,
        nutrient_constraints: Optional[Mapping[Union[NutrientID, str, int], NutrientConstraint]],
        nutrient_key: str,
    ) -> Optional[NutrientConstraint]:
        if not nutrient_constraints:
            return None

        if nutrient_key in nutrient_constraints:
            return nutrient_constraints[nutrient_key]

        try:
            nutrient_enum = NutrientID(int(nutrient_key))
            if nutrient_enum in nutrient_constraints:
                return nutrient_constraints[nutrient_enum]
        except Exception:
            pass

        try:
            nutrient_int = int(nutrient_key)
            if nutrient_int in nutrient_constraints:
                return nutrient_constraints[nutrient_int]
        except Exception:
            pass

        return None

    def _get_nutrient_metadata(
        self,
        nutrient_key: str,
        nutrient_meta_by_id: Dict[str, Dict[str, str]],
    ) -> Dict[str, str]:
        if nutrient_key in _DERIVED_NUTRIENT_METADATA:
            return {
                "name": _DERIVED_NUTRIENT_METADATA[nutrient_key]["name"],
                "unit": _DERIVED_NUTRIENT_METADATA[nutrient_key]["unit"],
            }

        if nutrient_key in nutrient_meta_by_id:
            return nutrient_meta_by_id[nutrient_key]

        try:
            nutrient_enum = NutrientID(int(nutrient_key))
            raw = NUTRIENT_METADATA.get(nutrient_enum, {})
            if not raw:
                return {}
            return {
                "name": raw.get("name", str(nutrient_enum)),
                "unit": raw.get("unit_name", raw.get("unit", "")),
            }
        except Exception:
            return {}

    # ------------------------------------------------------------------
    # formatting / validation
    # ------------------------------------------------------------------

    def _format_unit_with_basis(self, unit: str, basis: str) -> str:
        normalized_basis = self._normalize_basis_name(basis)

        if normalized_basis in _RATIO_BASIS_VALUES:
            return "ratio"

        if normalized_basis in _PER_1000_KCAL_BASIS_VALUES:
            return f"{unit}/1000kcal" if unit else "/1000kcal"

        if normalized_basis in _PER_RECIPE_BASIS_VALUES:
            return unit or ""

        return unit or ""

    def _validate_input_df(self, df: pd.DataFrame) -> None:
        required_columns = {"ingredient_id", "nutrient_id", "amount_per_100g"}
        missing = required_columns - set(df.columns)
        if missing:
            raise ValueError(
                f"ingredient_nutrients_df missing required columns: {sorted(missing)}"
            )

    def _validate_metadata_df(self, df: pd.DataFrame) -> None:
        required_columns = {"nutrient_id", "name", "unit_name"}
        missing = required_columns - set(df.columns)
        if missing:
            raise ValueError(
                f"nutrient_metadata_df missing required columns: {sorted(missing)}"
            )

    def _normalize_nutrient_key(self, key: Union[NutrientID, int, str]) -> str:
        if isinstance(key, NutrientID):
            return str(key.value)
        return str(key)

    def _normalize_basis_name(self, basis: str) -> str:
        raw = (basis or "").strip().lower()
        if raw in _PER_1000_KCAL_BASIS_VALUES:
            return "per_1000_kcal"
        if raw in _RATIO_BASIS_VALUES:
            return "ratio"
        if raw in _PER_RECIPE_BASIS_VALUES:
            return "per_recipe"
        return raw
        