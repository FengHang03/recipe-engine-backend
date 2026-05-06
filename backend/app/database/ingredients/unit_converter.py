from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from .nutrient_ids import NutrientID


@dataclass
class UnitConverter:
    MAGNITUDE_MAP = {
        "kg": 1000.0,
        "g": 1.0,
        "mg": 0.001,
        "ug": 0.000001,
        "mcg": 0.000001,
        "iu": 1.0,
        "kcal": 1.0,
    }

    VITAMIN_CONVERSION_MAP = {
        NutrientID.VITAMIN_A: 0.0003,
        NutrientID.VITAMIN_D: 0.000025,
        NutrientID.VITAMIN_E: 0.67,
    }

    @staticmethod
    def parse_unit_string(unit_str: str) -> tuple[str, str]:
        if "/" in unit_str:
            numerator, denominator = unit_str.split("/", 1)
        else:
            numerator, denominator = unit_str, "100g"
        return numerator.strip().lower(), denominator.strip().lower()

    @classmethod
    def get_unit_factor(
        cls,
        nutrient_id: int,
        nutrient_unit: str,
        threshold_unit: str,
    ) -> float:
        threshold_num, _ = cls.parse_unit_string(threshold_unit)
        nut_unit = (nutrient_unit or "").lower().strip()
        threshold_num = threshold_num.lower().strip()

        mag_factor = 1.0
        is_vitamin_special = nutrient_id in cls.VITAMIN_CONVERSION_MAP

        if is_vitamin_special:
            conversion_rate = cls.VITAMIN_CONVERSION_MAP[nutrient_id]

            if nut_unit == "iu" and threshold_num != "iu":
                weight_adjustment = cls.MAGNITUDE_MAP["mg"] / cls.MAGNITUDE_MAP[threshold_num]
                mag_factor = conversion_rate * weight_adjustment

            elif nut_unit != "iu" and threshold_num == "iu":
                source_mag = cls.MAGNITUDE_MAP.get(nut_unit, 1.0)
                to_mg_factor = source_mag / cls.MAGNITUDE_MAP["mg"]
                mag_factor = to_mg_factor * (1.0 / conversion_rate)

            elif nut_unit == threshold_num:
                mag_factor = 1.0

            elif nut_unit in cls.MAGNITUDE_MAP and threshold_num in cls.MAGNITUDE_MAP:
                mag_factor = cls.MAGNITUDE_MAP[nut_unit] / cls.MAGNITUDE_MAP[threshold_num]

        elif nut_unit in cls.MAGNITUDE_MAP and threshold_num in cls.MAGNITUDE_MAP:
            mag_factor = cls.MAGNITUDE_MAP[nut_unit] / cls.MAGNITUDE_MAP[threshold_num]

        return mag_factor

    @classmethod
    def get_base_factor(cls, energy_series: pd.Series, threshold_unit: str) -> pd.Series:
        _, threshold_denom = cls.parse_unit_string(threshold_unit)

        if threshold_denom == "100g":
            return pd.Series(1.0, index=energy_series.index)

        if threshold_denom == "1000kcal":
            safe_energy = energy_series.replace(0, pd.NA)
            return 1000.0 / safe_energy

        return pd.Series(1.0, index=energy_series.index)