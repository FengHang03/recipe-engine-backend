from typing import Optional

from app.domains.energy.contracts.enums import AdultEnergyProfile, Species
from app.domains.energy.contracts.profiles import AdultEnergyProfilesResult
from .constants import EnergyConstants
from .rer import bw075


def calculate_adult_energy_profiles(
    weight_kg: float,
    species: Species = Species.DOG,
) -> AdultEnergyProfilesResult:
    if weight_kg <= 0:
        raise ValueError("weight_kg must be > 0")

    x = bw075(weight_kg)

    coeffs = (
        EnergyConstants.DOG_ADULT_PROFILE_COEFFICIENTS
        if species == Species.DOG
        else EnergyConstants.CAT_ADULT_PROFILE_COEFFICIENTS
    )

    profiles = {
        profile.value: round(coeff * x, 1)
        for profile, coeff in coeffs.items()
    }

    return AdultEnergyProfilesResult(
        profiles=profiles,
        default_profile=AdultEnergyProfile.MODERATE_ACTIVITY.value,
    )