from typing import Optional
from enum import Enum as PyEnum


class Species(str, PyEnum):
    DOG = "dog"
    CAT = "cat"


class LifeStage(str, PyEnum):
    DOG_PUPPY = "dog_puppy"
    DOG_ADULT = "dog_adult"
    DOG_SENIOR = "dog_senior"
    CAT_KITTEN = "cat_kitten"
    CAT_ADULT = "cat_adult"
    CAT_SENIOR = "cat_senior"


class ActivityLevel(str, PyEnum):
    SEDENTARY = "sedentary"
    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"
    EXTREME = "extreme"


class SterilizationStatus(str, PyEnum):
    INTACT = "intact"
    NEUTERED = "neutered"


class ReproductiveStage(str, PyEnum):
    NONE = "none"
    PREGNANT = "pregnant"
    LACTATING = "lactating"


class BodyConditionGoal(str, PyEnum):
    MAINTAIN = "maintain"
    LOSE = "lose"
    GAIN = "gain"


class AdultEnergyProfile(str, PyEnum):
    LOW_ACTIVITY = "low_activity_adult"
    MODERATE_ACTIVITY = "moderate_activity_adult"
    ACTIVE = "active_adult"


class EstimateConfidence(str, PyEnum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"