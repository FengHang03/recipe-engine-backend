from __future__ import annotations

import asyncio
import json
import logging
import os
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any, Literal

from openai import AsyncOpenAI
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Tunables
# ---------------------------------------------------------------------------

_SESSION_TTL_MINUTES = 25
_MAX_HISTORY_TURNS = 8
_MAX_WEIGHTS_FOR_LLM = 12
_MAX_NUTRIENTS_FOR_LLM = 12
_MAX_USED_SUPPLEMENTS = 6
_MAX_WARNINGS = 6
_MAX_RESPONSE_TOKENS = 700
_DEFAULT_TEMPERATURE = 0.35

_QWEN_BASE_URL = os.getenv(
    "QWEN_BASE_URL",
    "https://dashscope-intl.aliyuncs.com/compatible-mode/v1",
)
_QWEN_MODEL = os.getenv("QWEN_MODEL", "qwen3.6-plus")
_QWEN_CHAT_API_KEY = os.getenv("QWEN_CHAT_API_KEY")


# ---------------------------------------------------------------------------
# Schemas
# If you already defined these elsewhere, import them instead.
# ---------------------------------------------------------------------------

class RecipeChatContext(BaseModel):
    recipe_id: str | None = None
    mode: str | None = None

    pet_profile: dict[str, Any] = Field(default_factory=dict)

    total_weight_grams: float | None = None
    objective_value: float | None = None

    weights: list[dict[str, Any]] = Field(default_factory=list)
    nutrient_analysis: list[dict[str, Any]] = Field(default_factory=list)

    used_supplements: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class RecipeChatRequest(BaseModel):
    session_id: str
    user_message: str
    recipe_context: RecipeChatContext


class RecipeChatStartSessionRequest(BaseModel):
    session_id: str
    recipe_context: RecipeChatContext


class RecipeChatResponse(BaseModel):
    session_id: str
    assistant_message: str

    is_expired: bool = False
    expires_at: datetime | None = None

    fallback_used: bool = False

    error_code: str | None = None
    error_message: str | None = None


class ChatMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str
    timestamp: datetime


class RecipeChatSession(BaseModel):
    session_id: str
    recipe_id: str | None = None

    created_at: datetime
    last_activity_at: datetime
    expires_at: datetime
    is_expired: bool = False

    context: RecipeChatContext
    message_history: list[ChatMessage] = Field(default_factory=list)
    message_count: int = 0


# ---------------------------------------------------------------------------
# Session store
# ---------------------------------------------------------------------------

class RecipeChatSessionStore:
    async def get(self, session_id: str) -> RecipeChatSession | None:
        raise NotImplementedError

    async def upsert(self, session: RecipeChatSession) -> None:
        raise NotImplementedError

    async def delete(self, session_id: str) -> None:
        raise NotImplementedError


@dataclass
class InMemoryRecipeChatSessionStore(RecipeChatSessionStore):
    _sessions: dict[str, RecipeChatSession] = field(default_factory=dict)
    _lock: asyncio.Lock = field(default_factory=asyncio.Lock)

    async def get(self, session_id: str) -> RecipeChatSession | None:
        async with self._lock:
            return self._sessions.get(session_id)

    async def upsert(self, session: RecipeChatSession) -> None:
        async with self._lock:
            self._sessions[session.session_id] = session

    async def delete(self, session_id: str) -> None:
        async with self._lock:
            self._sessions.pop(session_id, None)

    async def cleanup_expired(self) -> int:
        now = _utcnow()
        removed = 0
        async with self._lock:
            expired_keys = [
                sid for sid, s in self._sessions.items()
                if s.expires_at <= now or s.is_expired
            ]
            for sid in expired_keys:
                self._sessions.pop(sid, None)
                removed += 1
        return removed


# ---------------------------------------------------------------------------
# Main service
# ---------------------------------------------------------------------------

