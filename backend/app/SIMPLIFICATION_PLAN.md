# Code Simplification Plan

> **Scope**: Identify and plan removal of duplicated, dead, and over-engineered code in `app/`.
> **Rule**: No changes to production behaviour. Each phase is independently safe to execute.

---

## 1. Dead Code — Delete Immediately

These files have no production imports. Safe to delete outright.

| File | Reason |
|---|---|
| `app/debug_adapter.py` | Marked "delete after testing" in comments, no imports |
| `app/domains/recipe_generation/print_directory_tree.py` | Dev utility, hardcoded path, no imports |
| `app/domains/explain/QWEN_request_test.py` | Test file living in production module |
| `app/ingredients_generateor_incremental.py` | References undefined `TargetConfigure`, no production imports |
| `app/L1Generator/l1_example_usage.py` | Example functions never called |
| `app/L2Generator/test_l2.py` | Test file; move to `tests/` or delete |
| `app/SQLOperate/` (directory) | Data migration scripts, no production imports |
| `app/database/dateset_preparing.py` | Data prep script, no production imports |
| `app/domains/energy/generate_dog_energy_csv.py` | Dev/analysis script |
| `app/domains/energy/generate_user_display_energy_csv.py` | Dev/analysis script |
| `app/domains/recipe_generation/infra/loaders/nutrition_bundle_loader.py` | 38-line stub that references undefined `self.data_loader` |
| `app/L1Generator/export_combinations.py` | Not called from any production path |

**Verify before deletion**: run `grep -r "import <filename>"` across `app/` to confirm no hidden callers.

---

## 2. Duplicate Enum Definitions — Consolidate to One File

The same enums (`NutrientID`, `LifeStage`, `SterilizationStatus`, `ReproductiveStage`, `Species`, `SlotType`) are defined in **three** separate files:

| File | Status |
|---|---|
| `app/common/enums.py` | **Keep** — most complete, used by legacy modules |
| `app/shared/contracts/enums.py` | **Delete** — full duplicate; redirect imports to `common/enums.py` |
| `app/domains/energy/contracts/enums.py` | **Delete** — duplicate with `PyEnum` alias workaround |

**Plan**:
1. Audit every `from app.shared.contracts.enums import …` and `from app.domains.energy.contracts.enums import …` across the codebase.
2. Repoint each to `app.common.enums`.
3. Delete the two redundant files.

---

## 3. Duplicate AAFCO Configuration — One Source of Truth

| File | Lines | Status |
|---|---|---|
| `app/L2Generator/l2_aafco_config.py` | 941 | Older version |
| `app/domains/recipe_generation/engines/l2/aafco_config.py` | 1 626 | Newer, extended version |

Both define `AAFCO_STANDARDS`. A bug fixed in one is silently wrong in the other.

**Plan**:
1. Diff the two files; confirm the domains version is a strict superset.
2. Make `l2_aafco_config.py` a re-export: `from app.domains.recipe_generation.engines.l2.aafco_config import AAFCO_STANDARDS`.
3. Or simply delete `l2_aafco_config.py` and update the one import site in `l2_optimizer.py`.

---

## 4. Duplicate Unit Converter — Single Class

Three implementations of the same unit-conversion logic:

| File | Class | Notes |
|---|---|---|
| `app/common/utils.py` | `UnitConverter` | Used by L1/L2 legacy code |
| `app/database/ingredients/unit_converter.py` | `UnitConverter` | Near-identical copy |
| `app/domains/nutrient_analysis/unit_converter.py` | `NutrientUnitConverter` | Different API, same concept |

**Plan**:
1. Keep `app/common/utils.py:UnitConverter` as the single implementation.
2. Delete `app/database/ingredients/unit_converter.py`; repoint its callers.
3. Reconcile `NutrientUnitConverter` — either extend `UnitConverter` or replace it; keep one API.

---

## 5. Duplicate Ingredient Data Loading

Three classes do near-identical DB reads for ingredients:

