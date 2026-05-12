# Review — `2026-05-align-recipe-run-orm`

**Reviewer:** Review Agent (read-only)  
**Inputs:** `docs/agents/review-agent.md`, task doc, `03-implementation-summary.md`, contract audit, contracts/feature maps, implementation status, `backend/AGENTS.md`, `backend/CLAUDE.md`  
**Note:** Repo root `AGENTS.md` / `CLAUDE.md` were not present; project rules reference them — `backend/AGENTS.md` and `backend/CLAUDE.md` were used as the effective agent docs.

---

## How “current git diff” was interpreted

- `git diff` against HEAD lists **many** tracked paths (e.g. `recipe_generation`, `pet-recipe-web`, `shared/contracts`, `main.py`, `energy_service.py`, …) that are **outside** the task’s allowed edit list.
- The files named in `03-implementation-summary.md` (`backend/app/db/models/recipe_run.py`, `backend/app/domains/recipe_runs/router.py`, and the run doc) are **`??` untracked** in this workspace, so they **do not appear** in `git diff`. Their contents were reviewed directly and cross-checked with the implementation summary.

---

## 1. Did the Coding Agent only edit allowed files?

**For the ORM alignment work as documented:** Yes. The described edits stay within **May Edit** (`recipe_run.py`, `recipe_runs/router.py`, `03-implementation-summary.md`). `service.py` and `schemas.py` were correctly left unchanged.

**For the repository as a whole (tracked `git diff`):** No. There are substantial tracked changes under forbidden or unrelated areas (e.g. `backend/app/domains/recipe_generation/**`, `pet-recipe-web/src/**`, other backend modules). Those must **not** be attributed to or merged with this task unless they belong to a separate change set.

**PR hygiene (blocking if ignored):** Ensure a PR for this task adds/commits **only** the intended recipe-runs ORM/router/doc files, and does not accidentally include the broader dirty tree.

---

## 2. Does `RecipeRun.pet_id` now allow temporary pets?

**Yes.** `pet_id` is `nullable=True` with `ForeignKey("pets.id", ondelete="SET NULL")`, which matches the task (nullable for temporary pets; prefer SET NULL on delete).

---

## 3. Do `is_saved` and `expires_at` exist in the ORM and match DB expectations?

**Yes in the ORM:** `is_saved` is `Boolean`, `nullable=False`, `default=False`. `expires_at` is `DateTime(timezone=True)`, nullable.

**DB alignment:** Correct **if** the live `recipe_runs` table already has these columns and compatible types (as assumed in the task and implementation summary). If any environment still lacks nullable `pet_id`, these columns, or a compatible FK rule, inserts will fail — that is an environment/migration concern, not a code-shape issue in the reviewed model.

---

## 4. Did it avoid changing `recipe_generation`, `pets`, frontend, `saved_recipes`, and `policy_snapshot`?

**Per the task implementation files:** Yes — no edits to those areas in `recipe_run.py` / `recipe_runs/router.py`; `policy_snapshot` usage in `get_recipe_run` is unchanged.

**Per full tracked `git diff`:** The working tree **does** include changes under `recipe_generation` and `pet-recipe-web` (and others). Those are **out of scope** for this task and should be isolated from the ORM-alignment PR.

---

## 5. Does the change preserve `/api/recipe-runs/generate` behavior?

**Yes, at the HTTP contract level:** Same route, same `RunCreatedResponse`, same auth and pet ownership check when `pet_id` is set, same `input_snapshot` shape, same background task (`compute_recipe_generation_run`).

**Persistence:** Inserts now include `is_saved` and `expires_at` explicitly (mirroring the legacy `POST /api/recipe-runs` rule: not saved → ~7 days TTL, saved path would use `None` when `is_saved` is true). That is additive DB behavior and aligns with the audit’s finding that the router was already passing these kwargs.

---

## 6. Schema / API response changes needing frontend updates?

**No.** `RunCreatedResponse`, `RecipeRunResponse`, and `RecipeRunListItem` are unchanged; no new response fields were added. Wire JSON for create/get/list remains the same for this task.

---

## 7. Are validation steps sufficient?

**Adequate for manual acceptance** (compileall, two API scenarios, SQL spot-check) as listed in the task and summary.

**Gaps (non-blocking unless you want stronger gates):**

- No automated tests under `backend/app/domains/recipe_runs` (summary already notes this).
- No scripted check that **production/staging** DDL matches the ORM (nullable `pet_id`, columns, FK) — the summary’s “ORM vs DB drift” risk is real until verified per environment.

---

## Blocking issues

1. **Mixed working tree:** Tracked `git diff` contains many changes **outside** the task’s allowed paths. Shipping them together would violate task scope and review expectations; split commits/PRs and verify the ORM PR contains only the intended files.
2. **Untracked task files:** Core implementation files are `??`; they will be **missing from `git diff` and easy to omit from a commit** until `git add`. Confirm they are included when this task is merged.

---

## Non-blocking suggestions

1. After merge, tick **`recipe_runs.pet_id nullable`** (and optionally note ORM parity) in `docs/implementation-status.md`.
2. Optionally refresh **`docs/audits/contract-audit-2026-05.md` §7** later with a one-line note that ORM drift for `RecipeRun` was addressed (audit doc is historical; not required for this PR).
3. When pet-delete behavior is designed, reconcile **`Pet` ORM `recipe_runs` cascade** vs DB `ON DELETE SET NULL`** (called out in `03-implementation-summary.md`).

---

## Required fixes

- **Process / merge:** Isolate and commit the task-scoped files; do not merge unrelated tracked edits under the same PR as this ORM alignment.
- **Operational:** Confirm each target database’s `recipe_runs` schema matches the updated ORM before relying on `/generate` in that environment.

*(No code changes were requested from Review Agent.)*

---

## Validation commands

From repo root (PowerShell-friendly):

```powershell
python -m compileall backend/app/db/models/recipe_run.py backend/app/domains/recipe_runs
```

If/when tests exist:

```powershell
pytest backend/app/domains/recipe_runs
```

Manual API + SQL as in `docs/tasks/2026-05-align-recipe-run-orm.md` (temporary `pet_id: null`, saved `pet_id`, and `SELECT id, owner_uid, pet_id, status, is_saved, expires_at, created_at FROM recipe_runs ...`).

---

## Docs to update

| Doc | Why |
|-----|-----|
| `docs/implementation-status.md` | Mark `recipe_runs.pet_id nullable` / ORM–DB alignment as done once verified in prod. |
| `docs/runs/2026-05-align-recipe-run-orm/04-review.md` | This file (review artifact). |

Optional later: short note in contract audit or `docs/contracts-map.md` only if you want explicit “ORM now matches nullable `pet_id` + `is_saved` + `expires_at`” — `contracts-map` already states optional `pet_id` at the concept level.

---

*End of review.*
