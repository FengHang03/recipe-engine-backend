from __future__ import annotations

from dataclasses import dataclass, field
from typing import List

from .nutrient_ids import NutrientID


@dataclass
class TargetConfig:
    protein_target: List[int] = field(default_factory=lambda: [169192, 171791, 175168, 171956, 173424, 171287, 171794, 174030, 171478, 171077])
    shellfish_target: List[int] = field(default_factory=lambda: [175180, 174250])
    fat_target: List[int] = field(default_factory=lambda: [167702, 173577, 171025])
    carb_target: List[int] = field(default_factory=lambda: [169704, 168878, 168877, 173904, 173905])
    vegetable_target: List[int] = field(default_factory=lambda: [168568, 171711, 170407, 168449, 168448, 169141, 169961, 170394, 170393, 169967, 170379])
    organ_target: List[int] = field(default_factory=lambda: [168626, 171061, 169450])
    fruits_target: List[int] = field(default_factory=lambda: [171711])
    nut_seed_target: List[int] = field(default_factory=lambda: [170556])
    supplement_target: List[int] = field(default_factory=lambda: [746775, 1742558, 2375721])

    nutrient_target: List[int] = field(default_factory=lambda: [
        int(n) for n in NutrientID
    ])

    @classmethod
    def get_all_fdc_id(cls, unique: bool = True) -> List[int]:
        instance = cls()
        target = (
            instance.protein_target
            + instance.vegetable_target
            + instance.shellfish_target
            + instance.fruits_target
            + instance.fat_target
            + instance.organ_target
            + instance.carb_target
            + instance.nut_seed_target
            + instance.supplement_target
        )
        if unique:
            target = list(dict.fromkeys(target))
        return target

    @classmethod
    def get_all_nut_id(cls, unique: bool = True) -> List[int]:
        ids = cls().nutrient_target
        if unique:
            ids = list(dict.fromkeys(ids))
        return ids