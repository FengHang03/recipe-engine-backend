# Task: Align RecipeRun ORM with database schema

## Goal

Update the backend SQLAlchemy `RecipeRun` ORM model to match the current `recipe_runs` database schema.

The database now supports:
- `recipe_runs.pet_id` nullable for temporary pets
- `recipe_runs.is_saved`
- `recipe_runs.expires_at`

The backend ORM must reflect these fields so `/api/recipe-runs/generate` can create temporary and saved-pet recipe runs reliably.

## Background

The contract audit found drift between the product rules, database schema, router behavior, and ORM model:

- Temporary pets may generate recipe runs with `pet_id = null`.
- `recipe_runs.pet_id` should be nullable.
- The router/service may pass `is_saved` and `expires_at`.
- The ORM currently does not include `is_saved` and `expires_at`.

This task is a focused structural fix, not a schema simplification pass.

## Relevant Docs

- `CLAUDE.md`
- `AGENTS.md`
- `docs/contracts-map.md`
- `docs/feature-flow-map.md`
- `docs/implementation-status.md`
- `docs/audits/contract-audit-2026-05.md`

## Relevant Files

### May Edit

- `backend/app/db/models/recipe_run.py`
- `backend/app/domains/recipe_runs/router.py`
- `backend/app/domains/recipe_runs/service.py`
- `backend/app/domains/recipe_runs/schemas.py` only if needed for API response typing
- `docs/runs/2026-05-align-recipe-run-orm/03-implementation-summary.md`

### Do Not Edit

- `backend/app/domains/recipe_generation/**`
- `backend/app/domains/pets/**`
- `backend/app/domains/ingredients/**`
- `backend/app/domains/nutrient_analysis/**`
- `pet-recipe-web/src/**`
- database migration files unless explicitly requested
- `saved_recipes` or future favorite recipe logic

## Required Changes

1. In `backend/app/db/models/recipe_run.py`:
   - Make `RecipeRun.pet_id` nullable.
   - Confirm foreign key behavior matches DB design, preferably `ON DELETE SET NULL`.
   - Add `is_saved` column.
   - Add `expires_at` column.
   - Keep existing status enum behavior unchanged unless required by current DB schema.

2. In `recipe_runs/router.py` / `service.py`:
   - Confirm any `RecipeRun(...)` constructor arguments match ORM fields.
   - Do not remove `is_saved` or `expires_at` if DB supports them.
   - Keep temporary pet flow working with `pet_id=None`.

3. In `recipe_runs/schemas.py`:
   - Only add `is_saved` / `expires_at` to response schemas if they are already needed by the frontend or history UI.
   - Otherwise leave API response shape unchanged for this task.

## Out of Scope

- Do not implement `saved_recipes`.
- Do not implement recipe history UI.
- Do not refactor recipe generation.
- Do not normalize `recipe_items` / `recipe_nutrients`.
- Do not change `policy_snapshot` schema.
- Do not unify frontend result types.

## Acceptance Criteria

- Backend starts without SQLAlchemy model errors.
- `POST /api/recipe-runs/generate` works with `pet_id = null`.
- `POST /api/recipe-runs/generate` works with a saved SQL `pet_id`.
- Inserted `recipe_runs` rows include valid `is_saved` and `expires_at` values according to current router/service logic.
- No unrelated files are changed.
- No frontend code is changed.

## Validation

Manual DB check:

```sql
SELECT id, owner_uid, pet_id, status, is_saved, expires_at, created_at
FROM recipe_runs
ORDER BY created_at DESC
LIMIT 5;
```

### Manual API checks:

1. Temporary pet:
    - Submit /api/recipe-runs/generate with pet_id: null.
    - Confirm row has pet_id IS NULL.
2. Saved pet:
    - Submit /api/recipe-runs/generate with real SQL pet UUID.
    - Confirm row has pet_id = pets.id.

## Recommended backend checks:

python -m compileall backend/app/db/models/recipe_run.py
python -m compileall backend/app/domains/recipe_runs

If tests exist:

    pytest backend/app/domains/recipe_runs  