from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum as PyEnum
from typing import Dict, Optional, Tuple, List
import logging

logger = logging.getLogger(__name__)

from app.shared.contracts.pet import (
    Species, LifeStage, ActivityLevel, 
    SterilizationStatus, ReproductiveStage
)


class BodyConditionGoal(str, PyEnum):
    MAINTAIN = "maintain"
    LOSE = "lose"
    GAIN = "gain"


class EnergyConstants:
    """
    Conservative, clinic-friendly defaults.
    These are starting points, not absolutes.
    """

    # RER
    RER_BASE_COEFFICIENT = 70.0
    RER_EXPONENT = 0.75

    # Age thresholds
    DOG_PUPPY_EARLY_MAX = 4      # < 4 mo
    DOG_PUPPY_MAX = 12           # < 12 mo
    CAT_KITTEN_MAX = 12
    DEFAULT_DOG_SENIOR_MONTH = 84   # 7 years
    DEFAULT_CAT_SENIOR_MONTH = 132  # 11 years

    # Puppy / kitten growth factors
    DOG_PUPPY_EARLY_FACTOR = 3.0
    DOG_PUPPY_LATE_FACTOR = 2.0
    CAT_KITTEN_FACTOR = 2.5

    # Adult dog maintenance starting points
    # Based on common veterinary starting points:
    # neutered adult ~1.6 x RER, intact adult ~1.8 x RER
    DOG_ADULT_BASE = {
        SterilizationStatus.NEUTERED: 1.6,
        SterilizationStatus.INTACT: 1.8,
    }

    # Adult cat maintenance starting points
    CAT_ADULT_BASE = {
        SterilizationStatus.NEUTERED: 1.2,
        SterilizationStatus.INTACT: 1.4,
    }

    # Activity adjustments for ADULT maintenance only
    # These are deltas applied around the base multiplier.
    # Keep conservative; don't double-count life-stage growth needs.
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

    # Puppy/kitten activity: only tiny nudges
    YOUNG_ACTIVITY_MULTIPLIER = {
        ActivityLevel.SEDENTARY: 0.95,
        ActivityLevel.LOW: 0.98,
        ActivityLevel.MODERATE: 1.00,
        ActivityLevel.HIGH: 1.03,
        ActivityLevel.EXTREME: 1.05,
    }

    # Body condition goal adjustments
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

    # Pregnancy (dogs)
    # Early gestation ≈ maintenance.
    # Last third often needs +20% to +30% over maintenance.
    DOG_GESTATION_MULTIPLIERS = {
        "early": 1.00,   # day 1-41
        "mid": 1.10,     # day 42-49
        "late": 1.25,    # day 50-63
    }

    # Pregnancy (cats) tends to increase earlier and more continuously.
    CAT_GESTATION_MULTIPLIERS = {
        "early": 1.10,
        "mid": 1.20,
        "late": 1.30,
    }

    # Lactation target range is usually ~2-4 x maintenance.
    LACTATION_MIN_MULTIPLIER = 2.0
    LACTATION_MAX_MULTIPLIER = 4.0

    # Merck: formulas are starting points; animals can vary a lot.
    DEFAULT_RANGE_LOW = 0.85
    DEFAULT_RANGE_HIGH = 1.15

    # Validity guardrails
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


