from __future__ import annotations

'''
只做 mode 路由和输入合法性校验，不干业务计算
'''


import logging

from app.domains.recipe_generation.contracts.request import RecipeGenerationRequest
from app.domains.recipe_generation.contracts.results import RecipeGenerationResult
from app.domains.recipe_generation.orchestration.execution_planner import (
    ExecutionPlan,
    ExecutionPlanner,
)
from app.domains.recipe_generation.orchestration.generate_recipe_service import (
    RecipeGenerationService,
)

logger = logging.getLogger(__name__)


class RequestRouter:
    """
    Thin router for recipe-generation requests.

    Responsibility:
    - ask ExecutionPlanner for the execution plan
    - dispatch to the correct top-level service

    Non-responsibility:
    - no deep validation
    - no business logic
    - no DB access
    """

    def __init__(
        self,
        execution_planner: ExecutionPlanner,
        recipe_generation_service: RecipeGenerationService,
    ) -> None:
        self._execution_planner = execution_planner
        self._recipe_generation_service = recipe_generation_service

    async def route(
        self,
        request: RecipeGenerationRequest,
    ) -> RecipeGenerationResult:
        plan = self._execution_planner.plan(request)

        return await self._dispatch(plan=plan, request=request)

    async def _dispatch(
        self,
        plan: ExecutionPlan,
        request: RecipeGenerationRequest,
    ) -> RecipeGenerationResult:
        if plan.target_service == "recipe_generation":
            return await self._recipe_generation_service.generate(request)

        raise NotImplementedError(
            f"Unsupported target_service in execution plan: {plan.target_service}"
        )