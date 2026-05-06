> AI note:
> Before editing files in this folder, first read this README and confirm:
> 1. whether the requested change is data-access logic or business logic
> 2. whether the change belongs in cache / repository / helper
> 3. whether an existing shared contract should be reused

# Ingredients Domain README

## 1. Purpose of This Folder

This folder contains the **ingredient data support domain** for the recipe system.

Its job is to provide a stable, reusable data access layer for:

- ingredient base metadata
- ingredient nutrient values
- ingredient tags
- raw / cooked pairing
- in-memory cache and lookup indexes

This folder exists to support higher-level business domains such as:

- preset recipe generation
- beginner diy generation
- nutrient analysis
- explain / interpretation
- future ingredient-related tooling

This is **not** a full workflow domain like `recipe_generation` or `explain`.
It is a **lightweight support domain** centered around:

- cache
- repository
- lookup
- mapping

---

## 2. Why This Folder Exists

Ingredient-related logic is used by multiple domains and was becoming too large to leave scattered across:

- individual services
- ad hoc repository methods
- DB helper functions
- recipe-specific modules

This folder centralizes those responsibilities so that:

1. ingredient and nutrient lookups are consistent
2. repeated database queries can be reduced through preload cache
3. raw / cooked profile selection follows one shared rule
4. higher-level domains do not need to know DB details
5. future changes to ingredient storage stay localized

---

## 3. Scope

This folder is responsible for:

- loading ingredient base rows from storage
- loading ingredient nutrient rows from storage
- loading ingredient tags from storage
- building in-memory indexes for fast lookup
- hydrating `IngredientProfile`
- looking up ingredient profiles by:
  - `ingredient_id`
  - `fdc_id`
- resolving cooked ingredient profiles via:
  - `raw_equivalent_fdc_id`
- providing nutrient tables / matrices for downstream analysis

This folder is **not** responsible for:

- recipe generation orchestration
- preset resolution logic
- beginner diy structure logic
- L1 candidate selection strategy
- L2 optimization solving
- explain prompt building
- frontend display formatting
- API request / response routing

If logic starts to depend on pet profile, recipe mode, or generation workflow, it probably belongs in a higher-level domain instead of here.

---

## 4. Design Position

`ingredients` should be treated as a **cross-domain support module**.

It is intentionally **lighter** than domains that use full layering such as:

- contracts
- engines
- orchestration
- infra

This folder currently does **not** need a full four-layer structure because its primary responsibilities are data support and lookup, not business workflow execution.

Current design philosophy:

- keep it simple
- avoid speculative abstractions
- prefer cache + repository + helper over unnecessary layering
- keep contracts in shared models when they are reused across domains

---

## 5. Core Design Principles

### A. Contract-first at the edges
Shared domain contracts such as `IngredientProfile` should remain stable and reusable.
This folder should adapt raw storage rows into those contracts.

### B. Cache-first for repeated lookups
Ingredient data is read frequently and changes relatively rarely.
Whenever safe, use preloaded cache and in-memory indexes instead of repeated DB queries.

### C. Repository hides storage details
Higher-level domains should not need to know table names, SQL, or index-building details.

### D. Keep internal models lightweight
Internal cache rows and in-memory containers may use lightweight internal structures.
Not every internal object needs to become a full shared contract.

### E. No business orchestration here
This folder should support workflows, not own them.

---

## 6. Folder Responsibilities by File

> Exact filenames may evolve, but the intended responsibility split should remain stable.

### `ingredient_data_cache.py`
Owns the preloaded in-memory cache for ingredient-related data.

Typical responsibilities:
- load all active ingredient rows
- load all ingredient tags
- load all ingredient nutrient rows
- build lookup indexes such as:
  - `by_ingredient_id`
  - `by_fdc_id`
  - `cooked_by_raw_equivalent_fdc_id`
  - `tags_by_ingredient_id`
  - `nutrients_by_ingredient_id`

This file should focus on:
- preload
- indexing
- lightweight retrieval

It should not contain recipe business logic.

---

### `ingredient_repository.py`
Owns ingredient profile hydration and ingredient metadata lookup.

Typical responsibilities:
- get ingredient profile by `ingredient_id`
- get ingredient profiles by `ingredient_id` batch
- get ingredient profiles by `fdc_id` batch
- get cooked profile by `raw_equivalent_fdc_id`
- map cache rows into `IngredientProfile`

This repository should be the main entry point for:
- ingredient profile lookup
- ingredient base metadata lookup
- raw/cooked profile resolution support

It should not perform recipe generation.

---

### `ingredient_nutrients_repository.py`
Owns nutrient-value lookup and nutrient matrix generation.

Typical responsibilities:
- get nutrients for one ingredient
- get nutrients for multiple ingredients
- return long-form nutrient rows
- build wide nutrient matrix for analysis / optimization

This file should support downstream domains such as:
- nutrient analysis
- L2 optimization
- future diagnostics

It should not decide whether a nutrient is “good” or “bad”.
Interpretation belongs elsewhere.

---

### `dependencies.py` (optional)
If used, this file should expose dependency injection helpers for:
- cache singleton
- ingredient repository singleton
- ingredient nutrients repository singleton

This is preferred over ad hoc repository construction inside service code.

---

### `README.md`
This file.
Its purpose is to explain the intent, scope, and boundaries of this folder to both developers and AI assistants.

