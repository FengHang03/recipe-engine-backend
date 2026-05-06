from __future__ import annotations

import asyncio
import logging
import sys
from typing import List, Dict, Tuple, Sequence, Optional
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
from app.shared.contracts.ingredient import IngredientRef, IngredientProfile

from app.domains.recipe_generation.contracts.enums import SolveStatus, RecipeGenerationMode
from app.domains.recipe_generation.contracts.request import RecipeGenerationRequest
from app.domains.recipe_generation.contracts.recipe_spec import (
    PresetRecipeRef, PresetRecipeSpec
)
from app.domains.recipe_generation.contracts.results import WeightedIngredient, RecipeGenerationResult
from app.domains.recipe_generation.orchestration.validators.request_validator import (
    RecipeRequestValidator,
)
from app.domains.recipe_generation.orchestration.generate_recipe_service import (
    RecipeGenerationService,
)
from app.domains.recipe_generation.infra.repositories.preset_recipe_repository import (
    PresetRecipeRepository,
)
from app.domains.ingredients.infra.ingredient_repository import (
    IngredientRepository,
)
from app.domains.recipe_generation.infra.mappers.recipe_spec_mapper import (
    RecipeSpecMapper, RecipeSpecMappingError
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


logger = logging.getLogger("preset_resolution_test")


# ---------------------------------------------------------------------
# 4. 打印辅助
# ---------------------------------------------------------------------
def print_section(title: str) -> None:
    line = "=" * 88
    print(f"\n{line}\n{title}\n{line}")


def print_subsection(title: str) -> None:
    line = "-" * 88
    print(f"\n{title}\n{line}")


def print_resolved_items(preset) -> None:
    print_subsection("Resolved Preset Items")
    for idx, item in enumerate(preset.ingredients, start=1):
        print(
            f"[{idx:02d}] "
            f"name={item.ingredient.short_name or item.ingredient.description!s:<30} "
            f"slot={str(item.slot_type):<28} "
            f"resolved_weight_g={item.resolved_weight_g:<10} "
            f"resolved_unit={str(item.resolved_unit):<6} "
            f"mode={str(item.resolution_mode)}"
        )


def print_profiles_by_fdc(profiles_by_fdc_id: dict) -> None:
    print_subsection("Hydrated Ingredient Profiles (by fdc_id)")
    for fdc_id, profile in profiles_by_fdc_id.items():
        print(
            f"fdc_id={fdc_id:<10} "
            f"ingredient_id={profile.ingredient_id:<38} "
            f"short_name={str(profile.short_name):<28} "
            f"prep_state={str(getattr(profile, 'prep_state', None)):<12} "
            f"yield_factor={str(getattr(profile, 'yield_factor', None)):<8} "
            f"raw_equivalent_fdc_id={str(getattr(profile, 'raw_equivalent_fdc_id', None))}"
        )


def print_raw_preset_summary(raw_preset: dict) -> None:
    print_subsection("Raw Preset Summary")
    print(f"recipe_id              : {raw_preset.get('recipe_id')}")
    print(f"name                   : {raw_preset.get('name')}")
    print(f"display_basis          : {raw_preset.get('display_basis')}")
    print(f"analysis_basis         : {raw_preset.get('analysis_basis')}")
    print(f"weight_resolution_mode : {raw_preset.get('weight_resolution_mode')}")
    print(f"basis_kcal             : {raw_preset.get('basis_kcal')}")
    print(f"ingredient_count       : {len(raw_preset.get('ingredients', []))}")


def print_display_weights(display_weights) -> None:
    print_subsection("Display Weights")
    for idx, w in enumerate(display_weights, start=1):
        print(
            f"[{idx:02d}] "
            f"name={str(w.ingredient_name):<30} "
            f"ingredient_id={str(w.ingredient_id):<38} "
            f"weight_g={w.weight_grams:<10} "
            f"pct={str(w.pct_of_recipe):<8} "
            f"is_supplement={w.is_supplement}"
        )


def print_analysis_inputs(analysis_weights, analysis_profiles, analysis_debug) -> None:
    print_subsection("Analysis Weights")
    for idx, w in enumerate(analysis_weights, start=1):
        profile = analysis_profiles.get(str(w.ingredient_id))
        prep_state = getattr(profile, "prep_state", None) if profile else None
        print(
            f"[{idx:02d}] "
            f"name={str(w.ingredient_name):<30} "
            f"ingredient_id={str(w.ingredient_id):<38} "
            f"weight_g={w.weight_grams:<10} "
            f"prep_state={str(prep_state):<12}"
        )

    print_subsection("Analysis Debug")
    pprint(analysis_debug)


def print_nutrient_analysis(nutrient_analysis) -> None:
    print_subsection("Nutrient Analysis Summary")

    if not nutrient_analysis:
        print("No nutrient analysis rows returned.")
        return

    print(f"nutrient_count = {len(nutrient_analysis)}")

    # 先打印前 12 条，避免日志太长
    preview_count = min(12, len(nutrient_analysis))
    print_subsection(f"First {preview_count} Nutrients Preview")

    for idx, row in enumerate(nutrient_analysis[:preview_count], start=1):
        nutrient_name = getattr(row, "name", None) or getattr(row, "nutrient_name", None)
        value = getattr(row, "value", None)
        unit = getattr(row, "unit", None)
        min_value = getattr(row, "min_value", None)
        max_value = getattr(row, "max_value", None)
        meets_min = getattr(row, "meets_min", None)
        meets_max = getattr(row, "meets_max", None)

        print(
            f"[{idx:02d}] "
            f"name={str(nutrient_name):<24} "
            f"value={str(value):<12} "
            f"unit={str(unit):<8} "
            f"min={str(min_value):<10} "
            f"max={str(max_value):<10} "
            f"meets_min={str(meets_min):<8} "
            f"meets_max={str(meets_max):<8}"
        )


def print_recipe_generation_result(result) -> None:
    print_subsection("RecipeGenerationResult Summary")

    print(f"mode                : {getattr(result, 'mode', None)}")
    print(f"status              : {getattr(result, 'status', None)}")
    print(f"recipe_id           : {getattr(result, 'recipe_id', None)}")
    print(f"total_weight_grams  : {getattr(result, 'total_weight_grams', None)}")
    print(f"weights_count       : {len(getattr(result, 'weights', []) or [])}")
    print(f"nutrient_count      : {len(getattr(result, 'nutrient_analysis', []) or [])}")
    print(f"warnings            : {getattr(result, 'warnings', None)}")
    print(f"used_supplements    : {getattr(result, 'used_supplements', None)}")
    print(f"solve_time_seconds  : {getattr(result, 'solve_time_seconds', None)}")

    print_subsection("RecipeGenerationResult Weights Preview")
    for idx, w in enumerate((getattr(result, "weights", []) or [])[:12], start=1):
        print(
            f"[{idx:02d}] "
            f"name={str(getattr(w, 'ingredient_name', None)):<30} "
            f"weight_g={str(getattr(w, 'weight_grams', None)):<10} "
            f"pct={str(getattr(w, 'pct_of_recipe', None)):<8} "
            f"is_supplement={str(getattr(w, 'is_supplement', None))}"
        )

    debug_meta = getattr(result, "debug_meta", None)
    print_subsection("RecipeGenerationResult Debug Meta")
    pprint(debug_meta)

def print_key_nutrient_analysis(nutrient_analysis) -> None:
    """
    Print key nutrient rows from nutrient_analysis.

    Matching strategy:
    1. prefer nutrient_id if available
    2. fallback to nutrient name keyword matching
    """
    print_subsection("Key Nutrient Analysis")

    if not nutrient_analysis:
        print("No nutrient analysis rows returned.")
        return

    def normalize_name(value) -> str:
        return str(value or "").strip().lower()

    def pick_row(candidates):
        """
        candidates:
            list[dict] where each dict can contain:
            - nutrient_id
            - name_keywords: list[str]
        """
        for rule in candidates:
            target_id = rule.get("nutrient_id")
            keywords = [normalize_name(k) for k in rule.get("name_keywords", [])]

            for row in nutrient_analysis:
                row_id = getattr(row, "nutrient_id", None)
                row_name = normalize_name(
                    getattr(row, "name", None) or getattr(row, "nutrient_name", None)
                )

                if target_id is not None and row_id == target_id:
                    return row

                if keywords and any(k in row_name for k in keywords):
                    return row

        return None

    # 这里尽量兼容不同命名
    key_rules = [
        ("Protein", [
            {"name_keywords": ["protein"]},
        ]),
        ("Fat", [
            {"name_keywords": ["fat", "total lipid"]},
        ]),
        ("Calcium", [
            {"name_keywords": ["calcium"]},
        ]),
        ("Phosphorus", [
            {"name_keywords": ["phosphorus"]},
        ]),
        ("Ca:P Ratio", [
            {"name_keywords": ["ca:p", "ca/p", "calcium phosphorus ratio", "ca_p_ratio", "CA_P_RATIO"]},
        ]),
        ("Omega-6 : Omega-3", [
            {"name_keywords": ["omega-6:omega-3", "omega 6:omega 3", "n6:n3", "omega-6 omega-3 ratio"]},
        ]),
        ("EPA + DHA", [
            {"name_keywords": ["epa+dpa", "epa + dha", "epa dha", "epa+dah", "epa", "dha"]},
        ]),
        ("Iron", [
            {"name_keywords": ["iron"]},
        ]),
        ("Zinc", [
            {"name_keywords": ["zinc"]},
        ]),
        ("Vitamin D", [
            {"name_keywords": ["vitamin d"]},
        ]),
        ("Vitamin E", [
            {"name_keywords": ["vitamin e"]},
        ]),
        ("Iodine", [
            {"name_keywords": ["iodine"]},
        ]),
    ]

    found_any = False

    for display_name, candidates in key_rules:
        row = pick_row(candidates)
        if row is None:
            print(f"{display_name:<18} : NOT FOUND")
            continue

        found_any = True

        nutrient_name = getattr(row, "name", None) or getattr(row, "nutrient_name", None)
        value = getattr(row, "value", None)
        unit = getattr(row, "unit", None)
        min_value = getattr(row, "min_value", None)
        max_value = getattr(row, "max_value", None)
        meets_min = getattr(row, "meets_min", None)
        meets_max = getattr(row, "meets_max", None)

        print(
            f"{display_name:<18} : "
            f"value={str(value):<12} "
            f"unit={str(unit):<8} "
            f"min={str(min_value):<10} "
            f"max={str(max_value):<10} "
            f"meets_min={str(meets_min):<8} "
            f"meets_max={str(meets_max):<8} "
            f"name={str(nutrient_name)}"
        )

    if not found_any:
        print("No key nutrients were matched. Check nutrient names / IDs in analyzer output.")

# ---------------------------------------------------------------------
# 5. 测试主流程
# ---------------------------------------------------------------------
async def main() -> None:
    setup_logging()

    # 你自己的数据库连接字符串
    connection_string = "postgresql://postgres:Tuantuan_123@127.0.0.1:15432/tuanty_recipe"

    print_section("STEP 0 | Build request")

    pet_profile = PetProfile(
        species=Species.DOG,
        age_months=12,
        weight_kg=35.0,
        life_stage=LifeStage.DOG_PUPPY,
        size_class=SizeClass.MEDIUM,
        activity_level=ActivityLevel.MODERATE,
        daily_calories_kcal=1800.0,   # 这里先手动写一个测试值
        sterilization_status=SterilizationStatus.INTACT,
        reproductive_stage=ReproductiveStage.NONE,
        health_conditions=[],
        allergies=[],
    )

    request = RecipeGenerationRequest(
        mode=RecipeGenerationMode.SCALE_PRESET,
        pet_profile=pet_profile,
        preset_recipe_spec=PresetRecipeRef(
            recipe_id="preset_recipe_chicken_001_senior"
        ),
        request_id="preset-resolution-test-001",
        requested_by="local_script_test",
    )

    logger.info("Request built successfully.")
    print("Request summary:")
    print(f"  mode                   = {request.mode}")
    print(f"  recipe_id              = {request.preset_recipe_spec.recipe_id}")
    print(f"  pet.weight_kg          = {request.pet_profile.weight_kg}")
    print(f"  pet.daily_calories     = {request.pet_profile.daily_calories_kcal}")

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

    print_section("STEP 2 | Validate request")

    request_validator.validate(request)
    logger.info("Request validation passed.")
    print("Request validation: PASSED")

    print_section("STEP 3 | Load raw preset from repository")

    raw_preset = preset_recipe_repository.get_raw_preset(request.preset_recipe_spec.recipe_id)
    logger.info("Raw preset loaded successfully.")
    print_raw_preset_summary(raw_preset)

    print_subsection("First raw item preview")
    pprint(raw_preset["ingredients"][0])

    print_section("STEP 4 | Map raw preset dict -> RawPresetRecipeSpec")

    # 如果你已经按我们最新设计改成这个名字，就这样调用
    # 如果你当前 mapper 还叫 to_preset_recipe_spec，请临时替换成对应函数名
    if hasattr(recipe_spec_mapper, "to_raw_preset_recipe_spec"):
        raw_preset_spec = recipe_spec_mapper.to_raw_preset_recipe_spec(raw_preset)
    else:
        raise AttributeError(
            "RecipeSpecMapper is expected to implement to_raw_preset_recipe_spec(raw_preset)."
        )

    logger.info("Raw preset mapped to RawPresetRecipeSpec successfully.")
    print(f"raw_preset_spec.recipe_id        = {raw_preset_spec.recipe_id}")
    print(f"raw_preset_spec.name             = {raw_preset_spec.name}")
    print(f"raw_preset_spec.ingredients len  = {len(raw_preset_spec.ingredients)}")

    print_section("STEP 5 | Hydrate ingredient profiles by fdc_id")

    fdc_ids = [item.fdc_id for item in raw_preset_spec.ingredients]
    fdc_ids = list(dict.fromkeys(fdc_ids))  # preserve order + dedupe

    logger.info("Collected %s unique fdc_id values.", len(fdc_ids))
    print(f"Collected fdc_ids count = {len(fdc_ids)}")
    print(f"fdc_ids preview         = {fdc_ids[:10]}")

    profiles_by_fdc_id = ingredient_repository.get_ingredient_profiles_by_fdc_ids(fdc_ids)

    if not profiles_by_fdc_id:
        raise RuntimeError("No IngredientProfile objects were loaded by fdc_id.")

    missing_fdc_ids = [fdc_id for fdc_id in fdc_ids if fdc_id not in profiles_by_fdc_id]
    if missing_fdc_ids:
        raise RuntimeError(
            f"Missing IngredientProfile for fdc_id(s): {missing_fdc_ids}"
        )

    logger.info("Ingredient profiles hydrated successfully.")
    print_profiles_by_fdc(profiles_by_fdc_id)

    print_section("STEP 6 | Resolve raw preset -> PresetRecipeSpec by pet weight")

    # 这里调用你 service 中最新的 resolve 函数
    # 推荐最终签名：
    # _resolve_preset_items_for_pet(raw_preset, pet_weight_kg, ingredient_profiles_by_fdc_id)
    resolved_preset = service._resolve_preset_items_for_pet(
        raw_preset=raw_preset_spec,
        pet_weight_kg=float(request.pet_profile.weight_kg),
        ingredient_profiles_by_fdc_id=profiles_by_fdc_id,
    )

    logger.info("Resolved PresetRecipeSpec generated successfully.")
    print(f"resolved_preset.recipe_id        = {resolved_preset.recipe_id}")
    print(f"resolved_preset.name             = {resolved_preset.name}")
    print(f"resolved_preset.is_fully_resolved= {resolved_preset.is_fully_resolved()}")
    print_resolved_items(resolved_preset)

    print_section("STEP 7 | Optional: Call _resolve_full_preset_spec end-to-end")

    resolved_preset_2, profiles_by_ingredient_id = service._resolve_full_preset_spec(request)

    logger.info("_resolve_full_preset_spec executed successfully.")
    print(f"resolved_preset_2.recipe_id      = {resolved_preset_2.recipe_id}")
    print(f"profiles_by_ingredient_id count  = {len(profiles_by_ingredient_id)}")
    print_resolved_items(resolved_preset_2)

    print_section("STEP 8 | Build display weights from resolved preset")

    display_weights = service._build_display_weights_from_resolved_preset(
        resolved_preset_2
    )
    logger.info("_build_display_weights_from_resolved_preset executed successfully.")
    print_display_weights(display_weights)

    print_section("STEP 9 | Build analysis inputs from display weights")

    analysis_weights, analysis_profiles, analysis_debug = service._build_analysis_inputs_for_preset(
        preset=resolved_preset_2,
        display_weights=display_weights,
        ingredient_profiles=profiles_by_ingredient_id,
    )
    logger.info("_build_analysis_inputs_for_preset executed successfully.")
    print_analysis_inputs(analysis_weights, analysis_profiles, analysis_debug)

    print_section("STEP 10 | Success summary")

    print("Preset resolution + display/analysis input builder test completed successfully.")
    print("Verified chain:")
    print("  RecipeGenerationRequest")
    print("    -> request validation")
    print("    -> raw preset repository lookup")
    print("    -> raw preset mapping")
    print("    -> ingredient profile hydration by fdc_id")
    print("    -> resolve preset items by pet weight")
    print("    -> resolved PresetRecipeSpec")
    print("    -> _build_display_weights_from_resolved_preset")
    print("    -> _build_analysis_inputs_for_preset")

    print_section("STEP 11 | Run nutrient analysis")

    nutrient_analysis = nutrient_analysis_service.analyze(
        weights=analysis_weights,
        ingredient_profiles=analysis_profiles,
        pet_profile=request.pet_profile,
        normalize_per_1000_kcal=False,
    )

    logger.info("nutrient_analysis_service.analyze executed successfully.")
    print_nutrient_analysis(nutrient_analysis)
    print_key_nutrient_analysis(nutrient_analysis)

    print_section("STEP 12 | Build RecipeGenerationResult")

    total_weight_grams = round(
        sum(float(w.weight_grams) for w in display_weights),
        6,
    )

    used_supplements = [
        w.ingredient_id
        for w in display_weights
        if getattr(w, "is_supplement", False)
    ]

    result = RecipeGenerationResult(
        mode=RecipeGenerationMode.SCALE_PRESET,
        status=SolveStatus.FEASIBLE,
        recipe_id=f"scaled_{resolved_preset_2.recipe_id}",
        total_weight_grams=total_weight_grams,
        weights=display_weights,
        nutrient_analysis=nutrient_analysis,
        used_supplements=used_supplements,
        warnings=[],
        debug_meta={
            "generated_by": "preset_resolution_test_script",
            "request_id": request.request_id,
            "requested_by": request.requested_by,
            "preset_recipe_id": resolved_preset_2.recipe_id,
            "pet_weight_kg": float(request.pet_profile.weight_kg or 0.0),
            "analysis_debug": analysis_debug,
        },
        solve_time_seconds=None,
    )

    logger.info("RecipeGenerationResult built successfully.")
    print_recipe_generation_result(result)

    logger.info("Preset resolution test flow finished.")


if __name__ == "__main__":
    asyncio.run(main())