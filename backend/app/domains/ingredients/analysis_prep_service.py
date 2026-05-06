from __future__ import annotations

from enum import Enum
from typing import Dict, Iterable, List, Optional, Sequence

from pydantic import BaseModel, Field

from app.shared.contracts.enums import FoodGroup
from app.shared.contracts.ingredient import IngredientProfile, PrepState
from app.domains.nutrient_analysis.contracts import (
    AnalysisIngredientItem,
)


class AnalysisPrepPolicy(BaseModel):
    """
    Rule policy for choosing analysis prep state.

    Recommended v1 defaults:
    - Supplements -> AS_IS
    - Oils/Fats -> AS_IS
    - Everything else -> COOKED
    - If conversion is not possible, fall back to AS_IS
    """
    default_analysis_state: PrepState = PrepState.COOKED

    as_is_food_groups: List[FoodGroup] = Field(
        default_factory=lambda: [
            FoodGroup.SUPPLEMENT,
            FoodGroup.FAT_OIL,
        ]
    )

    # If the ingredient itself is already in one of these states,
    # and target analysis state matches, no conversion is needed.
    recognized_prep_states: List[str] = Field(
        default_factory=lambda: ["raw", "cooked", "supplement", "as_is"]
    )


class AnalysisPrepResult(BaseModel):
    """
    Rich conversion result for debugging / explain / traceability.
    """
    source_ingredient_id: str
    source_prep_state: Optional[str] = None
    source_weight_g: float = Field(ge=0)

    analysis_ingredient_id: str
    analysis_prep_state: PrepState
    analysis_weight_g: float = Field(ge=0)

    was_converted: bool = False

    used_yield_factor: Optional[float] = None
    used_raw_equivalent_fdc_id: Optional[str] = None
    matched_target_by_fdc_id: bool = False

    reason: str = ""


