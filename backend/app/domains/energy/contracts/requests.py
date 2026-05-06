from __future__ import annotations

from typing import Optional

from pydantic import BaseModel


from app.shared.contracts.enums import (
    Species, ActivityLevel, SterilizationStatus, ReproductiveStage, BodyConditionGoal
)


class EnergyCalculationRequest(BaseModel):
    weight_kg: float
    species: Species
    age_months: int
    activity_level: ActivityLevel
    sterilization_status: Optional[SterilizationStatus]
    reproductive_stage: Optional[ReproductiveStage]

    breed: Optional[str] = None
    lactation_week: Optional[int] = None
    nursing_count: Optional[int] = None
    senior_month: Optional[int] = None
    energy_requirement: Optional[float] = None
    body_condition_goal: BodyConditionGoal = BodyConditionGoal.MAINTAIN
    gestation_day: Optional[int] = None
    include_adult_profiles: bool = True
