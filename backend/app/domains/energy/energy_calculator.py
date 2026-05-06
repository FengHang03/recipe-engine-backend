from app.domains.energy.contracts.requests import EnergyCalculationRequest
from app.domains.energy.orchestration.energy_service import EnergyService
from app.domains.energy.engine.scaling import calculate_scaling_factor
from app.domains.energy.engine.adult_profiles import calculate_adult_energy_profiles

from app.shared.contracts.enums import (
    Species,
    LifeStage,
    ActivityLevel,
    SterilizationStatus,
    ReproductiveStage,
    BodyConditionGoal,
)
from app.domains.energy.contracts.models import EnergyCalculationResult


class EnergyCalculator:
    VERSION = EnergyService.VERSION

    @staticmethod
    def calculate_resting_energy_requirement(weight_kg: float) -> float:
        from app.domains.energy.engine.rer import calculate_rer
        return calculate_rer(weight_kg)

    @staticmethod
    def calculate_adult_energy_profiles(weight_kg: float, species: Species = Species.DOG):
        return calculate_adult_energy_profiles(weight_kg, species)

    @staticmethod
    def calculate_scaling_factor(target_energy_kcal: float, target_calories_kcal: float) -> float:
        return calculate_scaling_factor(target_energy_kcal, target_calories_kcal)

    @classmethod
    def calculate_daily_energy_requirement(
        cls,
        weight_kg: float,
        species: Species,
        age_months: int,
        activity_level: ActivityLevel,
        sterilization_status: SterilizationStatus,
        reproductive_stage: ReproductiveStage,
        breed: str | None = None,
        lactation_week: int | None = None,
        nursing_count: int | None = None,
        senior_month: int | None = None,
        energy_requirement: float | None = None,
        body_condition_goal: BodyConditionGoal = BodyConditionGoal.MAINTAIN,
        gestation_day: int | None = None,
        include_adult_profiles: bool = True,
    ) -> EnergyCalculationResult:
        req = EnergyCalculationRequest(
            weight_kg=weight_kg,
            species=species,
            age_months=age_months,
            activity_level=activity_level,
            sterilization_status=sterilization_status,
            reproductive_stage=reproductive_stage,
            breed=breed,
            lactation_week=lactation_week,
            nursing_count=nursing_count,
            senior_month=senior_month,
            energy_requirement=energy_requirement,
            body_condition_goal=body_condition_goal,
            gestation_day=gestation_day,
            include_adult_profiles=include_adult_profiles,
        )
        return EnergyService.calculate(req)