---

## 7. Runtime Lifecycle

The intended runtime pattern is:

1. App starts
2. Ingredient-related reference data is preloaded into memory
3. Repositories read from cache
4. Higher-level domains consume repositories
5. DB is not repeatedly queried for the same reference data during normal requests

Recommended lifecycle:

- preload on FastAPI app startup
- store cache and repositories as app-level singletons
- inject repositories into services
- avoid creating fresh repository instances inside every request flow

---

## 8. Data Flow

Typical flow for ingredient hydration:

1. caller provides `ingredient_id` or `fdc_id`
2. repository reads matching row from `IngredientDataCache`
3. repository reads tags and nutrient map from cache
4. repository maps data into `IngredientProfile`
5. caller receives stable domain contract

Typical flow for cooked profile lookup:

1. caller provides raw ingredient `fdc_id`
2. repository uses `raw_equivalent_fdc_id -> cooked profile` index
3. repository returns cooked `IngredientProfile` if present
4. caller decides whether to use cooked or raw profile in analysis

---

## 9. Boundary Rules

To keep this folder healthy, follow these rules.

### Allowed here
- DB read logic for ingredient reference data
- preload cache logic
- index building
- row-to-contract mapping
- batch lookup utilities
- nutrient matrix building

### Not allowed here
- pet-specific logic
- preset-specific logic
- beginner diy category logic
- recipe scoring
- rule engine logic
- explain wording
- UI display rules
- response assembly for generation endpoints

If a function requires:
- `pet_profile`
- `recipe mode`
- `life_stage decisions`
- `category ratio`
- `business warnings`

then it likely belongs outside this folder.

---

## 10. Relationship to Shared Contracts

This folder should reuse shared contracts wherever possible.

Examples of contracts/enums that usually live outside this folder:
- `IngredientProfile`
- `FoodGroup`
- `FoodSubgroup`
- `NutrientID`

Reason:
these are cross-domain concepts, not ingredients-folder-specific details.

This folder should **map into shared contracts**, not duplicate them.

---

## 11. Relationship to Recipe Domains

### Supports preset recipe
Used for:
- hydrate ingredient profiles by `fdc_id`
- cooked profile lookup during analysis input building
- nutrient lookup during analysis

### Supports beginner diy
Used for:
- ingredient hydration
- nutrient matrix building
- cooked/raw pairing
- supplement / ingredient data lookup

### Supports explain
Used indirectly through already-built recipe / analysis structures.
Explain should not directly own ingredient storage logic.

---

## 12. Performance Philosophy

This folder exists partly to reduce repeated DB calls.

Important principle:
the performance gain should come from **centralized preload + memory lookup**, not from scattering small caches across unrelated services.

Preferred:
- one preload cache
- one clear source of truth for indexes
- repositories that read from the cache

Avoid:
- multiple inconsistent local caches
- each service doing its own DB hydration
- repeated N+1 cooked profile queries

---

## 13. Internal Modeling Guidance

Not every internal object here needs to be a shared contract.

Use lightweight internal structures for:
- cache rows
- internal index entries
- temporary storage containers

Use shared contracts for:
- objects that cross domain boundaries
- stable semantic entities consumed by other modules

Rule of thumb:
- **internal cache shape** = lightweight internal model
- **cross-domain payload** = shared contract

---

## 14. Change Policy

When changing this folder:

1. keep changes surgical
2. avoid broad refactors unless multiple files clearly benefit
3. preserve repository method signatures when possible
4. do not mix business logic into cache / repository files
5. document any new lookup index or data assumption here

Every change should answer:
- is this a data access concern?
- is this a cache concern?
- is this a shared mapping concern?
- or is this actually business logic that belongs elsewhere?

---

## 15. Guidance for AI Assistants

If you are an AI assistant editing code in this folder, follow these rules:

### First understand the role of this folder
This is a lightweight ingredient support domain, not a recipe workflow domain.

### Do not silently add business logic
Do not place preset, beginner diy, or pet-specific logic here unless explicitly asked and clearly justified.

### Prefer minimal changes
If the request is about lookup speed, improve cache / repository behavior first.
Do not redesign unrelated architecture.

### Reuse shared contracts
Do not create duplicate ingredient models if `IngredientProfile` already exists and is sufficient.

### Keep boundaries sharp
If a proposed change starts requiring recipe context, move that logic to a higher-level domain.

### Optimize for reuse
Changes here should make ingredient access more reusable across preset, beginner diy, analysis, and explain.

---

## 16. Future Evolution

This folder may grow in the future, but only when justified.

Possible future additions:
- `ingredient_queries.py` for SQL separation
- `ingredient_mapper.py` if row mapping becomes larger
- `dependencies.py` for cleaner DI
- admin-side refresh utilities
- cache reload tooling

Do **not** add extra layering just for symmetry.
Only add structure when responsibilities genuinely become large enough.

---

## 17. Summary

This folder is the ingredient data support layer for the recipe system.

In one sentence:

> `domains/ingredients` provides cached, reusable, storage-agnostic ingredient and nutrient lookup for higher-level recipe domains.

Its core responsibilities are:
- preload
- lookup
- mapping
- nutrient access

Its non-responsibilities are:
- orchestration
- business rules
- recipe generation logic

Keep this folder simple, stable, and reusable.