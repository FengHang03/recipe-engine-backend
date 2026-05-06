from typing import Optional, Tuple

from app.domains.energy.contracts.enums import LifeStage, Species
from .constants import EnergyConstants


def default_senior_month(species: Species) -> int:
    if species == Species.DOG:
        return EnergyConstants.DEFAULT_DOG_SENIOR_MONTH
    return EnergyConstants.DEFAULT_CAT_SENIOR_MONTH


def get_life_stage_factor(
    species: Species,
    age_months: int,
    senior_month: Optional[int] = None,
) -> Tuple[float, LifeStage]:
    if senior_month is None:
        senior_month = default_senior_month(species)

    if species == Species.DOG:
        if age_months < EnergyConstants.DOG_PUPPY_EARLY_MAX:
            return EnergyConstants.DOG_PUPPY_EARLY_FACTOR, LifeStage.DOG_PUPPY
        if age_months < EnergyConstants.DOG_PUPPY_MAX:
            return EnergyConstants.DOG_PUPPY_LATE_FACTOR, LifeStage.DOG_PUPPY
        if age_months >= senior_month:
            return 1.0, LifeStage.DOG_SENIOR
        return 1.0, LifeStage.DOG_ADULT

    return 1.0, LifeStage.DOG_ADULT