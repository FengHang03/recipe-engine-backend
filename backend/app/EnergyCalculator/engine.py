from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum as PyEnum
from typing import Dict, Optional, Tuple, List
import logging

logger = logging.getLogger(__name__)

from app.shared.contracts.enums import (
    Species, LifeStage, ActivityLevel, SterilizationStatus, ReproductiveStage, 
    AdultEnergyProfile, BodyConditionGoal, EstimateConfidence
)


class EnergyConstants:
    """
    Stable and product-friendly defaults.
    These are starting-point estimates, not exact truths.
    """

    # Core RER
    RER_BASE_COEFFICIENT = 70.0
    RER_EXPONENT = 0.75

    # Website-friendly adult profiles for dogs
    # low: WSAVA inactive-style anchor
    # moderate: 1.6 * RER = 112 * BW^0.75
    # active: WSAVA active-style anchor
    DOG_ADULT_PROFILE_COEFFICIENTS = {
        AdultEnergyProfile.LOW_ACTIVITY: 95.0,
        AdultEnergyProfile.MODERATE_ACTIVITY: 112.0,
        AdultEnergyProfile.ACTIVE: 130.0,
    }

    # Cat display profiles kept conservative
    CAT_ADULT_PROFILE_COEFFICIENTS = {
        AdultEnergyProfile.LOW_ACTIVITY: 70.0,
        AdultEnergyProfile.MODERATE_ACTIVITY: 84.0,
        AdultEnergyProfile.ACTIVE: 98.0,
    }

    # Age thresholds
    DOG_PUPPY_EARLY_MAX = 4
    DOG_PUPPY_MAX = 12
    CAT_KITTEN_MAX = 12
    DEFAULT_DOG_SENIOR_MONTH = 84
    DEFAULT_CAT_SENIOR_MONTH = 132

    # Growth factors
    DOG_PUPPY_EARLY_FACTOR = 3.0
    DOG_PUPPY_LATE_FACTOR = 2.0
    CAT_KITTEN_FACTOR = 2.5

    # Advanced adult baseline multipliers
    DOG_ADULT_BASE = {
        SterilizationStatus.NEUTERED: 1.6,
        SterilizationStatus.INTACT: 1.8,
    }

    CAT_ADULT_BASE = {
        SterilizationStatus.NEUTERED: 1.2,
        SterilizationStatus.INTACT: 1.4,
    }

    # Activity deltas for advanced estimate
    DOG_ACTIVITY_DELTAS = {
        ActivityLevel.SEDENTARY: -0.2,
        ActivityLevel.LOW: -0.1,
        ActivityLevel.MODERATE: 0.0,
        ActivityLevel.HIGH: +0.2,
        ActivityLevel.EXTREME: +0.5,
    }

    CAT_ACTIVITY_DELTAS = {
        ActivityLevel.SEDENTARY: -0.1,
        ActivityLevel.LOW: 0.0,
        ActivityLevel.MODERATE: +0.1,
        ActivityLevel.HIGH: +0.2,
        ActivityLevel.EXTREME: +0.3,
    }

    # Very small activity tweaks for growth animals
    YOUNG_ACTIVITY_MULTIPLIER = {
        ActivityLevel.SEDENTARY: 0.95,
        ActivityLevel.LOW: 0.98,
        ActivityLevel.MODERATE: 1.00,
        ActivityLevel.HIGH: 1.03,
        ActivityLevel.EXTREME: 1.05,
    }

    # Body goal multipliers
    DOG_BODY_GOAL_MULTIPLIER = {
        BodyConditionGoal.MAINTAIN: 1.00,
        BodyConditionGoal.LOSE: 0.85,
        BodyConditionGoal.GAIN: 1.10,
    }

    CAT_BODY_GOAL_MULTIPLIER = {
        BodyConditionGoal.MAINTAIN: 1.00,
        BodyConditionGoal.LOSE: 0.85,
        BodyConditionGoal.GAIN: 1.08,
    }

    # Pregnancy
    DOG_GESTATION_MULTIPLIERS = {
        "early": 1.00,
        "mid": 1.10,
        "late": 1.25,
    }

    CAT_GESTATION_MULTIPLIERS = {
        "early": 1.10,
        "mid": 1.20,
        "late": 1.30,
    }

    # When gestation day is unknown, be conservative
    DOG_PREGNANCY_UNKNOWN_MULTIPLIER = 1.10
    CAT_PREGNANCY_UNKNOWN_MULTIPLIER = 1.15

    # Lactation
    LACTATION_MIN_MULTIPLIER = 2.0
    LACTATION_MAX_MULTIPLIER = 4.0

    # Range defaults by context
    RANGE_ADULT = (0.85, 1.15)
    RANGE_GROWTH = (0.90, 1.10)
    RANGE_REPRO = (0.85, 1.20)
    RANGE_MANUAL = (0.90, 1.10)

    # Guardrails
    MIN_WEIGHT_KG = 0.5
    MAX_WEIGHT_KG = 100.0


