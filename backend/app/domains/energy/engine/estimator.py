from __future__ import annotations

from typing import Dict, List, Tuple, Optional

from app.domains.energy.contracts.enums import (
    ActivityLevel,
    EstimateConfidence,
    LifeStage,
    ReproductiveStage,
    SterilizationStatus,
    Species,
)
from .constants import EnergyConstants
from .body_goal import get_body_goal_multiplier
from .life_stage import get_life_stage_factor
from .reproduction import lactation_multiplier, pregnancy_multiplier
from .rer import calculate_rer


def young_activity_multiplier(activity_level: ActivityLevel) -> float:
    return EnergyConstants.YOUNG_ACTIVITY_MULTIPLIER[activity_level]


def adult_maintenance_multiplier(
    species: Species,
    sterilization_status: SterilizationStatus,
    activity_level: ActivityLevel,
) -> float:
    if species == Species.DOG:
        base = EnergyConstants.DOG_ADULT_BASE[sterilization_status]
        delta = EnergyConstants.DOG_ACTIVITY_DELTAS[activity_level]
        return max(1.2, base + delta)

    base = EnergyConstants.CAT_ADULT_BASE[sterilization_status]
    delta = EnergyConstants.CAT_ACTIVITY_DELTAS[activity_level]
    return max(1.0, base + delta)


def estimate_energy(
    *,
    weight_kg: float,
    species: Species,
    age_months: int,
    activity_level: ActivityLevel,
    sterilization_status: SterilizationStatus,
    reproductive_stage: ReproductiveStage,
    body_condition_goal,
    gestation_day,
    lactation_week,
    nursing_count,
    senior_month,
) -> Tuple[float, str, Dict[str, float], List[str], str]:
    warnings: List[str] = []
    breakdown: Dict[str, float] = {}
    confidence = EstimateConfidence.HIGH

    rer = calculate_rer(weight_kg)
    breakdown["rer"] = round(rer, 2)

    life_stage_factor, life_stage = get_life_stage_factor(
        species=species,
        age_months=age_months,
        senior_month=senior_month,
    )
    breakdown["life_stage_factor"] = round(life_stage_factor, 2)

    is_young = life_stage in {LifeStage.DOG_PUPPY}
    is_senior = life_stage in {LifeStage.DOG_SENIOR}

    if is_young and reproductive_stage in {ReproductiveStage.PREGNANT, ReproductiveStage.LACTATING}:
        warnings.append(
            f"{life_stage.value} with reproductive_stage={reproductive_stage.value} is inconsistent; "
            "reverting to normal growth estimate."
        )
        reproductive_stage = ReproductiveStage.NONE
        confidence = EstimateConfidence.MEDIUM

    if is_young:
        activity_multiplier = young_activity_multiplier(activity_level)
        breakdown["young_activity_multiplier"] = round(activity_multiplier, 3)
        daily_energy = rer * life_stage_factor * activity_multiplier
        breakdown["daily_energy_before_goal"] = round(daily_energy, 2)

    else:
        maintenance_multiplier = adult_maintenance_multiplier(
            species=species,
            sterilization_status=sterilization_status,
            activity_level=activity_level,
        )
        breakdown["adult_maintenance_multiplier"] = round(maintenance_multiplier, 2)

        maintenance_energy = rer * maintenance_multiplier
        breakdown["maintenance_energy"] = round(maintenance_energy, 2)

        if is_senior:
            warnings.append(
                "Senior status does not trigger an automatic calorie reduction here. "
                "Adjust according to body condition, muscle condition, and weight trend."
            )

        if reproductive_stage == ReproductiveStage.PREGNANT:
            multiplier = pregnancy_multiplier(species, gestation_day, warnings)
            if gestation_day is None:
                confidence = EstimateConfidence.MEDIUM
            breakdown["pregnancy_multiplier_over_maintenance"] = round(multiplier, 2)
            daily_energy = maintenance_energy * multiplier

        elif reproductive_stage == ReproductiveStage.LACTATING:
            multiplier, repro_confidence = lactation_multiplier(
                lactation_week=lactation_week,
                nursing_count=nursing_count,
                warnings=warnings,
            )
            if repro_confidence != EstimateConfidence.HIGH:
                confidence = repro_confidence
            breakdown["lactation_multiplier_over_maintenance"] = round(multiplier, 2)
            daily_energy = maintenance_energy * multiplier

        else:
            daily_energy = maintenance_energy

        breakdown["daily_energy_before_goal"] = round(daily_energy, 2)

    goal_multiplier = get_body_goal_multiplier(species, body_condition_goal)
    breakdown["body_goal_multiplier"] = round(goal_multiplier, 2)

    daily_energy *= goal_multiplier
    breakdown["daily_energy_final"] = round(daily_energy, 2)

    warnings.append(
        "This is a starting-point estimate; monitor body weight and body condition and adjust over 2-4 weeks."
    )
    warnings.append(
        "Animals of the same weight can differ substantially in actual calorie needs."
    )

    return round(daily_energy, 1), life_stage.value, breakdown, warnings, confidence.value