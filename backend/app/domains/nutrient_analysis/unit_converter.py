from __future__ import annotations

"""
unit_converter.py

Utility functions for nutrient unit conversion and nutrition basis parsing.

Scope
-----
This module handles:
- numerator unit parsing (g, mg, ug, IU, etc.)
- denominator basis parsing (100g, 1000kcal)
- nutrient-specific IU conversions for vitamins
- basic normalization helpers

Non-scope
---------
This module does NOT:
- aggregate recipe nutrients
- read repositories
- compare against nutrient contracts
"""

from typing import Tuple, Union

from app.common.enums import NutrientID


class NutrientUnitConverter:
    """
    Unit conversion helper for nutrient analysis.

    Notes
    -----
    - Magnitude conversions use grams as the common weight base.
    - IU conversion is nutrient-specific and currently only supported for
      vitamins A / D / E.
    """

    MAGNITUDE_MAP = {
        "kg": 1000.0,
        "g": 1.0,
        "mg": 0.001,
        "ug": 0.000001,
        "mcg": 0.000001,
        "iu": 1.0,
        "kcal": 1.0,
        "ratio": 1.0,
        "": 1.0,
    }

    # IU -> mg
    VITAMIN_IU_TO_MG_MAP = {
        NutrientID.VITAMIN_A: 0.0003,
        NutrientID.VITAMIN_D: 0.000025,
        NutrientID.VITAMIN_E: 0.67,
    }

    @staticmethod
    def parse_unit_string(unit_str: str, default_denom: str = "100g") -> Tuple[str, str]:
        """
        Parse strings like:
            "mg/1000kcal" -> ("mg", "1000kcal")
            "g/100g"      -> ("g", "100g")
            "mg"          -> ("mg", default_denom)
        """
        raw = (unit_str or "").strip().lower()
        if "/" in raw:
            numerator, denominator = raw.split("/", 1)
            return numerator.strip(), denominator.strip()

        return raw.strip(), default_denom.strip().lower()

    @classmethod
    def convert_value(
        cls,
        value: float,
        nutrient_id: Union[NutrientID, int, str],
        from_unit: str,
        to_unit: str,
    ) -> float:
        """
        Convert a nutrient value between units.

        Supports:
        - magnitude-only conversions: g <-> mg <-> ug/mcg
        - vitamin IU conversions for A / D / E

        If units are identical or unsupported, returns the original value.
        """
        from_u = (from_unit or "").strip().lower()
        to_u = (to_unit or "").strip().lower()

        if from_u == to_u or value is None:
            return float(value)

        nutrient_enum = cls._normalize_nutrient_id(nutrient_id)

        # Vitamin-specific IU conversions
        if nutrient_enum in cls.VITAMIN_IU_TO_MG_MAP:
            return cls._convert_vitamin_with_iu(
                value=float(value),
                nutrient_id=nutrient_enum,
                from_unit=from_u,
                to_unit=to_u,
            )

        # Generic magnitude conversions
        if from_u in cls.MAGNITUDE_MAP and to_u in cls.MAGNITUDE_MAP:
            base_value_in_g = float(value) * cls.MAGNITUDE_MAP[from_u]
            return base_value_in_g / cls.MAGNITUDE_MAP[to_u]

        return float(value)

    @staticmethod
    def normalize_per_1000_kcal(value: float, target_calories_kcal: float) -> float:
        """
        Convert absolute per-recipe total into per-1000-kcal basis.
        """
        if target_calories_kcal is None or target_calories_kcal <= 0:
            raise ValueError("target_calories_kcal must be > 0 for per-1000-kcal normalization.")
        return float(value) / float(target_calories_kcal) * 1000.0

    @classmethod
    def _convert_vitamin_with_iu(
        cls,
        value: float,
        nutrient_id: NutrientID,
        from_unit: str,
        to_unit: str,
    ) -> float:
        """
        Convert between IU and weight units for supported vitamins.
        Conversion table stores IU -> mg.
        """
        iu_to_mg = cls.VITAMIN_IU_TO_MG_MAP[nutrient_id]

        if from_unit == "iu" and to_unit != "iu":
            mg_value = value * iu_to_mg
            if to_unit == "mg":
                return mg_value
            return cls.convert_value(
                value=mg_value,
                nutrient_id=nutrient_id,
                from_unit="mg",
                to_unit=to_unit,
            )

        if from_unit != "iu" and to_unit == "iu":
            if from_unit == "mg":
                mg_value = value
            else:
                mg_value = cls.convert_value(
                    value=value,
                    nutrient_id=nutrient_id,
                    from_unit=from_unit,
                    to_unit="mg",
                )
            if iu_to_mg == 0:
                return value
            return mg_value / iu_to_mg

        if from_unit in cls.MAGNITUDE_MAP and to_unit in cls.MAGNITUDE_MAP:
            base_value_in_g = float(value) * cls.MAGNITUDE_MAP[from_unit]
            return base_value_in_g / cls.MAGNITUDE_MAP[to_unit]

        return float(value)

    @staticmethod
    def _normalize_nutrient_id(nutrient_id: Union[NutrientID, int, str]) -> NutrientID | None:
        if isinstance(nutrient_id, NutrientID):
            return nutrient_id
        try:
            return NutrientID(int(nutrient_id))
        except Exception:
            return None
            