class EnergyCalculator:
    """
    More stable veterinary-style energy estimator.

    Philosophy:
    - Keep the scientifically stable core.
    - Avoid stacking too many speculative modifiers.
    - Return a starting point + reasonable range.
    - Let body weight trend / BCS guide real-world adjustment.
    """

    VERSION = "EnergyCalculator-v1.0-stable"

    @staticmethod
    def calculate_resting_energy_requirement(weight_kg: float) -> float:
        """
        RER = 70 * BW^0.75
        """
        if weight_kg <= 0:
            raise ValueError("weight_kg must be > 0")

        return EnergyConstants.RER_BASE_COEFFICIENT * (
            weight_kg ** EnergyConstants.RER_EXPONENT
        )

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

        return warnings

    @staticmethod
    def get_life_stage_factor(species: Species, age_months: int) -> Tuple[float, LifeStage]:
        if species == Species.DOG:
            if age_months < EnergyConstants.DOG_PUPPY_EARLY_MAX:
                return EnergyConstants.DOG_PUPPY_EARLY_FACTOR, LifeStage.DOG_PUPPY
            if age_months < EnergyConstants.DOG_PUPPY_MAX:
                return EnergyConstants.DOG_PUPPY_LATE_FACTOR, LifeStage.DOG_PUPPY
            if age_months >= EnergyConstants.DEFAULT_DOG_SENIOR_MONTH:
                return 1.0, LifeStage.DOG_SENIOR
            return 1.0, LifeStage.DOG_ADULT

        return 1.0, LifeStage.DOG_ADULT

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
        """
        If gestation_day is missing, return a conservative late-gestation starting point
        and warn the caller.
        """
        if gestation_day is None:
            warnings.append(
                "Pregnancy calculation is more precise with gestation_day. "
                "Using a conservative late-gestation starting multiplier."
            )
            return 1.25 if species == Species.DOG else 1.20

        if species == Species.DOG:
            if gestation_day <= 41:
                return EnergyConstants.DOG_GESTATION_MULTIPLIERS["early"]
            if gestation_day <= 49:
                return EnergyConstants.DOG_GESTATION_MULTIPLIERS["mid"]
            return EnergyConstants.DOG_GESTATION_MULTIPLIERS["late"]

        # cats
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
    ) -> float:
        """
        Stable heuristic bounded to 2.0-4.0 x maintenance.
        """
        if lactation_week is None:
            lactation_week = 3
            warnings.append(
                "lactation_week not provided; assuming week 3 (near peak demand)."
            )

        if nursing_count is None:
            nursing_count = 4
            warnings.append(
                "nursing_count not provided; assuming 4 nursing young."
            )

        # Week effect: peaks around weeks 3-4
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

        # Litter size effect: capped to avoid unrealistic outputs
        litter_component = min(1.0, max(0.0, 0.12 * max(0, nursing_count - 1)))

        multiplier = 2.0 + week_component + litter_component
        return min(EnergyConstants.LACTATION_MAX_MULTIPLIER,
                   max(EnergyConstants.LACTATION_MIN_MULTIPLIER, multiplier))

    @staticmethod
    def _starting_range(daily_energy_kcal: float) -> Tuple[float, float]:
        low = daily_energy_kcal * EnergyConstants.DEFAULT_RANGE_LOW
        high = daily_energy_kcal * EnergyConstants.DEFAULT_RANGE_HIGH
        return round(low, 1), round(high, 1)

    @classmethod
    def calculate_daily_energy_requirement(
        cls,
        weight_kg: float,
        species: Species,
        age_months: int,
        activity_level: ActivityLevel,
        sterilization_status: SterilizationStatus,
        reproductive_stage: ReproductiveStage,
        breed: Optional[str] = None,  # kept for compatibility; not used by default
        lactation_week: Optional[int] = None,
        nursing_count: Optional[int] = None,
        senior_month: Optional[int] = None,
        energy_requirement: Optional[float] = None,
        body_condition_goal: BodyConditionGoal = BodyConditionGoal.MAINTAIN,
        gestation_day: Optional[int] = None,
    ) -> EnergyCalculationResult:
        """
        Main entry point.
        """

        warnings = cls._validate_inputs(
            weight_kg=weight_kg,
            age_months=age_months,
            lactation_week=lactation_week,
            nursing_count=nursing_count,
            gestation_day=gestation_day,
        )
        breakdown: Dict[str, float] = {}

        rer = cls.calculate_resting_energy_requirement(weight_kg)
        breakdown["rer"] = round(rer, 2)

        life_stage_factor, life_stage = cls.get_life_stage_factor(species, age_months)
        breakdown["life_stage_factor"] = round(life_stage_factor, 2)

        is_young = life_stage in {LifeStage.DOG_PUPPY}
        is_senior = life_stage in {LifeStage.DOG_SENIOR}

        if breed:
            warnings.append(
                "breed parameter is currently ignored by default to avoid "
                "overfitting energy estimates with weak prior assumptions."
            )

        # Manual override
        if energy_requirement is not None:
            if energy_requirement <= 0:
                raise ValueError("energy_requirement must be > 0")
            return EnergyCalculationResult(
                resting_energy_kcal=round(rer, 1),
                daily_energy_kcal=round(energy_requirement, 1),
                target_kcal_range=cls._starting_range(energy_requirement),
                life_stage=life_stage.value,
                model_version=cls.VERSION,
                calculation_breakdown={
                    "rer": round(rer, 2),
                    "manual_override": round(energy_requirement, 2),
                },
                warnings=warnings + ["Using manual energy override."],
            )

        # Prevent impossible combination
        if is_young and reproductive_stage in {ReproductiveStage.PREGNANT, ReproductiveStage.LACTATING}:
            warnings.append(
                f"{life_stage.value} with reproductive_stage={reproductive_stage.value} is inconsistent; "
                "reverting to normal growth estimate."
            )
            reproductive_stage = ReproductiveStage.NONE

        # 1) Growth
        if is_young:
            young_activity = cls._young_activity_multiplier(activity_level)
            breakdown["young_activity_multiplier"] = round(young_activity, 3)

            daily_energy = rer * life_stage_factor * young_activity
            breakdown["daily_energy_before_goal"] = round(daily_energy, 2)

        # 2) Adult / senior baseline maintenance
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
                    "Adjust according to BCS, muscle condition, and body-weight trend."
                )

            if reproductive_stage == ReproductiveStage.PREGNANT:
                preg_multiplier = cls._pregnancy_multiplier(
                    species=species,
                    gestation_day=gestation_day,
                    warnings=warnings,
                )
                breakdown["pregnancy_multiplier_over_maintenance"] = round(preg_multiplier, 2)
                daily_energy = maintenance_energy * preg_multiplier
                breakdown["daily_energy_before_goal"] = round(daily_energy, 2)

            elif reproductive_stage == ReproductiveStage.LACTATING:
                lact_multiplier = cls._lactation_multiplier(
                    lactation_week=lactation_week,
                    nursing_count=nursing_count,
                    warnings=warnings,
                )
                breakdown["lactation_multiplier_over_maintenance"] = round(lact_multiplier, 2)
                daily_energy = maintenance_energy * lact_multiplier
                breakdown["daily_energy_before_goal"] = round(daily_energy, 2)

            else:
                daily_energy = maintenance_energy
                breakdown["daily_energy_before_goal"] = round(daily_energy, 2)

        # 3) Body condition goal adjustment
        goal_multiplier = cls._body_goal_multiplier(species, body_condition_goal)
        breakdown["body_goal_multiplier"] = round(goal_multiplier, 2)

        daily_energy *= goal_multiplier
        breakdown["daily_energy_final"] = round(daily_energy, 2)

        # 4) Warnings about interpretation
        warnings.append(
            "This is a starting-point estimate; monitor body weight and body condition "
            "and adjust intake over 2-4 weeks."
        )
        warnings.append(
            "Animals of the same weight can differ substantially in actual calorie needs."
        )

        daily_energy_rounded = round(daily_energy, 1)
        target_range = cls._starting_range(daily_energy_rounded)

        return EnergyCalculationResult(
            resting_energy_kcal=round(rer, 1),
            daily_energy_kcal=daily_energy_rounded,
            target_kcal_range=target_range,
            life_stage=life_stage.value,
            model_version=cls.VERSION,
            calculation_breakdown=breakdown,
            warnings=warnings,
        )
