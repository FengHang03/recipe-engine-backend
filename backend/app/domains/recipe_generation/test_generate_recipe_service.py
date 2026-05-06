from __future__ import annotations

import asyncio
import logging
import sys
from pprint import pprint
from pathlib import Path

# ---------------------------------------------------------------------
# 1. 项目路径
# ---------------------------------------------------------------------
BACKEND_DIR = Path(r"D:/Programs/Pet-Recipe-251204/backend")
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

# ---------------------------------------------------------------------
# 2. 导入项目对象
# ---------------------------------------------------------------------
from app.db.connection import create_db_engine

from app.shared.contracts.enums import (
    Species,
    LifeStage,
    SizeClass,
    ActivityLevel,
    SterilizationStatus,
    ReproductiveStage,
)
from app.shared.contracts.pet import PetProfile

from app.domains.recipe_generation.contracts.enums import RecipeGenerationMode
from app.domains.recipe_generation.contracts.request import RecipeGenerationRequest
from app.domains.recipe_generation.contracts.recipe_spec import PresetRecipeRef
from app.domains.recipe_generation.orchestration.validators.request_validator import (
    RecipeRequestValidator,
)
from app.domains.recipe_generation.orchestration.generate_recipe_service import (
    RecipeGenerationService,
)
from app.domains.recipe_generation.infra.repositories.preset_recipe_repository import (
    PresetRecipeRepository,
)
from app.domains.recipe_generation.infra.repositories.ingredient_repository import (
    IngredientRepository,
)
from app.domains.recipe_generation.infra.mappers.recipe_spec_mapper import (
    RecipeSpecMapper,
)
from app.domains.recipe_generation.engines.scaling.preset_scaler import PresetScaler
from app.domains.nutrient_analysis.nutrient_analysis_service import (
    NutrientAnalysisService,
)

# ---------------------------------------------------------------------
# 3. 日志配置
# ---------------------------------------------------------------------
def setup_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    )


logger = logging.getLogger("generate_recipe_service_test")


# ---------------------------------------------------------------------
# 4. 打印辅助
# ---------------------------------------------------------------------
def print_section(title: str) -> None:
    line = "=" * 88
    print(f"\n{line}\n{title}\n{line}")


def print_subsection(title: str) -> None:
    line = "-" * 88
    print(f"\n{title}\n{line}")


def print_request_summary(request: RecipeGenerationRequest) -> None:
    print_subsection("Request Summary")
    print(f"mode                   = {request.mode}")
    print(f"recipe_id              = {request.preset_recipe_spec.recipe_id}")
    print(f"species                = {request.pet_profile.species}")
    print(f"life_stage             = {request.pet_profile.life_stage}")
    print(f"weight_kg              = {request.pet_profile.weight_kg}")
    print(f"daily_calories_kcal    = {request.pet_profile.daily_calories_kcal}")
    print(f"request_id             = {request.request_id}")
    print(f"requested_by           = {request.requested_by}")


def print_resolved_recipe_choice(service, request: RecipeGenerationRequest) -> None:
    print_subsection("Preset Recipe Routing")
    base_recipe_id = request.preset_recipe_spec.recipe_id

    if hasattr(service, "_resolve_preset_recipe_id_for_pet"):
        final_recipe_id = service._resolve_preset_recipe_id_for_pet(
            base_recipe_id=base_recipe_id,
            request=request,
        )
    else:
        final_recipe_id = base_recipe_id

    print(f"base_recipe_id         = {base_recipe_id}")
    print(f"life_stage             = {request.pet_profile.life_stage}")
    print(f"final_recipe_id        = {final_recipe_id}")


def print_result_summary(result) -> None:
    print_subsection("RecipeGenerationResult Summary")
    print(f"mode                   = {getattr(result, 'mode', None)}")
    print(f"status                 = {getattr(result, 'status', None)}")
    print(f"recipe_id              = {getattr(result, 'recipe_id', None)}")
    print(f"total_weight_grams     = {getattr(result, 'total_weight_grams', None)}")
    print(f"weights_count          = {len(getattr(result, 'weights', []) or [])}")
    print(f"nutrient_count         = {len(getattr(result, 'nutrient_analysis', []) or [])}")
    print(f"warnings               = {getattr(result, 'warnings', None)}")
    print(f"used_supplements_count = {len(getattr(result, 'used_supplements', []) or [])}")
    print(f"solve_time_seconds     = {getattr(result, 'solve_time_seconds', None)}")


def print_weights_preview(result, limit: int = 12) -> None:
    print_subsection(f"Result Weights Preview (first {limit})")
    weights = getattr(result, "weights", []) or []
    for idx, w in enumerate(weights[:limit], start=1):
        print(
            f"[{idx:02d}] "
            f"name={str(getattr(w, 'ingredient_name', None)):<30} "
            f"weight_g={str(getattr(w, 'weight_grams', None)):<10} "
            f"pct={str(getattr(w, 'pct_of_recipe', None)):<8} "
            f"is_supplement={str(getattr(w, 'is_supplement', None))}"
        )


def print_nutrient_preview(result, limit: int = 12) -> None:
    print_subsection(f"Nutrient Analysis Preview (first {limit})")
    nutrient_rows = getattr(result, "nutrient_analysis", []) or []
    if not nutrient_rows:
        print("No nutrient analysis rows returned.")
        return

    for idx, row in enumerate(nutrient_rows[:limit], start=1):
        nutrient_name = getattr(row, "name", None) or getattr(row, "nutrient_name", None)
        value = getattr(row, "value", None)
        unit = getattr(row, "unit", None)
        min_value = getattr(row, "min_value", None)
        max_value = getattr(row, "max_value", None)
        meets_min = getattr(row, "meets_min", None)
        meets_max = getattr(row, "meets_max", None)

        print(
            f"[{idx:02d}] "
            f"name={str(nutrient_name):<28} "
            f"value={str(value):<12} "
            f"unit={str(unit):<8} "
            f"min={str(min_value):<10} "
            f"max={str(max_value):<10} "
            f"meets_min={str(meets_min):<8} "
            f"meets_max={str(meets_max):<8}"
        )


