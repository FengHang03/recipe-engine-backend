from __future__ import annotations

import os
from typing import Optional

from fastapi import Request

from app.db.connection import create_db_engine

from app.domains.recipe_generation.orchestration.generate_recipe_service import (
    RecipeGenerationService,
)
from app.domains.recipe_generation.orchestration.validators.request_validator import (
    RecipeRequestValidator,
)
from app.domains.recipe_generation.orchestration.explain_payload_builder import (
    ExplainPayloadBuilder,
)
from app.domains.recipe_generation.orchestration.execution_planner import (
    ExecutionPlanner,
)
from app.domains.recipe_generation.orchestration.request_router import (
    RequestRouter,
)

from app.domains.recipe_generation.engines.scaling.preset_scaler import PresetScaler
from app.domains.recipe_generation.engines.diy.beginner_diy_preview import (
    BeginnerDiyPreviewService,
)

# from app.domains.recipe_generation.infra.repositories.ingredient_repository import (
#     IngredientRepository,
# )
from app.domains.ingredients.infra.ingredient_nutrients_repository import (
    IngredientNutrientsRepository,
)
from app.domains.ingredients.infra.ingredient_repository import (
    IngredientRepository,
)
from app.domains.recipe_generation.infra.repositories.preset_recipe_repository import (
    PresetRecipeRepository,
)
from app.domains.recipe_generation.infra.mappers.recipe_spec_mapper import (
    RecipeSpecMapper,
)

from app.domains.ingredients.analysis_prep_service import (
    AnalysisPrepService,
)
from app.domains.nutrient_analysis.input_preparation_service import (
    NutrientAnalysisInputPreparationService,
)
from app.domains.nutrient_analysis.nutrient_analysis_service import (
    NutrientAnalysisService as DomainNutrientAnalysisService,
)


# ------------------------------------------------------------------
# Low-level shared resources
# ------------------------------------------------------------------

def get_db_engine(request: Request):
    """
    Prefer the engine already created during app lifespan.
    Fallback to DATABASE_URL only when app.state is unavailable.
    """
    engine = getattr(request.app.state, "db_engine", None)
    if engine is not None:
        return engine

    connection_string = os.getenv("DATABASE_URL")
    if not connection_string:
        raise RuntimeError("DATABASE_URL is not configured.")
    return create_db_engine(connection_string)


# ------------------------------------------------------------------
# Repositories
# ------------------------------------------------------------------

def get_ingredient_repository(request: Request) -> IngredientRepository:
    repo = getattr(request.app.state, "ingredient_repository", None)
    if repo is not None:
        return repo

    data_cache = getattr(request.app.state, "ingredient_data_cache", None)
    engine = get_db_engine(request)
    return IngredientRepository(engine=engine, data_cache=data_cache)


def get_ingredient_nutrients_repository(
    request: Request,
) -> IngredientNutrientsRepository:
    repo = getattr(request.app.state, "ingredient_nutrients_repository", None)
    if repo is not None:
        return repo

    data_cache = getattr(request.app.state, "ingredient_data_cache", None)
    engine = get_db_engine(request)
    return IngredientNutrientsRepository(engine=engine, data_cache=data_cache)


def get_preset_recipe_repository() -> PresetRecipeRepository:
    return PresetRecipeRepository()


def get_recipe_spec_mapper() -> RecipeSpecMapper:
    return RecipeSpecMapper()


# ------------------------------------------------------------------
# Domain services
# ------------------------------------------------------------------

def get_analysis_prep_service() -> AnalysisPrepService:
    return AnalysisPrepService()


def get_nutrient_analysis_input_preparation_service() -> NutrientAnalysisInputPreparationService:
    return NutrientAnalysisInputPreparationService(
        analysis_prep_service=get_analysis_prep_service()
    )


def get_domain_nutrient_analysis_service() -> DomainNutrientAnalysisService:
    return DomainNutrientAnalysisService()


def get_beginner_diy_preview_service() -> BeginnerDiyPreviewService:
    return BeginnerDiyPreviewService(
        input_preparation_service=get_nutrient_analysis_input_preparation_service(),
        nutrient_analysis_service=get_domain_nutrient_analysis_service(),
    )


# ------------------------------------------------------------------
# Orchestration
# ------------------------------------------------------------------

def get_execution_planner() -> ExecutionPlanner:
    return ExecutionPlanner()


def get_recipe_generation_service(request: Request) -> RecipeGenerationService:
    ingredient_repository = get_ingredient_repository(request)
    ingredient_nutrients_repository = get_ingredient_nutrients_repository(request)
    preset_recipe_repository = get_preset_recipe_repository()
    recipe_spec_mapper = get_recipe_spec_mapper()

    preset_scaler = PresetScaler()
    nutrient_analysis_service = get_domain_nutrient_analysis_service()
    nutrient_analysis_input_preparation_service = get_nutrient_analysis_input_preparation_service()
    beginner_diy_preview_service = get_beginner_diy_preview_service()
    request_validator = RecipeRequestValidator()
    explain_payload_builder = ExplainPayloadBuilder()

    return RecipeGenerationService(
        ingredient_repository=ingredient_repository,
        ingredient_nutrients_repository=ingredient_nutrients_repository,
        preset_recipe_repository=preset_recipe_repository,
        recipe_spec_mapper=recipe_spec_mapper,
        preset_scaler=preset_scaler,
        nutrient_analysis_service=nutrient_analysis_service,
        nutrient_analysis_input_preparation_service=nutrient_analysis_input_preparation_service,
        beginner_diy_preview_service=beginner_diy_preview_service,
        l2_engine=None,
        request_validator=request_validator,
        explain_payload_builder=explain_payload_builder,
    )


def get_recipe_request_router(request: Request) -> RequestRouter:
    return RequestRouter(
        execution_planner=get_execution_planner(),
        recipe_generation_service=get_recipe_generation_service(request),
    )