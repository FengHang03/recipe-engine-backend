from __future__ import annotations

from typing import Iterable, List, Optional

from app.domains.recipe_generation.contracts.enums import RecipeGenerationMode
from app.domains.recipe_generation.contracts.request import RecipeGenerationRequest


class RecipeRequestValidationError(ValueError):
    """Raised when RecipeGenerationRequest is invalid."""


class RecipeRequestValidator:
    """
    Validate RecipeGenerationRequest before orchestration dispatch.

    Responsibility:
    1. Enforce mode-specific required payloads
    2. Enforce mutually exclusive recipe specs
    3. Validate basic pet profile and request-level fields
    4. Validate minimal preset / fixed-set / user-defined shape

    Notes:
    - No DB access
    - No heavy business logic
    - No engine-specific optimization rules
    """

    def validate(self, request: RecipeGenerationRequest) -> None:
        self._validate_request_basics(request)
        self._validate_spec_exclusivity(request)
        self._validate_mode_specific_payload(request)
        self._validate_supplement_toolkit_ids(request)

    # ------------------------------------------------------------------
    # Request-level validation
    # ------------------------------------------------------------------

    def _validate_request_basics(self, request: RecipeGenerationRequest) -> None:
        if request.mode is None:
            raise RecipeRequestValidationError("request.mode is required.")

        if request.pet_profile is None:
            raise RecipeRequestValidationError("request.pet_profile is required.")

        if request.pet_profile.daily_calories_kcal is None:
            raise RecipeRequestValidationError(
                "request.pet_profile.daily_calories_kcal is required."
            )

        if float(request.pet_profile.daily_calories_kcal) <= 0:
            raise RecipeRequestValidationError(
                "request.pet_profile.daily_calories_kcal must be > 0."
            )

        if request.pet_profile.weight_kg is None:
            raise RecipeRequestValidationError("request.pet_profile.weight_kg is required.")

        if float(request.pet_profile.weight_kg) <= 0:
            raise RecipeRequestValidationError(
                "request.pet_profile.weight_kg must be > 0."
            )

        if request.pet_profile.life_stage is None:
            raise RecipeRequestValidationError(
                "request.pet_profile.life_stage is required."
            )

    def _validate_spec_exclusivity(self, request: RecipeGenerationRequest) -> None:
        provided_specs = [
            ("combination_spec", request.combination_spec),
            ("user_defined_spec", request.user_defined_spec),
            ("preset_recipe_spec", request.preset_recipe_spec),
            ("beginner_diy_spec", getattr(request, "beginner_diy_spec", None)),
        ]
        provided = [name for name, value in provided_specs if value is not None]

        if len(provided) == 0:
            raise RecipeRequestValidationError(
                "Exactly one recipe spec is required: "
                "combination_spec, user_defined_spec, preset_recipe_spec, or beginner_diy_spec."
            )

        if len(provided) > 1:
            raise RecipeRequestValidationError(
                "Only one recipe spec may be provided. "
                f"Received multiple: {', '.join(provided)}."
            )

    # ------------------------------------------------------------------
    # Mode-specific validation
    # ------------------------------------------------------------------

    def _validate_mode_specific_payload(self, request: RecipeGenerationRequest) -> None:
        if request.mode == RecipeGenerationMode.OPTIMIZE_FIXED_SET:
            self._validate_fixed_set_request(request)
            return

        if request.mode == RecipeGenerationMode.OPTIMIZE_USER_DEFINED:
            self._validate_user_defined_request(request)
            return

        if request.mode == RecipeGenerationMode.SCALE_PRESET:
            self._validate_scale_preset_request(request)
            return

        if request.mode == RecipeGenerationMode.BEGINNER_DIY_PREVIEW:
            self._validate_beginner_diy_preview_request(request)
            return

        if request.mode == RecipeGenerationMode.PRESET_WITH_TOLERANCE:
            self._validate_preset_with_tolerance_request(request)
            return

        raise RecipeRequestValidationError(
            f"Unsupported RecipeGenerationMode: {request.mode}"
        )

    def _validate_fixed_set_request(self, request: RecipeGenerationRequest) -> None:
        if request.combination_spec is None:
            raise RecipeRequestValidationError(
                "OPTIMIZE_FIXED_SET requires request.combination_spec."
            )

        if request.user_defined_spec is not None or request.preset_recipe_spec is not None:
            raise RecipeRequestValidationError(
                "OPTIMIZE_FIXED_SET only accepts combination_spec."
            )

        if not request.combination_spec.recipe_id:
            raise RecipeRequestValidationError(
                "combination_spec.recipe_id is required."
            )

        ingredients_by_slot = getattr(request.combination_spec, "ingredients_by_slot", None)
        if ingredients_by_slot is None:
            ingredients_by_slot = getattr(request.combination_spec, "ingredients", None)

        if not ingredients_by_slot:
            raise RecipeRequestValidationError(
                "combination_spec must contain at least one slot with ingredients."
            )

        ingredient_count = 0
        for _, items in ingredients_by_slot.items():
            if items:
                ingredient_count += len(items)

        if ingredient_count == 0:
            raise RecipeRequestValidationError(
                "combination_spec contains no ingredients."
            )

    def _validate_user_defined_request(self, request: RecipeGenerationRequest) -> None:
        if request.user_defined_spec is None:
            raise RecipeRequestValidationError(
                "OPTIMIZE_USER_DEFINED requires request.user_defined_spec."
            )

        if request.combination_spec is not None or request.preset_recipe_spec is not None:
            raise RecipeRequestValidationError(
                "OPTIMIZE_USER_DEFINED only accepts user_defined_spec."
            )

        if not request.user_defined_spec.recipe_id:
            raise RecipeRequestValidationError(
                "user_defined_spec.recipe_id is required."
            )

        selected_items = getattr(request.user_defined_spec, "selected_items", None)
        if selected_items is None:
            selected_items = getattr(request.user_defined_spec, "ingredients", None)

        if not selected_items:
            raise RecipeRequestValidationError(
                "user_defined_spec must contain at least one selected ingredient."
            )

        for idx, item in enumerate(selected_items):
            if getattr(item, "ingredient", None) is None:
                raise RecipeRequestValidationError(
                    f"user_defined_spec.selected_items[{idx}].ingredient is required."
                )

            ingredient_id = getattr(item.ingredient, "ingredient_id", None)
            if not ingredient_id:
                raise RecipeRequestValidationError(
                    f"user_defined_spec.selected_items[{idx}].ingredient.ingredient_id is required."
                )

            min_weight_g = getattr(item, "min_weight_g", None)
            max_weight_g = getattr(item, "max_weight_g", None)

            if min_weight_g is not None and float(min_weight_g) < 0:
                raise RecipeRequestValidationError(
                    f"user_defined_spec.selected_items[{idx}].min_weight_g must be >= 0."
                )

            if max_weight_g is not None and float(max_weight_g) < 0:
                raise RecipeRequestValidationError(
                    f"user_defined_spec.selected_items[{idx}].max_weight_g must be >= 0."
                )

            if (
                min_weight_g is not None
                and max_weight_g is not None
                and float(min_weight_g) > float(max_weight_g)
            ):
                raise RecipeRequestValidationError(
                    f"user_defined_spec.selected_items[{idx}] has min_weight_g > max_weight_g."
                )

            target_ratio = getattr(item, "target_ratio", None)
            if target_ratio is not None and float(target_ratio) < 0:
                raise RecipeRequestValidationError(
                    f"user_defined_spec.selected_items[{idx}].target_ratio must be >= 0."
                )


    def _validate_scale_preset_request(self, request: RecipeGenerationRequest) -> None:
        if request.preset_recipe_spec is None:
            raise RecipeRequestValidationError(
                "SCALE_PRESET requires request.preset_recipe_spec."
            )

        if request.combination_spec is not None or request.user_defined_spec is not None:
            raise RecipeRequestValidationError(
                "SCALE_PRESET only accepts preset_recipe_spec."
            )

        if not getattr(request.preset_recipe_spec, "recipe_id", None):
            raise RecipeRequestValidationError(
                "preset_recipe_spec.recipe_id is required."
            )

    def _validate_beginner_diy_preview_request(self, request: RecipeGenerationRequest) -> None:
        beginner_diy_spec = getattr(request, "beginner_diy_spec", None)

        if beginner_diy_spec is None:
            raise RecipeRequestValidationError(
                "BEGINNER_DIY_PREVIEW requires request.beginner_diy_spec."
            )

        if (
            request.combination_spec is not None
            or request.user_defined_spec is not None
            or request.preset_recipe_spec is not None
        ):
            raise RecipeRequestValidationError(
                "BEGINNER_DIY_PREVIEW only accepts beginner_diy_spec."
            )

        if not getattr(beginner_diy_spec, "recipe_id", None):
            raise RecipeRequestValidationError(
                "beginner_diy_spec.recipe_id is required."
            )

    def _validate_preset_with_tolerance_request(
        self,
        request: RecipeGenerationRequest,
    ) -> None:
        # Reuse scale preset structural validation for now
        self._validate_scale_preset_request(request)

    # ------------------------------------------------------------------
    # Supplement toolkit validation
    # ------------------------------------------------------------------

    def _validate_supplement_toolkit_ids(self, request: RecipeGenerationRequest) -> None:
        toolkit_ids = getattr(request, "supplement_toolkit_ids", None)
        if toolkit_ids is None:
            return

        if not isinstance(toolkit_ids, list):
            raise RecipeRequestValidationError(
                "request.supplement_toolkit_ids must be a list of strings."
            )

        for idx, item in enumerate(toolkit_ids):
            if not isinstance(item, str):
                raise RecipeRequestValidationError(
                    f"request.supplement_toolkit_ids[{idx}] must be a string."
                )
            if not item.strip():
                raise RecipeRequestValidationError(
                    f"request.supplement_toolkit_ids[{idx}] must not be empty."
                )