@dataclass
class EnergyCalculationResult:
    resting_energy_kcal: float
    daily_energy_kcal: float
    target_kcal_range: Tuple[float, float]
    life_stage: str
    model_version: str
    calculation_breakdown: Dict[str, float] = field(default_factory=dict)
    warnings: List[str] = field(default_factory=list)
    confidence: str = EstimateConfidence.HIGH.value
    adult_energy_profiles: Optional[Dict[str, float]] = None
    default_adult_profile: Optional[str] = None


class EnergyCalculator:
    """
    Product-friendly energy estimator.

    Recommended usage:
    1) For website display for healthy adult pets:
       use calculate_adult_energy_profiles(...)
    2) For individualized estimate:
       use calculate_daily_energy_requirement(...)
    """

    VERSION = "EnergyCalculator-v1.1-product"

    @staticmethod
    def calculate_resting_energy_requirement(weight_kg: float) -> float:
        if weight_kg <= 0:
            raise ValueError("weight_kg must be > 0")
        return EnergyConstants.RER_BASE_COEFFICIENT * (
            weight_kg ** EnergyConstants.RER_EXPONENT
        )

    @staticmethod
    def _bw075(weight_kg: float) -> float:
        return weight_kg ** EnergyConstants.RER_EXPONENT

    @staticmethod
    def _validate_inputs(
        weight_kg: float,
        age_months: int,
        lactation_week: Optional[int],
        nursing_count: Optional[int],
        gestation_day: Optional[int],
    ) -> List[str]:
        warnings: List[str] = []

        if weight_kg <= 0:
            raise ValueError(f"weight_kg must be > 0, got {weight_kg}")
        if age_months < 0:
            raise ValueError(f"age_months must be >= 0, got {age_months}")

        if weight_kg < EnergyConstants.MIN_WEIGHT_KG:
            warnings.append(
                f"Very low body weight ({weight_kg} kg): estimate may be less reliable."
            )
        if weight_kg > EnergyConstants.MAX_WEIGHT_KG:
            warnings.append(
                f"Very high body weight ({weight_kg} kg): estimate may be less reliable."
            )

        if lactation_week is not None and not (1 <= lactation_week <= 8):
            raise ValueError(f"lactation_week must be between 1 and 8, got {lactation_week}")

        if nursing_count is not None and nursing_count < 0:
            raise ValueError(f"nursing_count must be >= 0, got {nursing_count}")

        if gestation_day is not None and not (1 <= gestation_day <= 70):
            raise ValueError(f"gestation_day must be between 1 and 70, got {gestation_day}")

        return warnings

    @staticmethod
    def _default_senior_month(species: Species) -> int:
        if species == Species.DOG:
            return EnergyConstants.DEFAULT_DOG_SENIOR_MONTH
        return EnergyConstants.DEFAULT_CAT_SENIOR_MONTH

    @classmethod
    def get_life_stage_factor(
        cls,
        species: Species,
        age_months: int,
        senior_month: Optional[int] = None,
    ) -> Tuple[float, LifeStage]:
        if senior_month is None:
            senior_month = cls._default_senior_month(species)

        if species == Species.DOG:
            if age_months < EnergyConstants.DOG_PUPPY_EARLY_MAX:
                return EnergyConstants.DOG_PUPPY_EARLY_FACTOR, LifeStage.DOG_PUPPY
            if age_months < EnergyConstants.DOG_PUPPY_MAX:
                return EnergyConstants.DOG_PUPPY_LATE_FACTOR, LifeStage.DOG_PUPPY
            if age_months >= senior_month:
                return 1.0, LifeStage.DOG_SENIOR
            return 1.0, LifeStage.DOG_ADULT

        return 1.0, LifeStage.DOG_ADULT

    @classmethod
    def calculate_adult_energy_profiles(
        cls,
        weight_kg: float,
        species: Species = Species.DOG,
    ) -> Dict[str, float]:
        """
        Simple, front-end-friendly profiles for healthy adult animals.
        Use this for website display cards or profile selection.
        """
        if weight_kg <= 0:
            raise ValueError("weight_kg must be > 0")

        bw075 = cls._bw075(weight_kg)

        if species == Species.DOG:
            coeffs = EnergyConstants.DOG_ADULT_PROFILE_COEFFICIENTS
        else:
            coeffs = EnergyConstants.CAT_ADULT_PROFILE_COEFFICIENTS

        return {
            profile.value: round(coeff * bw075, 1)
            for profile, coeff in coeffs.items()
        }

    @staticmethod
    def _young_activity_multiplier(activity_level: ActivityLevel) -> float:
        return EnergyConstants.YOUNG_ACTIVITY_MULTIPLIER[activity_level]

    @staticmethod
    def _adult_maintenance_multiplier(
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

    @staticmethod
    def _body_goal_multiplier(
        species: Species,
        body_goal: BodyConditionGoal,
    ) -> float:
        if species == Species.DOG:
            return EnergyConstants.DOG_BODY_GOAL_MULTIPLIER[body_goal]
        return EnergyConstants.CAT_BODY_GOAL_MULTIPLIER[body_goal]

    @staticmethod
    def _pregnancy_multiplier(
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

    @staticmethod
    def _lactation_multiplier(
        lactation_week: Optional[int],
        nursing_count: Optional[int],
        warnings: List[str],
    ) -> Tuple[float, EstimateConfidence]:
        confidence = EstimateConfidence.HIGH

        if lactation_week is None:
            lactation_week = 3
            warnings.append(
                "lactation_week not provided; assuming week 3."
            )
            confidence = EstimateConfidence.MEDIUM

        if nursing_count is None:
            nursing_count = 4
            warnings.append(
                "nursing_count not provided; assuming 4 nursing young."
            )
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

    @staticmethod
    def _starting_range(
        daily_energy_kcal: float,
        low_factor: float,
        high_factor: float,
    ) -> Tuple[float, float]:
        low = daily_energy_kcal * low_factor
        high = daily_energy_kcal * high_factor
        return round(low, 1), round(high, 1)

    @classmethod
    def calculate_scaling_factor(
        cls,
        target_energy_kcal: float,
        target_calories_kcal: float,
    ) -> float:
        if target_energy_kcal <= 0:
            raise ValueError("target_energy_kcal must be > 0")
        if target_calories_kcal <= 0:
            raise ValueError("target_calories_kcal must be > 0")
        return round(target_energy_kcal / target_calories_kcal, 4)

    @classmethod
    def calculate_daily_energy_requirement(
        cls,
        weight_kg: float,
        species: Species,
        age_months: int,
        activity_level: ActivityLevel,
        sterilization_status: SterilizationStatus,
        reproductive_stage: ReproductiveStage,
        breed: Optional[str] = None,
        lactation_week: Optional[int] = None,
        nursing_count: Optional[int] = None,
        senior_month: Optional[int] = None,
        energy_requirement: Optional[float] = None,
        body_condition_goal: BodyConditionGoal = BodyConditionGoal.MAINTAIN,
        gestation_day: Optional[int] = None,
        include_adult_profiles: bool = True,
    ) -> EnergyCalculationResult:
        warnings = cls._validate_inputs(
            weight_kg=weight_kg,
            age_months=age_months,
            lactation_week=lactation_week,
            nursing_count=nursing_count,
            gestation_day=gestation_day,
        )

        breakdown: Dict[str, float] = {}
        confidence = EstimateConfidence.HIGH

        rer = cls.calculate_resting_energy_requirement(weight_kg)
        breakdown["rer"] = round(rer, 2)

        life_stage_factor, life_stage = cls.get_life_stage_factor(
            species=species,
            age_months=age_months,
            senior_month=senior_month,
        )
        breakdown["life_stage_factor"] = round(life_stage_factor, 2)

        is_young = life_stage in {LifeStage.DOG_PUPPY}
        is_senior = life_stage in {LifeStage.DOG_SENIOR}
        is_repro = reproductive_stage in {ReproductiveStage.PREGNANT, ReproductiveStage.LACTATING}

        adult_profiles: Optional[Dict[str, float]] = None
        default_adult_profile: Optional[str] = None
        if include_adult_profiles and species in {Species.DOG, Species.CAT}:
            adult_profiles = cls.calculate_adult_energy_profiles(weight_kg, species)
            default_adult_profile = AdultEnergyProfile.MODERATE_ACTIVITY.value

        if breed:
            warnings.append(
                "breed is currently accepted for compatibility only and is not used in energy calculation."
            )

        if energy_requirement is not None:
            if energy_requirement <= 0:
                raise ValueError("energy_requirement must be > 0")

            return EnergyCalculationResult(
                resting_energy_kcal=round(rer, 1),
                daily_energy_kcal=round(energy_requirement, 1),
                target_kcal_range=cls._starting_range(
                    energy_requirement,
                    *EnergyConstants.RANGE_MANUAL,
                ),
                life_stage=life_stage.value,
                model_version=cls.VERSION,
                calculation_breakdown={
                    "rer": round(rer, 2),
                    "manual_override": round(energy_requirement, 2),
                },
                warnings=warnings + ["Using manual energy override."],
                confidence=EstimateConfidence.HIGH.value,
                adult_energy_profiles=adult_profiles,
                default_adult_profile=default_adult_profile,
            )

        if is_young and reproductive_stage in {ReproductiveStage.PREGNANT, ReproductiveStage.LACTATING}:
            warnings.append(
                f"{life_stage.value} with reproductive_stage={reproductive_stage.value} is inconsistent; "
                "reverting to normal growth estimate."
            )
            reproductive_stage = ReproductiveStage.NONE
            is_repro = False
            confidence = EstimateConfidence.MEDIUM

        if is_young:
            young_activity = cls._young_activity_multiplier(activity_level)
            breakdown["young_activity_multiplier"] = round(young_activity, 3)

            daily_energy = rer * life_stage_factor * young_activity
            breakdown["daily_energy_before_goal"] = round(daily_energy, 2)

            range_low, range_high = EnergyConstants.RANGE_GROWTH

        else:
            adult_multiplier = cls._adult_maintenance_multiplier(
                species=species,
                sterilization_status=sterilization_status,
                activity_level=activity_level,
            )
            breakdown["adult_maintenance_multiplier"] = round(adult_multiplier, 2)

            maintenance_energy = rer * adult_multiplier
            breakdown["maintenance_energy"] = round(maintenance_energy, 2)

            if is_senior:
                warnings.append(
                    "Senior status does not trigger an automatic calorie reduction here. "
                    "Adjust according to body condition, muscle condition, and weight trend."
                )

            if reproductive_stage == ReproductiveStage.PREGNANT:
                preg_multiplier = cls._pregnancy_multiplier(
                    species=species,
                    gestation_day=gestation_day,
                    warnings=warnings,
                )
                if gestation_day is None:
                    confidence = EstimateConfidence.MEDIUM

                breakdown["pregnancy_multiplier_over_maintenance"] = round(preg_multiplier, 2)
                daily_energy = maintenance_energy * preg_multiplier
                breakdown["daily_energy_before_goal"] = round(daily_energy, 2)
                range_low, range_high = EnergyConstants.RANGE_REPRO

            elif reproductive_stage == ReproductiveStage.LACTATING:
                lact_multiplier, lact_confidence = cls._lactation_multiplier(
                    lactation_week=lactation_week,
                    nursing_count=nursing_count,
                    warnings=warnings,
                )
                if lact_confidence != EstimateConfidence.HIGH:
                    confidence = lact_confidence

                breakdown["lactation_multiplier_over_maintenance"] = round(lact_multiplier, 2)
                daily_energy = maintenance_energy * lact_multiplier
                breakdown["daily_energy_before_goal"] = round(daily_energy, 2)
                range_low, range_high = EnergyConstants.RANGE_REPRO

            else:
                daily_energy = maintenance_energy
                breakdown["daily_energy_before_goal"] = round(daily_energy, 2)
                range_low, range_high = EnergyConstants.RANGE_ADULT

        goal_multiplier = cls._body_goal_multiplier(species, body_condition_goal)
        breakdown["body_goal_multiplier"] = round(goal_multiplier, 2)

        daily_energy *= goal_multiplier
        breakdown["daily_energy_final"] = round(daily_energy, 2)

        warnings.append(
            "This is a starting-point estimate; monitor body weight and body condition and adjust over 2-4 weeks."
        )
        warnings.append(
            "Animals of the same weight can differ substantially in actual calorie needs."
        )

        daily_energy_rounded = round(daily_energy, 1)
        target_range = cls._starting_range(
            daily_energy_rounded,
            range_low,
            range_high,
        )

        return EnergyCalculationResult(
            resting_energy_kcal=round(rer, 1),
            daily_energy_kcal=daily_energy_rounded,
            target_kcal_range=target_range,
            life_stage=life_stage.value,
            model_version=cls.VERSION,
            calculation_breakdown=breakdown,
            warnings=warnings,
            confidence=confidence.value,
            adult_energy_profiles=adult_profiles,
            default_adult_profile=default_adult_profile,
        )