class RecipeChatService:
    """
    Temporary per-result-page recipe chat service.

    Design choices:
      - Sessions are ephemeral and not persisted long-term.
      - A session must be explicitly started before chat begins.
      - /message will NOT auto-create a session.
      - Sessions expire after 25 minutes of inactivity.
      - expire_session() deletes the session from the store.
    """

    def __init__(
        self,
        session_store: RecipeChatSessionStore | None = None,
        client: AsyncOpenAI | None = None,
        model: str = _QWEN_MODEL,
    ) -> None:
        self.session_store = session_store or InMemoryRecipeChatSessionStore()
        self.model = model
        self.client = client or self._build_client()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def start_new_session(
            self,
            session_id: str,
            recipe_context: RecipeChatContext,
        ) -> RecipeChatSession:
            await self._cleanup_if_supported()

            now = _utcnow()
            session = RecipeChatSession(
                session_id=session_id,
                recipe_id=recipe_context.recipe_id,
                created_at=now,
                last_activity_at=now,
                expires_at=now + timedelta(minutes=_SESSION_TTL_MINUTES),
                is_expired=False,
                context=recipe_context,
                message_history=[],
                message_count=0,
            )
            await self.session_store.upsert(session)
            return session

    async def send_message(self, request: RecipeChatRequest) -> RecipeChatResponse:
        await self._cleanup_if_supported()

        user_message = request.user_message.strip()
        if not user_message:
            return RecipeChatResponse(
                session_id=request.session_id,
                assistant_message="Please enter a message before sending.",
                error_code="EMPTY_MESSAGE",
                error_message="User message is empty.",
            )

        now = _utcnow()
        session = await self.session_store.get(request.session_id)

        # IMPORTANT:
        # No auto-create here. Session must already exist.
        if session is None:
            return RecipeChatResponse(
                session_id=request.session_id,
                assistant_message="This chat session is no longer available. Please start a new conversation.",
                is_expired=True,
                fallback_used=False,
                error_code="SESSION_NOT_FOUND",
                error_message="Chat session was not found or has already been removed.",
            )

        if self._is_expired(session, now):
            await self.session_store.delete(request.session_id)
            return RecipeChatResponse(
                session_id=request.session_id,
                assistant_message="This chat session has expired. Please start a new conversation.",
                is_expired=True,
                expires_at=session.expires_at,
                fallback_used=False,
                error_code="SESSION_EXPIRED",
                error_message="Chat session expired due to inactivity.",
            )

        # Keep latest context in case the result page refreshed richer data.
        session.context = request.recipe_context
        session.recipe_id = request.recipe_context.recipe_id

        session.message_history.append(
            ChatMessage(role="user", content=user_message, timestamp=now)
        )
        session.message_history = _trim_history(session.message_history, _MAX_HISTORY_TURNS)
        session.message_count += 1


        logger.info(
            "Recipe chat request received | session_id=%s | message_len=%d | recipe_id=%s | has_session=%s",
            request.session_id,
            len(user_message),
            request.recipe_context.recipe_id,
            session is not None,
        )
        
        try:
            prompt = self._build_chat_prompt(
                context=session.context,
                history=session.message_history,
                user_message=user_message,
            )

            logger.info(
                "Calling recipe chat LLM | model=%s | prompt_chars=%d | history_count=%d | weights=%d | nutrients=%d",
                self.model,
                len(prompt),
                len(session.message_history),
                len(session.context.weights),
                len(session.context.nutrient_analysis),
            )
            assistant_message = await self._call_llm(prompt)
            fallback_used = False
        except Exception as exc:  # noqa: BLE001
            logger.exception(
                "Recipe chat LLM call failed | model=%s | base_url=%s | using_fallback=True",
                self.model,
                _QWEN_BASE_URL,
            )
            assistant_message = self._fallback_message(session.context, user_message)
            fallback_used = True

        assistant_time = _utcnow()
        session.message_history.append(
            ChatMessage(role="assistant", content=assistant_message, timestamp=assistant_time)
        )
        session.message_history = _trim_history(session.message_history, _MAX_HISTORY_TURNS)

        session.last_activity_at = assistant_time
        session.expires_at = assistant_time + timedelta(minutes=_SESSION_TTL_MINUTES)
        session.is_expired = False

        await self.session_store.upsert(session)

        return RecipeChatResponse(
            session_id=session.session_id,
            assistant_message=assistant_message,
            is_expired=False,
            expires_at=session.expires_at,
            fallback_used=fallback_used,
        )

    async def expire_session(self, session_id: str) -> None:
        """
        Hard-delete the temporary session.

        This matches the product goal:
          - current-page-only conversation
          - no long-term storage
          - close means close
        """
        await self.session_store.delete(session_id)

    async def delete_session(self, session_id: str) -> None:
        await self.session_store.delete(session_id)

    # ------------------------------------------------------------------
    # Prompt building
    # ------------------------------------------------------------------

    def _build_chat_prompt(
        self,
        context: RecipeChatContext,
        history: list[ChatMessage],
        user_message: str,
    ) -> str:
        trimmed_context = self._trim_context(context)

        history_lines: list[str] = []
        # Exclude the last element (current user message already in history)
        # to avoid sending it twice in the prompt
        prior_history = history[-_MAX_HISTORY_TURNS:-1]
        for msg in prior_history:
            role = "User" if msg.role == "user" else "Assistant"
            history_lines.append(f"{role}: {msg.content}")

        history_block = "\n".join(history_lines) if history_lines else "No previous conversation."

        return (
            "You are Kibo, a helpful chat assistant for a pet fresh-food recipe result.\n\n"
            "RULES:\n"
            "1. Only answer using the provided recipe context and recent conversation.\n"
            "2. Do not invent ingredients, nutrient values, weights, or medical facts.\n"
            "3. Do not give diagnoses or replace veterinary advice.\n"
            "4. If the user asks something not supported by the recipe context, say so clearly.\n"
            "5. Keep answers practical, clear, and reasonably concise.\n"
            "6. When discussing substitutions, explain that swaps may change nutrient balance.\n"
            "7. Treat ingredient and nutrient data as the source of truth.\n\n"
            f"[RECIPE CHAT CONTEXT]\n{trimmed_context}\n\n"
            f"[RECENT CHAT HISTORY]\n{history_block}\n\n"
            f"[CURRENT USER QUESTION]\n{user_message}\n"
        )

    def _trim_context(self, context: RecipeChatContext) -> str:
        pet_profile = {
            k: v
            for k, v in context.pet_profile.items()
            if k in {
                "species",
                "breed",
                "life_stage",
                "size_class",
                "body_weight_kg",
                "weight_kg",
                "age_months",
                "daily_calories_kcal",
                "target_calories_kcal",
                "activity_level",
                "allergies",
                "health_conditions",
            }
            and v not in (None, "", [], {})
        }

        weights = [
            self._normalize_weight_item(item)
            for item in context.weights[:_MAX_WEIGHTS_FOR_LLM]
        ]
        nutrients = [
            self._normalize_nutrient_item(item)
            for item in self._select_chat_nutrients(context.nutrient_analysis)[:_MAX_NUTRIENTS_FOR_LLM]
        ]

        payload = {
            "recipe_id": context.recipe_id,
            "mode": context.mode,
            "pet_profile": pet_profile,
            "total_weight_grams": context.total_weight_grams,
            "objective_value": context.objective_value,
            "weights": weights,
            "key_nutrients": nutrients,
            "used_supplements": context.used_supplements[:_MAX_USED_SUPPLEMENTS],
            "warnings": context.warnings[:_MAX_WARNINGS],
        }

        return json.dumps(payload, ensure_ascii=False, indent=2)

    def _select_chat_nutrients(self, nutrient_analysis: list[dict[str, Any]]) -> list[dict[str, Any]]:
        if not nutrient_analysis:
            return []

        priority_names = {
            "protein",
            "fat",
            "calcium",
            "phosphorus",
            "calcium : phosphorus ratio",
            "ca:p",
            "epa + dha",
            "omega-6 : omega-3 ratio",
            "zinc",
            "iodine",
            "vitamin e",
            "organ percentage",
        }

        selected: list[dict[str, Any]] = []
        seen: set[str] = set()

        def key_of(item: dict[str, Any]) -> str:
            display = str(
                item.get("display_name")
                or item.get("nutrient_name")
                or item.get("name")
                or ""
            ).strip().lower()
            nutrient_id = str(item.get("nutrient_id") or "").strip().lower()
            return display or nutrient_id

        for item in nutrient_analysis:
            key = key_of(item)
            if key in priority_names and key not in seen:
                selected.append(item)
                seen.add(key)

        for item in nutrient_analysis:
            key = key_of(item)
            if key not in seen:
                selected.append(item)
                seen.add(key)
            if len(selected) >= _MAX_NUTRIENTS_FOR_LLM:
                break

        return selected

    @staticmethod
    def _normalize_weight_item(item: dict[str, Any]) -> dict[str, Any]:
        return {
            "ingredient_id": item.get("ingredient_id") or item.get("id"),
            "ingredient_name": item.get("ingredient_name") or item.get("name"),
            "grams": item.get("grams") or item.get("weight_grams") or item.get("weight"),
            "pct_of_recipe": item.get("pct_of_recipe") or item.get("percentage"),
            "food_group": item.get("food_group"),
        }

    @staticmethod
    def _normalize_nutrient_item(item: dict[str, Any]) -> dict[str, Any]:
        return {
            "nutrient_id": item.get("nutrient_id"),
            "display_name": item.get("display_name") or item.get("nutrient_name") or item.get("name"),
            "value": item.get("value"),
            "unit": item.get("unit"),
            "status": item.get("status"),
            "min_target": item.get("min_target") or item.get("min_required"),
            "max_target": item.get("max_target") or item.get("max_allowed"),
        }

    # ------------------------------------------------------------------
    # LLM / fallback
    # ------------------------------------------------------------------

    async def _call_llm(self, prompt: str) -> str:
        if self.client is None:
            raise RuntimeError("LLM client is not available")

        response = await self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": "You are Kibo, a pet recipe result chat assistant."},
                {"role": "user", "content": prompt},
            ],
            temperature=_DEFAULT_TEMPERATURE,
            max_tokens=_MAX_RESPONSE_TOKENS,
            extra_body={"enable_thinking": False},
        )

        content = response.choices[0].message.content or ""
        return content.strip() or "I couldn't generate a useful reply this time."

    def _fallback_message(self, context: RecipeChatContext, user_message: str) -> str:
        recipe_name = context.recipe_id or "this recipe"

        lowered = user_message.lower()
        if "replace" in lowered or "swap" in lowered or "substitute" in lowered:
            return (
                f"I can't fully evaluate substitutions for {recipe_name} right now. "
                "In general, changing ingredients can alter the nutrient balance, so any substitution should be re-checked against the recipe analysis."
            )

        if context.warnings:
            return (
                "I'm having trouble generating a full answer right now. "
                f"One thing to keep in mind is that this recipe already has noted warnings: {', '.join(context.warnings[:3])}."
            )

        return (
            "I'm having trouble answering that right now. "
            "Please try again in a moment, or start a new chat if this session has expired."
        )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _is_expired(session: RecipeChatSession, now: datetime) -> bool:
        return session.is_expired or session.expires_at <= now

    @staticmethod
    def _build_client() -> AsyncOpenAI | None:
        if not _QWEN_CHAT_API_KEY:
            logger.warning("QWEN_CHAT_API_KEY is not configured. Recipe chat will use fallback responses.")
            return None

        logger.info(
            "Initializing recipe chat LLM client | model=%s | base_url=%s | api_key_present=%s",
            _QWEN_MODEL,
            _QWEN_BASE_URL,
            bool(_QWEN_CHAT_API_KEY),
        )

        return AsyncOpenAI(
            api_key=_QWEN_CHAT_API_KEY,
            base_url=_QWEN_BASE_URL,
        )

    async def _cleanup_if_supported(self) -> None:
        cleanup = getattr(self.session_store, "cleanup_expired", None)
        if cleanup is not None:
            try:
                await cleanup()
            except Exception as exc:  # noqa: BLE001
                logger.warning("Recipe chat cleanup_expired failed: %s", exc)


# ---------------------------------------------------------------------------
# Utilities
# ---------------------------------------------------------------------------

def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _trim_history(messages: list[ChatMessage], max_messages: int) -> list[ChatMessage]:
    if len(messages) <= max_messages:
        return messages
    return messages[-max_messages:]


# ---------------------------------------------------------------------------
# Dependency factory
# ---------------------------------------------------------------------------

_default_service: RecipeChatService | None = None


def get_recipe_chat_service() -> RecipeChatService:
    global _default_service
    if _default_service is None:
        _default_service = RecipeChatService()
    return _default_service