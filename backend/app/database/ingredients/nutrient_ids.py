from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, IntEnum
from typing import Dict, List, Optional, Set

import pandas as pd
from pydantic import BaseModel, Field
from .contracts import ThresholdValue, TagRule, IngredientTagRecord, CategoryLimit


class NutrientGroup(str, Enum):
    PROTEIN = "protein_amino"
    FAT = "fat_fatty_acid"
    MINERALS = "minerals"
    VITAMINS_OTHER = "vitamins_other"


class NutrientID(IntEnum):
    """营养素 ID 常量定义"""

    ENERGY = 1008
    CARBOHYDRATE = 1005
    FIBER = 1079

    PROTEIN = 1003
    ARGININE = 1220
    HISTIDINE = 1221
    ISOLEUCINE = 1212
    LEUCINE = 1213
    LYSINE = 1214
    METHIONINE = 1215
    CYSTINE = 1216
    PHENYLALANINE = 1217
    TYROSINE = 1218
    THREONINE = 1211
    TRYPTOPHAN = 1210
    VALINE = 1219

    FAT = 1004
    PUFA_18_2 = 1269
    ALA = 1404
    PUFA_20_4 = 1271
    DHA = 1272
    EPA = 1278

    CALCIUM = 1087
    PHOSPHORUS = 1091
    POTASSIUM = 1092
    SODIUM = 1093
    CHLORIDE = 1088
    MAGNESIUM = 1090
    IRON = 1089
    COPPER = 1098
    MANGANESE = 1101
    ZINC = 1095
    IODINE = 1100
    SELENIUM = 1103

    VITAMIN_A = 1104
    VITAMIN_D = 1110
    VITAMIN_E = 1109
    THIAMIN = 1165
    RIBOFLAVIN = 1166
    PANTOTHENIC_ACID = 1170
    NIACIN = 1167
    PYRIDOXINE = 1175
    FOLIC_ACID = 1186
    VITAMIN_B12 = 1178
    CHOLINE = 1180


NUTRIENT_GROUPS: Dict[NutrientGroup, Set[int]] = {
    NutrientGroup.PROTEIN: {
        NutrientID.ARGININE,
        NutrientID.HISTIDINE,
        NutrientID.ISOLEUCINE,
        NutrientID.LEUCINE,
        NutrientID.LYSINE,
        NutrientID.METHIONINE,
        NutrientID.CYSTINE,
        NutrientID.PHENYLALANINE,
        NutrientID.TYROSINE,
        NutrientID.THREONINE,
        NutrientID.TRYPTOPHAN,
        NutrientID.VALINE,
        NutrientID.PROTEIN,
    },
    NutrientGroup.FAT: {
        NutrientID.PUFA_18_2,
        NutrientID.ALA,
        NutrientID.PUFA_20_4,
        NutrientID.DHA,
        NutrientID.EPA,
        NutrientID.FAT,
    },
    NutrientGroup.MINERALS: {
        NutrientID.CALCIUM,
        NutrientID.PHOSPHORUS,
        NutrientID.POTASSIUM,
        NutrientID.SODIUM,
        NutrientID.CHLORIDE,
        NutrientID.MAGNESIUM,
        NutrientID.IRON,
        NutrientID.COPPER,
        NutrientID.MANGANESE,
        NutrientID.ZINC,
        NutrientID.IODINE,
        NutrientID.SELENIUM,
    },
    NutrientGroup.VITAMINS_OTHER: {
        NutrientID.VITAMIN_A,
        NutrientID.VITAMIN_D,
        NutrientID.VITAMIN_E,
        NutrientID.VITAMIN_B12,
        NutrientID.RIBOFLAVIN,
        NutrientID.THIAMIN,
        NutrientID.NIACIN,
        NutrientID.PANTOTHENIC_ACID,
        NutrientID.PYRIDOXINE,
        NutrientID.FOLIC_ACID,
        NutrientID.CHOLINE,
        NutrientID.FIBER,
        NutrientID.CARBOHYDRATE,
        NutrientID.ENERGY,
    },
}


class NutrientMeta:
    _id_to_name_cache: Dict[int, str] = {}
    _id_to_group_cache: Dict[int, str] = {}
    _id_to_unit_cache: Dict[int, str] = {}

    @classmethod
    def initialize(cls) -> None:
        if cls._id_to_name_cache:
            return

        for nutrient in NutrientID:
            cls._id_to_name_cache[int(nutrient)] = nutrient.name.lower().replace("_", " ")

        for group, ids in NUTRIENT_GROUPS.items():
            for nutrient_id in ids:
                cls._id_to_group_cache[int(nutrient_id)] = group.value

    @classmethod
    def load_metadata(cls, nutrient_csv_path: str) -> None:
        df = pd.read_csv(
            nutrient_csv_path,
            usecols=["nutrient_id", "name", "unit_name"],
        ).copy()

        df["nutrient_id"] = (
            pd.to_numeric(df["nutrient_id"], errors="coerce")
            .fillna(0)
            .astype(int)
        )
        df = df[df["nutrient_id"] > 0]

        def clean_unit(unit_value: object) -> str:
            if not isinstance(unit_value, str):
                return ""
            unit_value = unit_value.strip()
            if unit_value.upper() == "IU":
                return "IU"
            return unit_value.lower()

        cls.initialize()
        cls._id_to_unit_cache.update(
            dict(zip(df["nutrient_id"], df["unit_name"].apply(clean_unit)))
        )

    @classmethod
    def get_name(cls, nutrient_id: int) -> str:
        cls.initialize()
        return cls._id_to_name_cache.get(int(nutrient_id), f"unknown nutrient {nutrient_id}")

    @classmethod
    def get_group(cls, nutrient_id: int) -> str:
        cls.initialize()
        return cls._id_to_group_cache.get(int(nutrient_id), "unknown")

    @classmethod
    def get_unit(cls, nutrient_id: int) -> str:
        return cls._id_to_unit_cache.get(int(nutrient_id), "")

    @classmethod
    def get_defined_ids_in_order(cls) -> List[int]:
        return [int(n) for n in NutrientID]
