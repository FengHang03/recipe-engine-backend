# app/api/router/recipe_chat.py
from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, Response, status

from app.domains.recipe_chat.recipe_chat_service import (
    RecipeChatRequest,
    RecipeChatResponse,
    RecipeChatSession,
    RecipeChatStartSessionRequest,
    RecipeChatService,
    get_recipe_chat_service,
)

# If you already have auth, uncomment and wire it here.
# from app.api.dependencies.auth import verify_firebase_token

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/recipe-chat",
    tags=["recipe_chat"],
)


@router.post(
    "/session/start",
    response_model=RecipeChatSession,
    status_code=status.HTTP_200_OK,
    summary="Start a temporary recipe chat session",
)
async def start_session(
    request: RecipeChatStartSessionRequest,
    service: RecipeChatService = Depends(get_recipe_chat_service),
    # _user = Depends(verify_firebase_token),
) -> RecipeChatSession:
    """
    Start a new temporary recipe chat session for the current result page.

    Notes:
    - This should be called before `/message`.
    - Session is temporary and expires after inactivity.
    - No long-term persistence is intended in the current design.
    """
    if not request.session_id.strip():
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="session_id must not be empty",
        )

    return await service.start_new_session(
        session_id=request.session_id,
        recipe_context=request.recipe_context,
    )


@router.post(
    "/message",
    response_model=RecipeChatResponse,
    status_code=status.HTTP_200_OK,
    summary="Send a message to the recipe chat assistant",
)
async def send_message(
    request: RecipeChatRequest,
    service: RecipeChatService = Depends(get_recipe_chat_service),
    # _user = Depends(verify_firebase_token),
) -> RecipeChatResponse:
    """
    Send one user message to the temporary recipe chat assistant.

    Behavior:
    - Requires an existing session created via `/session/start`.
    - Returns `SESSION_NOT_FOUND` if the session does not exist.
    - Returns `SESSION_EXPIRED` if the session timed out after inactivity.
    - Falls back gracefully if the LLM is unavailable.
    """
    if not request.session_id.strip():
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="session_id must not be empty",
        )

    if not request.user_message.strip():
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="user_message must not be empty",
        )

    try:
        return await service.send_message(request)
    except Exception as exc:  # noqa: BLE001
        logger.exception("Recipe chat send_message failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Recipe chat service failed.",
        ) from exc


@router.delete(
    "/session/{session_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
    summary="Expire a recipe chat session early",
)
async def expire_session(
    session_id: str,
    service: RecipeChatService = Depends(get_recipe_chat_service),
    # _user = Depends(verify_firebase_token),
) -> Response:
    """
    Explicitly end the current temporary chat session.

    Intended use cases:
    - user closes the chat
    - result page unmounts
    - frontend wants to release the session early

    Current service behavior deletes the session immediately.
    """
    if not session_id.strip():
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="session_id must not be empty",
        )

    try:
        await service.expire_session(session_id)
        return Response(status_code=status.HTTP_204_NO_CONTENT)
    except Exception as exc:  # noqa: BLE001
        logger.exception("Recipe chat expire_session failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Recipe chat session expiration failed.",
        ) from exc


@router.get("/ping", include_in_schema=False)
async def ping() -> dict[str, str]:
    return {"status": "ok"}
    