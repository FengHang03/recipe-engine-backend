from app.domains.energy.contracts.enums import BodyConditionGoal, Species
from .constants import EnergyConstants


def get_body_goal_multiplier(species: Species, body_goal: BodyConditionGoal) -> float:
    if species == Species.DOG:
        return EnergyConstants.DOG_BODY_GOAL_MULTIPLIER[body_goal]
    return EnergyConstants.CAT_BODY_GOAL_MULTIPLIER[body_goal]