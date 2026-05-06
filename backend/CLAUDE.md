# CLAUDE.md

Behavioral guidelines to reduce common LLM coding mistakes. Merge with project-specific instructions as needed.

**Tradeoff:** These guidelines bias toward caution over speed. For trivial tasks, use judgment.

## 1. Think Before Coding

**Don't assume. Don't hide confusion. Surface tradeoffs.**

Before implementing:
- State your assumptions explicitly. If uncertain, ask.
- If multiple interpretations exist, present them - don't pick silently.
- If a simpler approach exists, say so. Push back when warranted.
- If something is unclear, stop. Name what's confusing. Ask.

## 2. Simplicity First

**Minimum code that solves the problem. Nothing speculative.**

- No features beyond what was asked.
- No abstractions for single-use code.
- No "flexibility" or "configurability" that wasn't requested.
- No error handling for impossible scenarios.
- If you write 200 lines and it could be 50, rewrite it.

Ask yourself: "Would a senior engineer say this is overcomplicated?" If yes, simplify.

## 3. Surgical Changes

**Touch only what you must. Clean up only your own mess.**

When editing existing code:
- Don't "improve" adjacent code, comments, or formatting.
- Don't refactor things that aren't broken.
- Match existing style, even if you'd do it differently.
- If you notice unrelated dead code, mention it - don't delete it.

When your changes create orphans:
- Remove imports/variables/functions that YOUR changes made unused.
- Don't remove pre-existing dead code unless asked.

The test: Every changed line should trace directly to the user's request.

## 4. Goal-Driven Execution

**Define success criteria. Loop until verified.**

Transform tasks into verifiable goals:
- "Add validation" → "Write tests for invalid inputs, then make them pass"
- "Fix the bug" → "Write a test that reproduces it, then make it pass"
- "Refactor X" → "Ensure tests pass before and after"

For multi-step tasks, state a brief plan:
```
1. [Step] → verify: [check]
2. [Step] → verify: [check]
3. [Step] → verify: [check]
```

Strong success criteria let you loop independently. Weak criteria ("make it work") require constant clarification.

---

**These guidelines are working if:** fewer unnecessary changes in diffs, fewer rewrites due to overcomplication, and clarifying questions come before implementation rather than after mistakes.


## Commands

```bash
# Run locally (from backend/)
uvicorn app.main:app --host 0.0.0.0 --port 8080 --reload

# Run tests
pytest app/L2Generator/test_l2.py
pytest app/domains/recipe_generation/

# Build Docker image
docker build -t pet-recipe-backend .

# Deploy to Cloud Run
bash deploy_with_secrets.sh
```

Requires a `.env` file in `backend/` with at minimum `DATABASE_URL` (PostgreSQL).

## Architecture

This is a **pet recipe generation API** (FastAPI) that generates nutritionally balanced recipes for dogs and cats using a two-stage optimization pipeline:

### Two-Stage Pipeline

**L1 Generator** (`app/L1Generator/`) — heuristic candidate generation
- Assigns ingredients to typed slots (MAIN_PROTEIN, ORGAN_LIVER, VEGETABLE, OMEGA3_LC, SUPPLEMENT, etc.) defined in `l1_config.py`
- `l1_slot_scheduler.py` activates slots based on pet profile
- Outputs a list of `RecipeCombination` objects scored for diversity, risk, and nutritional completeness

**L2 Optimizer** (`app/L2Generator/`) — linear programming via Google OR-Tools
- Two-phase solve: Phase 1 without supplements, Phase 2 with supplements
- Enforces AAFCO nutritional standards from `l2_aafco_config.py`
- Returns `OptimizationResult` with per-ingredient gram weights and full nutrient analysis

`app/recipe_engine.py` orchestrates the L1→L2 pipeline and is the legacy entry point.

### Domain Modules (`app/domains/`)

Newer domain-structured code coexists with the legacy `L1Generator/L2Generator` modules:

- `energy/` — computes daily calorie requirement from pet profile (weight, life stage, activity, reproductive status)
- `ingredients/` — ingredient data cache and repositories (lazy-loaded from DB on startup)
- `explain/` — LLM-powered recipe explanations via Qwen API
- `recipe_chat/` — chat interface wrapping recipe context
- `recipe_generation/` — newer structured domain with contracts, orchestration, engines, and infra subdirectories

### API Layer (`app/api/`)

- `POST /api/recipe-generation/generate` — main recipe generation endpoint
- `POST /api/calculate-energy` — energy/calorie calculation
- `GET /health` — health check with ingredient count

### Startup Flow (`app/main.py` lifespan)

1. Create SQLAlchemy engine (psycopg2 locally, pg8000 on Cloud Run via Unix socket)
2. Load `IngredientDataCache` from DB
3. Initialize `IngredientDataLoader`, `L1RecipeGenerator`, `L2Optimizer`, `RecipeEngine`
4. All heavy init is synchronous; Cloud Run uses `--workers=1 --concurrency=4` (CPU-bound workload)

### Key Shared Types (`app/common/`)

- `enums.py`: `NutrientID` (USDA nutrient IDs), `LifeStage`, `ActivityLevel`, `SterilizationStatus`, `ReproductiveStage`, `FoodGroup`, `FoodSubgroup`, `SlotType`
- `models.py`: `Ingredient`, `RecipeCombination`
- `utils.py`: `UnitConverter`, nutrient unit helpers

## Environment

| Variable | Purpose |
|---|---|
| `ENVIRONMENT` | `"development"` or `"production"` |
| `DATABASE_URL` | Full PostgreSQL connection string |
| `QWEN_API_KEY` / `QWEN_BASE_URL` | LLM API for recipe explanations |
| `INSTANCE_CONNECTION_NAME` | Cloud SQL instance (production only) |

Local dev uses `postgresql+psycopg2`, production uses `postgresql+pg8000` over Cloud SQL Unix socket.

## Interface Contract

`interface.md` at the repo root defines the frontend↔backend request/response schemas for energy calculation and recipe generation. Keep this file in sync when changing API contracts.
