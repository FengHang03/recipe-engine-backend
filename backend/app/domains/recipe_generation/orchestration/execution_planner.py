from __future__ import annotations

"""
职责：
把 request 翻译成“本次执行计划”。

这是 orchestration 层非常值钱的一个文件。

它做什么

根据：

- request.mode
- constraints
- supplement_toolkit_ids
- spec 类型

决定：

    需要加载哪些数据
    要走哪个 engine
    是否需要 constraint bundle
    是否需要 supplement hydration
    是否需要 post-analysis / explain payload
输出

我建议它输出一个轻量 plan 对象，比如：

    engine_type
    needs_nutrition_bundle
    needs_constraint_bundle
    needs_supplements
    result_postprocessors
为什么需要它

这样 generate_recipe_service.py 不会变成大 if/else 文件。
"""

from dataclasses import dataclass

from app.domains.recipe_generation.contracts.enums import RecipeGenerationMode
from app.domains.recipe_generation.contracts.request import RecipeGenerationRequest


@dataclass(frozen=True)
class ExecutionPlan:
    """
    Minimal execution plan for request routing.

    Fields:
    - target_service: which top-level service should handle the request
    - operation: stable operation key for logging/debugging/future branching
    """
    target_service: str
    operation: str


class ExecutionPlanner:
    """
    Thin planner for recipe-generation requests.

    Responsibility:
    - decide which top-level service should handle the request
    - provide a stable operation key

    Non-responsibility:
    - no deep validation
    - no DB access
    - no business execution
    """

    def plan(self, request: RecipeGenerationRequest) -> ExecutionPlan:
        mode = request.mode

        if mode == RecipeGenerationMode.SCALE_PRESET:
            return ExecutionPlan(
                target_service="recipe_generation",
                operation="scale_preset",
            )

        if mode == RecipeGenerationMode.OPTIMIZE_FIXED_SET:
            return ExecutionPlan(
                target_service="recipe_generation",
                operation="optimize_fixed_set",
            )

        if mode == RecipeGenerationMode.BEGINNER_DIY_PREVIEW:
            return ExecutionPlan(
                target_service="recipe_generation",
                operation="beginner_diy_preview",
            )

        if mode == RecipeGenerationMode.OPTIMIZE_USER_DEFINED:
            return ExecutionPlan(
                target_service="recipe_generation",
                operation="optimize_user_defined",
            )

        if mode == RecipeGenerationMode.PRESET_WITH_TOLERANCE:
            return ExecutionPlan(
                target_service="recipe_generation",
                operation="preset_with_tolerance",
            )

        raise NotImplementedError(f"Unsupported recipe generation mode: {mode!r}")