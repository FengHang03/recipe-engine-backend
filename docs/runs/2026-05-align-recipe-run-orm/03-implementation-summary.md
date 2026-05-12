# Implementation summary

Task: `docs/tasks/2026-05-align-recipe-run-orm.md`  
Slug: `2026-05-align-recipe-run-orm`

## 1. Files changed

- `backend/app/db/models/recipe_run.py`
- `backend/app/domains/recipe_runs/router.py`
- `docs/runs/2026-05-align-recipe-run-orm/03-implementation-summary.md` (this file)

## 2. What changed

### `recipe_run.py`

- **`RecipeRun.pet_id`:** `nullable=True` and foreign key `ondelete` changed from `CASCADE` to **`SET NULL`** so a deleted pet row can leave historical runs with `pet_id` cleared instead of blocking null inserts for temporary pets.
- **`RecipeRun.is_saved`:** New `Boolean` column, `nullable=False`, `default=False`.
- **`RecipeRun.expires_at`:** New timezone-aware `DateTime`, nullable (matches legacy router logic where saved runs would use `None`).

### `router.py`

- **`POST /api/recipe-runs/generate`:** When constructing `RecipeRun`, set **`is_saved = False`** and **`expires_at`** using the same rule as `POST /api/recipe-runs` (legacy): `now + 7 days` when not saved, else `None`, so inserts match the columns the DB expects and acceptance criteria for populated `is_saved` / `expires_at`.

No edits to `service.py` or `schemas.py` (constructors and response shapes already sufficient for this task).

## 3. Contract / API impact

- **Request/response Pydantic schemas:** Unchanged (`RunCreatedResponse`, `RecipeRunResponse`, etc.).
- **Wire JSON:** Unchanged; `policy_snapshot` and `input_snapshot` were not modified.
- **Behavioral impact:** Inserts for `/api/recipe-runs/generate` now persist `is_saved` and `expires_at` at the ORM/DB layer instead of relying on missing attributes or DB defaults only.

## 4. DB assumptions

- Table **`recipe_runs`** already includes columns **`is_saved`** and **`expires_at`** with types compatible with SQLAlchemy `Boolean` and `DateTime(timezone=True)` (e.g. PostgreSQL `boolean` and `timestamptz`).
- **`pet_id`** is nullable in the database and the FK allows **`ON DELETE SET NULL`** (or equivalent) when a referenced `pets` row is removed. This task does **not** add or edit Alembic/SQL migrations.
- If the live database still has **`pet_id` NOT NULL** or **`ON DELETE CASCADE`** only, inserts or deletes may fail until the database is migrated to match this ORM (see risks).

## 5. Validation steps

- [x] `python -m compileall backend/app/db/models/recipe_run.py backend/app/domains/recipe_runs`
- [ ] `pytest backend/app/domains/recipe_runs` (no tests under this package in repo at time of change)
- [ ] **Manual API:** `POST /api/recipe-runs/generate` with `pet_id: null` — row should have `pet_id IS NULL`, `is_saved = false`, `expires_at` set (~7 days).
- [ ] **Manual API:** same endpoint with a real `pet_id` — row should have that UUID, same `is_saved` / `expires_at` behavior.
- [ ] **SQL:**  
  `SELECT id, owner_uid, pet_id, status, is_saved, expires_at, created_at FROM recipe_runs ORDER BY created_at DESC LIMIT 5;`

## 6. Any unresolved risk

- **ORM vs database drift:** If production/staging schema has not yet been migrated (nullable `pet_id`, `is_saved`, `expires_at`, FK delete rule), runtime errors will persist until DB matches this model.
- **`Pet` ORM cascade:** `db/models/pet.py` still declares `recipe_runs` with `cascade="all, delete-orphan"` (unchanged—out of allowed edit list). DB-level `SET NULL` on `recipe_runs.pet_id` vs ORM cascade semantics should be reviewed when pets are deleted in bulk; not introduced by this task beyond the FK definition on `RecipeRun`.
