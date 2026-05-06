from __future__ import annotations

from typing import List, Optional

from app.domains.energy.contracts.enums import EstimateConfidence
from app.domains.energy.contracts.models import EnergyCalculationResult
from app.domains.energy.contracts.requests import EnergyCalculationRequest
from app.domains.energy.engine.adult_profiles import calculate_adult_energy_profiles
from app.domains.energy.engine.constants import EnergyConstants
from app.domains.energy.engine.estimator import estimate_energy
from app.domains.energy.engine.ranges import build_starting_range, get_range_factors
from app.domains.energy.engine.rer import calculate_rer
from app.domains.energy.engine.life_stage import get_life_stage_factor


def validate_inputs(
    weight_kg: float,
    age_months: int,
    lactation_week,
    nursing_count,
    gestation_day,
) -> List[str]:
    warnings: List[str] = []

    if weight_kg <= 0:
        raise ValueError(f"weight_kg must be > 0, got {weight_kg}")
    if age_months < 0:
        raise ValueError(f"age_months must be >= 0, got {age_months}")

    if weight_kg < EnergyConstants.MIN_WEIGHT_KG:
        warnings.append(f"Very low body weight ({weight_kg} kg): estimate may be less reliable.")
    if weight_kg > EnergyConstants.MAX_WEIGHT_KG:
        warnings.append(f"Very high body weight ({weight_kg} kg): estimate may be less reliable.")

    if lactation_week is not None and not (1 <= lactation_week <= 8):
        raise ValueError(f"lactation_week must be between 1 and 8, got {lactation_week}")
    if nursing_count is not None and nursing_count < 0:
        raise ValueError(f"nursing_count must be >= 0, got {nursing_count}")
    if gestation_day is not None and not (1 <= gestation_day <= 70):
        raise ValueError(f"gestation_day must be between 1 and 70, got {gestation_day}")

    return warnings


class EnergyService:
    VERSION = "EnergyCalculator-v1.1-product"

    @classmethod
    def calculate(cls, req: EnergyCalculationRequest) -> EnergyCalculationResult:
        warnings = validate_inputs(
            weight_kg=req.weight_kg,
            age_months=req.age_months,
            lactation_week=req.lactation_week,
            nursing_count=req.nursing_count,
            gestation_day=req.gestation_day,
        )

        rer = round(calculate_rer(req.weight_kg), 1)

        adult_profiles = None
        default_profile = None
        if req.include_adult_profiles:
            profiles_result = calculate_adult_energy_profiles(req.weight_kg, req.species)
            adult_profiles = profiles_result.profiles
            default_profile = profiles_result.default_profile

        if req.energy_requirement is not None:
            if req.energy_requirement <= 0:
                raise ValueError("energy_requirement must be > 0")

            return EnergyCalculationResult(
                resting_energy_kcal=rer,
                daily_energy_kcal=round(req.energy_requirement, 1),
                target_kcal_range=build_starting_range(
                    req.energy_requirement,
                    *EnergyConstants.RANGE_MANUAL,
                ),
                life_stage=get_life_stage_factor(req.species, req.age_months, req.senior_month)[1].value,
                model_version=cls.VERSION,
                calculation_breakdown={
                    "rer": round(rer, 2),
                    "manual_override": round(req.energy_requirement, 2),
                },
                warnings=warnings + ["Using manual energy override."],
                confidence=EstimateConfidence.HIGH.value,
                adult_energy_profiles=adult_profiles,
                default_adult_profile=default_profile,
            )

        if req.breed:
            warnings.append(
                "breed is currently accepted for compatibility only and is not used in energy calculation."
            )

        daily_energy, life_stage, breakdown, engine_warnings, confidence = estimate_energy(
            weight_kg=req.weight_kg,
            species=req.species,
            age_months=req.age_months,
            activity_level=req.activity_level,
            sterilization_status=req.sterilization_status,
            reproductive_stage=req.reproductive_stage,
            body_condition_goal=req.body_condition_goal,
            gestation_day=req.gestation_day,
            lactation_week=req.lactation_week,
            nursing_count=req.nursing_count,
            senior_month=req.senior_month,
        )

        warnings.extend(engine_warnings)

        _, life_stage_enum = get_life_stage_factor(req.species, req.age_months, req.senior_month)
        low_factor, high_factor = get_range_factors(life_stage_enum, req.reproductive_stage)

        return EnergyCalculationResult(
            resting_energy_kcal=rer,
            daily_energy_kcal=daily_energy,
            target_kcal_range=build_starting_range(daily_energy, low_factor, high_factor),
            life_stage=life_stage,
            model_version=cls.VERSION,
            calculation_breakdown=breakdown,
            warnings=warnings,
            confidence=confidence,
            adult_energy_profiles=adult_profiles,
            default_adult_profile=default_profile,
        )