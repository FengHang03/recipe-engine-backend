from typing import Tuple, Optional

from app.domains.energy.contracts.enums import LifeStage, ReproductiveStage
from .constants import EnergyConstants


def get_range_factors(life_stage: LifeStage, reproductive_stage: ReproductiveStage) -> Tuple[float, float]:
    if reproductive_stage in {ReproductiveStage.PREGNANT, ReproductiveStage.LACTATING}:
        return EnergyConstants.RANGE_REPRO

    if life_stage in {LifeStage.DOG_PUPPY, LifeStage.CAT_KITTEN}:
        return EnergyConstants.RANGE_GROWTH

    return EnergyConstants.RANGE_ADULT


def build_starting_range(
    daily_energy_kcal: float,
    low_factor: float,
    high_factor: float,
) -> Tuple[float, float]:
    return round(daily_energy_kcal * low_factor, 1), round(daily_energy_kcal * high_factor, 1)