class AnalysisPrepService:
    """
    Resolve ingredient analysis basis and convert source weights accordingly.

    Core principle:
    - UI / recipe-generation may work with display/formulation weights
    - nutrient analysis consumes standardized analysis items
    - nutrient analysis itself should not care about raw/cooked logic

    Assumptions for yield_factor:
        raw_weight * yield_factor = cooked_weight
    Therefore:
        cooked_weight / yield_factor = raw_weight
    """

    def __init__(self, policy: Optional[AnalysisPrepPolicy] = None):
        self.policy = policy or AnalysisPrepPolicy()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def convert_item(
        self,
        ingredient_id: str,
        source_weight_g: float,
        ingredient_profiles: Dict[str, IngredientProfile],
    ) -> AnalysisPrepResult:
        """
        Convert one ingredient amount into nutrient-analysis basis.
        """
        if source_weight_g < 0:
            raise ValueError(f"source_weight_g must be >= 0, got {source_weight_g}")

        source_profile = ingredient_profiles.get(ingredient_id)
        if source_profile is None:
            raise KeyError(f"missing IngredientProfile for ingredient_id='{ingredient_id}'")

        source_prep_state = self._normalize_prep_state(source_profile.prep_state)
        target_state = self.resolve_analysis_prep_state(source_profile)

        # 1) AS_IS directly
        if target_state == PrepState.AS_IS:
            return self._build_as_is_result(
                source_profile=source_profile,
                source_weight_g=source_weight_g,
                reason="analysis policy resolved to AS_IS",
            )

        # 2) RAW target
        if target_state == PrepState.RAW:
            return self._convert_to_raw(
                source_profile=source_profile,
                source_weight_g=source_weight_g,
                source_prep_state=source_prep_state,
                ingredient_profiles=ingredient_profiles,
            )

        # 3) COOKED target
        if target_state == PrepState.COOKED:
            return self._convert_to_cooked(
                source_profile=source_profile,
                source_weight_g=source_weight_g,
                source_prep_state=source_prep_state,
                ingredient_profiles=ingredient_profiles,
            )

        return self._build_as_is_result(
            source_profile=source_profile,
            source_weight_g=source_weight_g,
            reason="unexpected analysis state; fell back to AS_IS",
        )

    def convert_items(
        self,
        items: Sequence[AnalysisIngredientItem],
        ingredient_profiles: Dict[str, IngredientProfile],
    ) -> List[AnalysisPrepResult]:
        """
        Convert multiple items in order.
        """
        return [
            self.convert_item(
                ingredient_id=item.ingredient_id,
                source_weight_g=item.weight_g,
                ingredient_profiles=ingredient_profiles,
            )
            for item in items
        ]

    def to_analysis_items(
        self,
        converted_items: Iterable[AnalysisPrepResult],
    ) -> List[AnalysisIngredientItem]:
        """
        Collapse converted results into aggregated analysis items.

        If multiple source items map to the same analysis ingredient, aggregate by weight.
        """
        aggregated: Dict[str, float] = {}

        for item in converted_items:
            aggregated[item.analysis_ingredient_id] = (
                aggregated.get(item.analysis_ingredient_id, 0.0)
                + float(item.analysis_weight_g)
            )

        return [
            AnalysisIngredientItem(
                ingredient_id=ingredient_id,
                weight_g=round(weight_g, 6),
            )
            for ingredient_id, weight_g in aggregated.items()
        ]

    def resolve_analysis_prep_state(
        self,
        ingredient: IngredientProfile,
    ) -> PrepState:
        """
        Decide which prep state should be used for nutrient analysis.

        v1 policy:
        - SUPPLEMENT / FAT_OIL -> AS_IS
        - otherwise -> COOKED
        """
        if ingredient.food_group in self.policy.as_is_food_groups:
            return PrepState.AS_IS

        return self.policy.default_analysis_state

    # ------------------------------------------------------------------
    # Conversion implementations
    # ------------------------------------------------------------------

    def _convert_to_raw(
        self,
        source_profile: IngredientProfile,
        source_weight_g: float,
        source_prep_state: Optional[str],
        ingredient_profiles: Dict[str, IngredientProfile],
    ) -> AnalysisPrepResult:
        """
        Convert current ingredient/weight into raw-equivalent basis.
        """
        # Already raw
        if source_prep_state == "raw":
            return AnalysisPrepResult(
                source_ingredient_id=source_profile.ingredient_id,
                source_prep_state=source_prep_state,
                source_weight_g=round(float(source_weight_g), 6),
                analysis_ingredient_id=source_profile.ingredient_id,
                analysis_prep_state=PrepState.RAW,
                analysis_weight_g=round(float(source_weight_g), 6),
                was_converted=False,
                used_yield_factor=None,
                used_raw_equivalent_fdc_id=source_profile.raw_equivalent_fdc_id,
                matched_target_by_fdc_id=False,
                reason="source ingredient already in RAW state",
            )

        # Need raw-equivalent mapping + yield
        raw_profile = self._resolve_raw_equivalent_profile(
            source_profile=source_profile,
            ingredient_profiles=ingredient_profiles,
        )
        if raw_profile is None:
            return self._build_as_is_result(
                source_profile=source_profile,
                source_weight_g=source_weight_g,
                reason="RAW analysis requested but no raw-equivalent profile found",
            )

        if source_profile.yield_factor is None or source_profile.yield_factor <= 0:
            return self._build_as_is_result(
                source_profile=source_profile,
                source_weight_g=source_weight_g,
                reason="RAW analysis requested but yield_factor is missing/invalid",
            )

        raw_weight_g = self._cooked_to_raw_weight(
            cooked_weight_g=source_weight_g,
            yield_factor=source_profile.yield_factor,
        )

        return AnalysisPrepResult(
            source_ingredient_id=source_profile.ingredient_id,
            source_prep_state=source_prep_state,
            source_weight_g=round(float(source_weight_g), 6),
            analysis_ingredient_id=raw_profile.ingredient_id,
            analysis_prep_state=PrepState.RAW,
            analysis_weight_g=round(float(raw_weight_g), 6),
            was_converted=True,
            used_yield_factor=source_profile.yield_factor,
            used_raw_equivalent_fdc_id=source_profile.raw_equivalent_fdc_id,
            matched_target_by_fdc_id=(raw_profile.ingredient_id != source_profile.ingredient_id),
            reason="converted source ingredient to RAW-equivalent basis",
        )

    def _convert_to_cooked(
        self,
        source_profile: IngredientProfile,
        source_weight_g: float,
        source_prep_state: Optional[str],
        ingredient_profiles: Dict[str, IngredientProfile],
    ) -> AnalysisPrepResult:
        """
        Convert current ingredient/weight into cooked basis.
        """
        # Already cooked
        if source_prep_state == "cooked":
            return AnalysisPrepResult(
                source_ingredient_id=source_profile.ingredient_id,
                source_prep_state=source_prep_state,
                source_weight_g=round(float(source_weight_g), 6),
                analysis_ingredient_id=source_profile.ingredient_id,
                analysis_prep_state=PrepState.COOKED,
                analysis_weight_g=round(float(source_weight_g), 6),
                was_converted=False,
                used_yield_factor=None,
                used_raw_equivalent_fdc_id=source_profile.raw_equivalent_fdc_id,
                matched_target_by_fdc_id=False,
                reason="source ingredient already in COOKED state",
            )

        # If source is raw, try to find cooked counterpart and convert weight
        if source_prep_state == "raw":
            cooked_profile = self._resolve_cooked_equivalent_profile(
                raw_profile=source_profile,
                ingredient_profiles=ingredient_profiles,
            )
            if cooked_profile is None:
                return self._build_as_is_result(
                    source_profile=source_profile,
                    source_weight_g=source_weight_g,
                    reason="COOKED analysis requested but no cooked-equivalent profile found",
                )

            if cooked_profile.yield_factor is None or cooked_profile.yield_factor <= 0:
                return self._build_as_is_result(
                    source_profile=source_profile,
                    source_weight_g=source_weight_g,
                    reason="COOKED analysis requested but cooked-equivalent yield_factor missing/invalid",
                )

            cooked_weight_g = self._raw_to_cooked_weight(
                raw_weight_g=source_weight_g,
                yield_factor=cooked_profile.yield_factor,
            )

            return AnalysisPrepResult(
                source_ingredient_id=source_profile.ingredient_id,
                source_prep_state=source_prep_state,
                source_weight_g=round(float(source_weight_g), 6),
                analysis_ingredient_id=cooked_profile.ingredient_id,
                analysis_prep_state=PrepState.COOKED,
                analysis_weight_g=round(float(cooked_weight_g), 6),
                was_converted=True,
                used_yield_factor=cooked_profile.yield_factor,
                used_raw_equivalent_fdc_id=cooked_profile.raw_equivalent_fdc_id,
                matched_target_by_fdc_id=True,
                reason="converted source ingredient to COOKED basis",
            )

        # as_is / supplement / unknown states -> fallback
        return self._build_as_is_result(
            source_profile=source_profile,
            source_weight_g=source_weight_g,
            reason="COOKED analysis requested but source prep_state is not convertible; using AS_IS",
        )

    # ------------------------------------------------------------------
    # Profile resolution
    # ------------------------------------------------------------------

    def _resolve_raw_equivalent_profile(
        self,
        source_profile: IngredientProfile,
        ingredient_profiles: Dict[str, IngredientProfile],
    ) -> Optional[IngredientProfile]:
        """
        raw_equivalent_fdc_id always points to the RAW ingredient's fdc_id.
        """
        target_fdc_id = source_profile.raw_equivalent_fdc_id
        if not target_fdc_id:
            return None

        for candidate in ingredient_profiles.values():
            if candidate.fdc_id == target_fdc_id and self._normalize_prep_state(candidate.prep_state) == "raw":
                return candidate

        # Accept same-id fallback if current ingredient is already the raw anchor
        for candidate in ingredient_profiles.values():
            if candidate.fdc_id == target_fdc_id:
                return candidate

        return None

    def _resolve_cooked_equivalent_profile(
        self,
        raw_profile: IngredientProfile,
        ingredient_profiles: Dict[str, IngredientProfile],
    ) -> Optional[IngredientProfile]:
        """
        Find a cooked profile whose raw_equivalent_fdc_id points back to the raw anchor FDC id.

        Preferred anchor:
        - raw_profile.raw_equivalent_fdc_id

        Fallback:
        - raw_profile.fdc_id
        """
        raw_anchor_fdc_id = raw_profile.raw_equivalent_fdc_id or raw_profile.fdc_id
        if not raw_anchor_fdc_id:
            return None

        raw_anchor_fdc_id = str(raw_anchor_fdc_id).strip()

        for candidate in ingredient_profiles.values():
            candidate_prep_state = self._normalize_prep_state(candidate.prep_state)
            candidate_raw_equivalent_fdc_id = getattr(candidate, "raw_equivalent_fdc_id", None)

            if (
                candidate_prep_state == "cooked"
                and candidate_raw_equivalent_fdc_id is not None
                and str(candidate_raw_equivalent_fdc_id).strip() == raw_anchor_fdc_id
            ):
                return candidate

        return None

    # ------------------------------------------------------------------
    # Weight conversion helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _raw_to_cooked_weight(
        raw_weight_g: float,
        yield_factor: Optional[float],
    ) -> float:
        """
        raw_weight * yield_factor = cooked_weight
        """
        if yield_factor is None or yield_factor <= 0:
            raise ValueError(f"yield_factor must be > 0, got {yield_factor}")
        return float(raw_weight_g) * float(yield_factor)

    @staticmethod
    def _cooked_to_raw_weight(
        cooked_weight_g: float,
        yield_factor: Optional[float],
    ) -> float:
        """
        raw_weight * yield_factor = cooked_weight
        => raw_weight = cooked_weight / yield_factor
        """
        if yield_factor is None or yield_factor <= 0:
            raise ValueError(f"yield_factor must be > 0, got {yield_factor}")
        return float(cooked_weight_g) / float(yield_factor)

    # ------------------------------------------------------------------
    # Internal utilities
    # ------------------------------------------------------------------

    def _build_as_is_result(
        self,
        source_profile: IngredientProfile,
        source_weight_g: float,
        reason: str,
    ) -> AnalysisPrepResult:
        source_prep_state = self._normalize_prep_state(source_profile.prep_state)



        return AnalysisPrepResult(
            source_ingredient_id=source_profile.ingredient_id,
            source_prep_state=source_prep_state,
            source_weight_g=round(float(source_weight_g), 6),
            analysis_ingredient_id=source_profile.ingredient_id,
            analysis_prep_state=PrepState.AS_IS,
            analysis_weight_g=round(float(source_weight_g), 6),
            was_converted=False,
            used_yield_factor=None,
            used_raw_equivalent_fdc_id=source_profile.raw_equivalent_fdc_id,
            matched_target_by_fdc_id=False,
            reason=reason,
        )

    @staticmethod
    def _normalize_prep_state(prep_state: Optional[object]) -> Optional[str]:
        if prep_state is None:
            return None

        if hasattr(prep_state, "value"):
            value = str(prep_state.value).strip().lower()
        else:
            value = str(prep_state).strip().lower()

        return value or None