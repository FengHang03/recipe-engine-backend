from typing import List, Optional
from uuid import UUID
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.api.dependencies.auth import FirebaseUser, get_current_user
from app.api.dependencies.recipe import get_recipe_request_router
from app.db.models.pet import Pet
from app.db.models.recipe_run import RecipeRun, RecipeRunStatus
from app.db.session import get_db
from app.domains.recipe_runs.schemas import (
    RecipeRunListItem,
    RecipeRunResponse,
    RunCreatedResponse,
    SubmitRecipeGenerationRunRequest,
    SubmitRunRequest,
)
from app.domains.recipe_runs.service import (
    compute_recipe_generation_run,
    compute_recipe_run,
    enforce_run_cap,
)

router = APIRouter(prefix="/recipe-runs", tags=["recipe_runs"])


def _get_pet_or_404(db: Session, pet_id: UUID, owner_uid: str) -> Pet:
    pet = db.get(Pet, pet_id)

    if pet is None or pet.owner_uid != owner_uid:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Pet not found",
        )

    return pet


def _enum_value(value):
    return getattr(value, "value", value)


@router.post("", response_model=RunCreatedResponse, status_code=status.HTTP_202_ACCEPTED)
async def submit_recipe_run(
    body: SubmitRunRequest,
    background_tasks: BackgroundTasks,
    request: Request,
    current_user: FirebaseUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> RunCreatedResponse:
    """
    Legacy recipe-run endpoint.

    Kept for the old legacy_recipe_engine.generate_recipes(pet, top_k) path.
    New Beginner DIY / Preset generation should use:
    POST /api/recipe-runs/generate
    """
    if body.pet_id is not None:
        _get_pet_or_404(db, body.pet_id, current_user.uid)

    session_factory = request.app.state.db_session_factory
    enforce_run_cap(current_user.uid, session_factory)

    is_saved = False
    expires_at = datetime.now(timezone.utc) + timedelta(days=7) if not is_saved else None

    run = RecipeRun(
        owner_uid=current_user.uid,
        pet_id=body.pet_id,
        life_stage=str(_enum_value(body.pet.life_stage)),
        daily_calories_kcal=body.pet.daily_calories_kcal,
        input_snapshot={
            "pet_id": str(body.pet_id) if body.pet_id else None,
            "pet": body.pet.model_dump(mode="json"),
            "top_k": body.top_k,
        },
        is_saved=is_saved,
        expires_at=expires_at,
        status=RecipeRunStatus.PENDING,
    )

    db.add(run)
    db.flush()
    run_id = run.id
    db.commit()

    background_tasks.add_task(
        compute_recipe_run,
        run_id=run_id,
        pet_profile=body.pet,
        top_k=body.top_k,
        session_factory=session_factory,
        fastapi_state=request.app.state,
    )

    return RunCreatedResponse(run_id=run_id, status=RecipeRunStatus.PENDING)


@router.post("/generate", response_model=RunCreatedResponse, status_code=status.HTTP_202_ACCEPTED)
async def submit_recipe_generation_run(
    body: SubmitRecipeGenerationRunRequest,
    background_tasks: BackgroundTasks,
    request: Request,
    current_user: FirebaseUser = Depends(get_current_user),
    db: Session = Depends(get_db),
    request_router=Depends(get_recipe_request_router),
) -> RunCreatedResponse:
    """
    Unified async recipe generation endpoint.

    Use this for Beginner DIY, Preset, and future AI recipe generation.

    It wraps the existing RecipeGenerationRequest flow:
    RequestRouter.route(request)
    and persists the result to recipe_runs.policy_snapshot.
    """
    if body.pet_id is not None:
        _get_pet_or_404(db, body.pet_id, current_user.uid)

    session_factory = request.app.state.db_session_factory
    enforce_run_cap(current_user.uid, session_factory)

    pet_profile = body.request.pet_profile

    is_saved = False
    expires_at = datetime.now(timezone.utc) + timedelta(days=7) if not is_saved else None

    run = RecipeRun(
        owner_uid=current_user.uid,
        pet_id=body.pet_id,
        life_stage=str(_enum_value(pet_profile.life_stage)),
        daily_calories_kcal=pet_profile.daily_calories_kcal,
        input_snapshot={
            "pet_id": str(body.pet_id) if body.pet_id else None,
            "pet_name": body.pet_name if body.pet_name else None,
            "request": body.request.model_dump(mode="json"),
        },
        is_saved=is_saved,
        expires_at=expires_at,
        status=RecipeRunStatus.PENDING,
    )

    db.add(run)
    db.flush()
    run_id = run.id
    db.commit()

    background_tasks.add_task(
        compute_recipe_generation_run,
        run_id=run_id,
        generation_request=body.request,
        session_factory=session_factory,
        request_router=request_router,
    )

    return RunCreatedResponse(run_id=run_id, status=RecipeRunStatus.PENDING)


@router.get("", response_model=List[RecipeRunListItem])
def list_recipe_runs(
    pet_id: Optional[UUID] = None,
    current_user: FirebaseUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> List[RecipeRunListItem]:
    q = db.query(RecipeRun).filter(RecipeRun.owner_uid == current_user.uid)

    if pet_id is not None:
        q = q.filter(RecipeRun.pet_id == pet_id)

    runs = q.order_by(RecipeRun.created_at.desc()).all()

    return [
        RecipeRunListItem(
            run_id=run.id,
            pet_id=run.pet_id,
            status=run.status,
            life_stage=run.life_stage,
            daily_calories_kcal=float(run.daily_calories_kcal),
            created_at=run.created_at,
        )
        for run in runs
    ]


@router.get("/{run_id}", response_model=RecipeRunResponse)
def get_recipe_run(
    run_id: UUID,
    current_user: FirebaseUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> RecipeRunResponse:
    run = db.get(RecipeRun, run_id)

    if run is None or run.owner_uid != current_user.uid:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Run not found",
        )

    return RecipeRunResponse(
        run_id=run.id,
        pet_id=run.pet_id,
        status=run.status,
        life_stage=run.life_stage,
        daily_calories_kcal=float(run.daily_calories_kcal),
        created_at=run.created_at,
        error_message=run.error_message,
        result=run.policy_snapshot if run.status == RecipeRunStatus.SUCCESS else None,
    )


@router.delete("/{run_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_recipe_run(
    run_id: UUID,
    current_user: FirebaseUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> None:
    run = db.get(RecipeRun, run_id)

    if run is None or run.owner_uid != current_user.uid:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Run not found",
        )

    db.delete(run)