| File | Class |
|---|---|
| `app/database/data_loader.py` (677 lines) | `IngredientDataLoader` |
| `app/domains/ingredients/ingredient_repository.py` | `IngredientRepository` |
| `app/domains/recipe_generation/infra/repositories/ingredient_repository.py` | Second `IngredientRepository` |

Both repositories delegate to `IngredientDataCache` but duplicate the initialization pattern and caching logic.

**Plan**:
1. Confirm which repository is actually wired into the live request path (`main.py` → `api/dependencies/`).
2. Delete the unused repository; update callers of the other to import from a single path.
3. `IngredientDataLoader` can stay as the raw DB layer; only one repository should wrap it.

---

## 6. Duplicate Nutrient Analysis Service

| File | Class | Lines |
|---|---|---|
| `app/domains/nutrient_analysis/nutrient_analysis_service.py` | `NutrientAnalysisService` | 615 |
| `app/domains/recipe_generation/engines/scaling/nutrient_analysis_service.py` | `NutrientAnalysisService` | 150+ |

Both compute the same derived metrics (`CA_P_RATIO`, `N6_N3_RATIO`, `EPA_DHA_SUM`).

**Plan**:
1. Identify which one is called by the live recipe generation path.
2. Check whether the smaller one can be deleted and its callers redirected.
3. If both are needed (different inputs), extract the shared derived-metric constants into one place and import from there.

---

## 7. Duplicate Ingredient Model Definitions

| File | Class | Type |
|---|---|---|
| `app/common/models.py` | `Ingredient` | Pydantic `BaseModel` |
| `app/shared/contracts/ingredient.py` | `IngredientRef`, `IngredientProfile` | Pydantic `BaseModel` |
| `app/L2Generator/l2_data_models.py` (line 85) | `Ingredient` | `dataclass` |

Each representation forces conversion boilerplate wherever they meet.

**Plan**:
1. Determine which model type is actually required at each boundary (API layer vs. solver).
2. The dataclass in `l2_data_models.py` is required by OR-Tools code that expects plain Python objects — keep it, but make it a thin internal type.
3. Unify the two Pydantic representations (`common/models.py` + `shared/contracts/ingredient.py`) into one.

---

## 8. Duplicate Energy Calculator

| File | Role |
|---|---|
| `app/EnergyCalculator/energy_calculator.py` (455 lines) | Full legacy implementation |
| `app/domains/energy/energy_calculator.py` (50 lines) | Facade that wraps domain functions |

The facade adds no logic — every method is a one-line delegation.

**Plan**:
1. Confirm `app/api/router/energy.py` calls only one of these.
2. If the legacy `EnergyCalculator/` version is not called from any live API path, delete it.
3. If the facade is the only live path, it can be removed too — callers can import the domain functions directly.

---

## 9. Unused Functions in Deployed Files

These functions are defined inside files that *are* imported, but the functions themselves are never called:

| File | Functions |
|---|---|
| `app/recipe_engine.py` | `example_basic_usage()`, `print_result()`, `main()` |

**Plan**: Delete these three functions. They are clearly leftover examples.

---

## 10. Inconsistent Cache Initialization Pattern

Three different initialization contracts for cache-using classes make dependency injection unpredictable:

- `IngredientDataCache`: `load_from_db()` class method
- `IngredientRepository` (ingredients domain): constructor + `set_data_cache()`
- `IngredientRepository` (recipe_generation domain): constructor with optional cache

**Plan**: After resolving item 5 (single repository), standardise on one pattern — constructor injection with the cache as a required parameter.

---

## Execution Order

```
Phase 1 — Zero Risk (delete files with no callers)
  → Items 1, 9

Phase 2 — Low Risk (redirect imports, delete redundant copies)
  → Items 2, 3, 4, 8

Phase 3 — Medium Risk (consolidate live code paths)
  → Items 5, 6, 7, 10
```

Each item should be committed separately so regressions are easy to bisect.

**Before each Phase 2/3 change**: run `pytest app/L2Generator/test_l2.py && pytest app/domains/recipe_generation/` to confirm nothing regresses.
