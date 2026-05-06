from __future__ import annotations

from typing import Any, Dict, List, Protocol

from app.shared.contracts.ingredient import IngredientProfile
from app.shared.contracts.pet import PetProfile
from app.shared.contracts.nutrition import NutrientAnalysis
from app.domains.recipe_generation.contracts.enums import RecipeGenerationMode, SolveStatus
from app.domains.recipe_generation.contracts.recipe_spec import RecipeCombinationSpec
from app.domains.recipe_generation.contracts.results import RecipeGenerationResult, WeightedIngredient


class LegacyL2Solver(Protocol):
    """Adapter protocol for your existing L2 optimizer implementation."""

    def optimize_fixed_set(
        self,
        pet_profile: PetProfile,
        combination_spec: RecipeCombinationSpec,
        supplement_toolkit: List[IngredientProfile],
    ) -> Dict[str, Any]:
        ...


class L2Engine:
    """Thin engine façade over the existing L2 optimizer.

    Step 2 goal: do not rewrite your L2 internals yet. Wrap them behind one
    consistent entry point and normalize the return shape.
    """

    def __init__(self, solver: LegacyL2Solver) -> None:
        self._solver = solver

    def optimize_fixed_set(
        self,
        pet_profile: PetProfile,
        combination_spec: RecipeCombinationSpec,
        supplement_toolkit: List[IngredientProfile],
    ) -> RecipeGenerationResult:
        raw = self._solver.optimize_fixed_set(
            pet_profile=pet_profile,
            combination_spec=combination_spec,
            supplement_toolkit=supplement_toolkit,
        )
        return self._normalize_result(raw, RecipeGenerationMode.OPTIMIZE_FIXED_SET)

    def _normalize_result(
        self,
        raw: Dict[str, Any],
        mode: RecipeGenerationMode,
    ) -> RecipeGenerationResult:
        weights = [
            self._normalize_weight(item)
            for item in raw.get("weights", [])
        ]
        nutrient_analysis = [
            item if isinstance(item, NutrientAnalysis) else NutrientAnalysis.model_validate(item)
            for item in raw.get("nutrient_analysis", [])
        ]

        status = raw.get("status", SolveStatus.ERROR)
        if isinstance(status, str):
            status = SolveStatus(status)

        return RecipeGenerationResult(
            mode=mode,
            status=status,
            source_recipe_id=raw.get("source_recipe_id"),
            recipe_id=raw.get("recipe_id"),
            source_type=raw.get("source_type"),
            rank=raw.get("rank"),
            solve_time_seconds=raw.get("solve_time_seconds"),
            total_weight_grams=raw.get("total_weight_grams"),
            weights=weights,
            nutrient_analysis=nutrient_analysis,
            objective_value=raw.get("objective_value"),
            penalty_breakdown=raw.get("penalty_breakdown"),
            infeasibility_diagnostic=raw.get("infeasibility_diagnostic"),
            used_supplements=list(raw.get("used_supplements", []) or []),
            warnings=list(raw.get("warnings", []) or []),
            explanation_payload=raw.get("explanation_payload"),
            debug_meta=dict(raw.get("debug_meta", {}) or {}),
        )

    def _normalize_weight(self, raw: Any) -> WeightedIngredient:
        if isinstance(raw, WeightedIngredient):
            return raw
        return WeightedIngredient.model_validate(raw)
