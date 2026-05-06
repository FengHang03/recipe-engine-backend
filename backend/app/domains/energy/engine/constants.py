from __future__ import annotations
from typing import Optional

from app.domains.energy.contracts.enums import (
    ActivityLevel,
    AdultEnergyProfile,
    BodyConditionGoal,
    SterilizationStatus,
)


class EnergyConstants:
    RER_BASE_COEFFICIENT = 70.0
    RER_EXPONENT = 0.75

    DOG_ADULT_PROFILE_COEFFICIENTS = {
        AdultEnergyProfile.LOW_ACTIVITY: 95.0,
        AdultEnergyProfile.MODERATE_ACTIVITY: 112.0,
        AdultEnergyProfile.ACTIVE: 130.0,
    }

    CAT_ADULT_PROFILE_COEFFICIENTS = {
        AdultEnergyProfile.LOW_ACTIVITY: 70.0,
        AdultEnergyProfile.MODERATE_ACTIVITY: 84.0,
        AdultEnergyProfile.ACTIVE: 98.0,
    }

    DOG_PUPPY_EARLY_MAX = 4
    DOG_PUPPY_MAX = 12
    CAT_KITTEN_MAX = 12
    DEFAULT_DOG_SENIOR_MONTH = 84
    DEFAULT_CAT_SENIOR_MONTH = 132

    DOG_PUPPY_EARLY_FACTOR = 3.0
    DOG_PUPPY_LATE_FACTOR = 2.0
    CAT_KITTEN_FACTOR = 2.5

    DOG_ADULT_BASE = {
        SterilizationStatus.NEUTERED: 1.6,
        SterilizationStatus.INTACT: 1.8,
    }

    CAT_ADULT_BASE = {
        SterilizationStatus.NEUTERED: 1.2,
        SterilizationStatus.INTACT: 1.4,
    }

    DOG_ACTIVITY_DELTAS = {
        ActivityLevel.SEDENTARY: -0.2,
        ActivityLevel.LOW: -0.1,
        ActivityLevel.MODERATE: 0.0,
        ActivityLevel.HIGH: 0.2,
        ActivityLevel.EXTREME: 0.5,
    }

    CAT_ACTIVITY_DELTAS = {
        ActivityLevel.SEDENTARY: -0.1,
        ActivityLevel.LOW: 0.0,
        ActivityLevel.MODERATE: 0.1,
        ActivityLevel.HIGH: 0.2,
        ActivityLevel.EXTREME: 0.3,
    }

    YOUNG_ACTIVITY_MULTIPLIER = {
        ActivityLevel.SEDENTARY: 0.95,
        ActivityLevel.LOW: 0.98,
        ActivityLevel.MODERATE: 1.00,
        ActivityLevel.HIGH: 1.03,
        ActivityLevel.EXTREME: 1.05,
    }

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

    DOG_PREGNANCY_UNKNOWN_MULTIPLIER = 1.10
    CAT_PREGNANCY_UNKNOWN_MULTIPLIER = 1.15

    LACTATION_MIN_MULTIPLIER = 2.0
    LACTATION_MAX_MULTIPLIER = 4.0

    RANGE_ADULT = (0.85, 1.15)
    RANGE_GROWTH = (0.90, 1.10)
    RANGE_REPRO = (0.85, 1.20)
    RANGE_MANUAL = (0.90, 1.10)

    MIN_WEIGHT_KG = 0.5
    MAX_WEIGHT_KG = 100.0