def print_key_nutrients(result) -> None:
    print_subsection("Key Nutrients")

    nutrient_rows = getattr(result, "nutrient_analysis", []) or []
    if not nutrient_rows:
        print("No nutrient analysis rows returned.")
        return

    def normalize_name(value) -> str:
        return str(value or "").strip().lower()

    def find_by_keywords(keywords: list[str]):
        keywords = [normalize_name(k) for k in keywords]
        for row in nutrient_rows:
            row_name = normalize_name(
                getattr(row, "name", None) or getattr(row, "nutrient_name", None)
            )
            if any(k in row_name for k in keywords):
                return row
        return None

    rules = [
        ("Protein", ["protein"]),
        ("Fat", ["fat", "total lipid"]),
        ("Calcium", ["calcium"]),
        ("Phosphorus", ["phosphorus"]),
        ("Ca:P Ratio", ["ca:p", "ca/p", "calcium phosphorus ratio", "calcium/phosphorus ratio"]),
        ("Omega-6:Omega-3", ["omega-6:omega-3", "omega 6:omega 3", "n6:n3"]),
        ("EPA + DHA", ["epa + dha", "epa+dah", "epa dha", "dha"]),
        ("Iron", ["iron"]),
        ("Zinc", ["zinc"]),
        ("Vitamin D", ["vitamin d"]),
        ("Vitamin E", ["vitamin e"]),
        ("Iodine", ["iodine"]),
    ]

    for label, keywords in rules:
        row = find_by_keywords(keywords)
        if row is None:
            print(f"{label:<18} : NOT FOUND")
            continue

        nutrient_name = getattr(row, "name", None) or getattr(row, "nutrient_name", None)
        value = getattr(row, "value", None)
        unit = getattr(row, "unit", None)
        print(
            f"{label:<18} : "
            f"value={str(value):<12} "
            f"unit={str(unit):<8} "
            f"name={str(nutrient_name)}"
        )


def print_debug_meta(result) -> None:
    print_subsection("Debug Meta")
    pprint(getattr(result, "debug_meta", None))


# ---------------------------------------------------------------------
# 5. 主流程
# ---------------------------------------------------------------------
async def main() -> None:
    setup_logging()

    connection_string = "postgresql://postgres:Tuantuan_123@127.0.0.1:15432/tuanty_recipe"

    print_section("STEP 0 | Build request")

    pet_profile = PetProfile(
        species=Species.DOG,
        age_months=12,
        weight_kg=22.0,
        life_stage=LifeStage.DOG_ADULT,
        size_class=SizeClass.MEDIUM,
        activity_level=ActivityLevel.MODERATE,
        daily_calories_kcal=900.0,
        sterilization_status=SterilizationStatus.INTACT,
        reproductive_stage=ReproductiveStage.NONE,
        health_conditions=[],
        allergies=[],
    )

    request = RecipeGenerationRequest(
        mode=RecipeGenerationMode.SCALE_PRESET,
        pet_profile=pet_profile,
        preset_recipe_spec=PresetRecipeRef(
            recipe_id="preset_recipe_beef_001"
        ),
        request_id="generate-service-test-001",
        requested_by="local_script_test",
    )

    logger.info("Request built successfully.")
    print_request_summary(request)

    print_section("STEP 1 | Build dependencies")

    engine = create_db_engine(connection_string)

    ingredient_repository = IngredientRepository(engine=engine)
    preset_recipe_repository = PresetRecipeRepository()
    recipe_spec_mapper = RecipeSpecMapper()
    preset_scaler = PresetScaler()
    nutrient_analysis_service = NutrientAnalysisService()
    request_validator = RecipeRequestValidator()

    service = RecipeGenerationService(
        ingredient_repository=ingredient_repository,
        preset_recipe_repository=preset_recipe_repository,
        recipe_spec_mapper=recipe_spec_mapper,
        preset_scaler=preset_scaler,
        nutrient_analysis_service=nutrient_analysis_service,
        l2_engine=None,
        request_validator=request_validator,
        explain_payload_builder=None,
    )

    logger.info("All dependencies initialized.")
    print("Dependencies initialized successfully.")

    print_section("STEP 2 | Validate request")
    request_validator.validate(request)
    logger.info("Request validation passed.")
    print("Request validation: PASSED")

    print_section("STEP 3 | Resolve preset recipe routing")
    print_resolved_recipe_choice(service, request)

    print_section("STEP 4 | Run service.generate(request)")
    result = await service.generate(request)
    logger.info("service.generate(request) executed successfully.")
    print("service.generate(request): PASSED")

    print_section("STEP 5 | Inspect final result")
    print_result_summary(result)
    print_weights_preview(result)
    print_nutrient_preview(result)
    print_key_nutrients(result)
    print_debug_meta(result)

    print_section("STEP 6 | Success summary")
    print("generate_recipe_service.py full flow test completed successfully.")
    print("Verified chain:")
    print("  RecipeGenerationRequest")
    print("    -> request validation")
    print("    -> preset recipe routing")
    print("    -> service.generate(request)")
    print("    -> resolved preset flow")
    print("    -> display weights")
    print("    -> analysis inputs")
    print("    -> nutrient analysis")
    print("    -> RecipeGenerationResult")

    logger.info("generate_recipe_service full flow test finished.")


if __name__ == "__main__":
    asyncio.run(main())