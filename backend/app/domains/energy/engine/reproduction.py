from typing import List, Optional, Tuple

from app.domains.energy.contracts.enums import EstimateConfidence, Species
from .constants import EnergyConstants


def pregnancy_multiplier(
    species: Species,
    gestation_day: Optional[int],
    warnings: List[str],
) -> float:
    if gestation_day is None:
        warnings.append(
            "gestation_day not provided; using a conservative mid-pregnancy multiplier."
        )
        return (
            EnergyConstants.DOG_PREGNANCY_UNKNOWN_MULTIPLIER
            if species == Species.DOG
            else EnergyConstants.CAT_PREGNANCY_UNKNOWN_MULTIPLIER
        )

    if species == Species.DOG:
        if gestation_day <= 41:
            return EnergyConstants.DOG_GESTATION_MULTIPLIERS["early"]
        if gestation_day <= 49:
            return EnergyConstants.DOG_GESTATION_MULTIPLIERS["mid"]
        return EnergyConstants.DOG_GESTATION_MULTIPLIERS["late"]

    if gestation_day <= 21:
        return EnergyConstants.CAT_GESTATION_MULTIPLIERS["early"]
    if gestation_day <= 42:
        return EnergyConstants.CAT_GESTATION_MULTIPLIERS["mid"]
    return EnergyConstants.CAT_GESTATION_MULTIPLIERS["late"]


def lactation_multiplier(
    lactation_week: Optional[int],
    nursing_count: Optional[int],
    warnings: List[str],
) -> Tuple[float, EstimateConfidence]:
    confidence = EstimateConfidence.HIGH

    if lactation_week is None:
        lactation_week = 3
        warnings.append("lactation_week not provided; assuming week 3.")
        confidence = EstimateConfidence.MEDIUM

    if nursing_count is None:
        nursing_count = 4
        warnings.append("nursing_count not provided; assuming 4 nursing young.")
        confidence = EstimateConfidence.MEDIUM

    week_component = {
        1: 0.2,
        2: 0.5,
        3: 0.9,
        4: 1.0,
        5: 0.8,
        6: 0.6,
        7: 0.3,
        8: 0.1,
    }[lactation_week]

    litter_component = min(1.0, max(0.0, 0.12 * max(0, nursing_count - 1)))

    multiplier = 2.0 + week_component + litter_component
    multiplier = min(
        EnergyConstants.LACTATION_MAX_MULTIPLIER,
        max(EnergyConstants.LACTATION_MIN_MULTIPLIER, multiplier),
    )
    return multiplier, confidence