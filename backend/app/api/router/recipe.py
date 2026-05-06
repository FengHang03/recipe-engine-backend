from fastapi import APIRouter, Depends

from app.domains.recipe_generation.contracts.request import RecipeGenerationRequest
from app.domains.recipe_generation.contracts.results import RecipeGenerationResult
from app.domains.recipe_generation.orchestration.request_router import (
    RequestRouter,
)
from app.api.dependencies.recipe import get_recipe_request_router

router = APIRouter(prefix="/recipe-generation", tags=["recipe_generation"])


@router.post("/generate", response_model=RecipeGenerationResult)
async def generate_recipe(
    request: RecipeGenerationRequest,
    request_router: RequestRouter = Depends(get_recipe_request_router),
) -> RecipeGenerationResult:
    """
    Unified recipe generation endpoint.

    Supported paths are routed internally by RequestRouter / ExecutionPlanner,
    for example:
    - SCALE_PRESET
    - OPTIMIZE_FIXED_SET
    - BEGINNER_DIY_PREVIEW
    """
    return await request_router.route(request)
    