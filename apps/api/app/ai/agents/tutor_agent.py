from __future__ import annotations

from collections.abc import AsyncGenerator
from typing import Any

from apps.api.app.ai.llm.router import llm_router
from apps.api.app.ai.memory.conversation_memory import ConversationMemory
from apps.api.app.ai.prompts.manager import prompt_manager
from apps.api.app.ai.context.manager import context_manager
from apps.api.app.ai.schemas.models import StreamChunk, SourceCitation, TutorResponse
from apps.api.app.core.config import settings


class TutorAgent:
    def __init__(self, user_id: str, conversation_id: str | None = None) -> None:
        self.user_id = user_id
        self.conversation_id = conversation_id
        self.memory = ConversationMemory(user_id, conversation_id, prefix="tutor")

    async def _get_or_create_conversation(self, conversation_id: str | None) -> str:
        if conversation_id:
            self.conversation_id = conversation_id
            self.memory = ConversationMemory(self.user_id, conversation_id, prefix="tutor")

        conversation = await self.memory.get_or_create()
        self.conversation_id = conversation["id"]
        return self.conversation_id

    async def _build_messages(self, topic: str, question: str) -> list[dict[str, Any]]:
        history = await self.memory.get_history()
        context_data = await context_manager.build_context(self.user_id, {"topic": topic})
        system_prompt = prompt_manager.render("tutor_socratic", {"topic": topic, **context_data})

        messages: list[dict[str, Any]] = [
            {"role": "system", "content": system_prompt},
        ]
        for h in history[-settings.MAX_CONVERSATION_HISTORY:]:
            messages.append({"role": h["role"], "content": h["content"]})

        if not question:
            question = f"Help me understand {topic}."

        return messages

    async def tutor(
        self,
        topic: str,
        question: str = "",
        conversation_id: str | None = None,
    ) -> TutorResponse:
        await self._get_or_create_conversation(conversation_id)

        question_text = question or f"Help me understand {topic}."
        await self.memory.add_message({"role": "user", "content": question_text})

        messages = await self._build_messages(topic, question_text)
        response = await llm_router.complete(messages)
        await self.memory.add_message({"role": "assistant", "content": response.content})

        return TutorResponse(
            conversation_id=self.conversation_id or "",
            topic=topic,
            question=question_text,
            response=response.content,
            citations=[],
        )

    async def tutor_stream(
        self,
        topic: str,
        question: str = "",
        conversation_id: str | None = None,
    ) -> AsyncGenerator[StreamChunk, None]:
        await self._get_or_create_conversation(conversation_id)

        question_text = question or f"Help me understand {topic}."
        await self.memory.add_message({"role": "user", "content": question_text})

        messages = await self._build_messages(topic, question_text)

        collected = ""
        async for event in llm_router.complete_stream(messages):
            if event.type == "token":
                collected += event.token
                yield StreamChunk(event_type="token", token=event.token, content=event.token)
            elif event.type == "done":
                await self.memory.add_message({"role": "assistant", "content": collected})
                yield StreamChunk(
                    event_type="done",
                    content=collected,
                    finish_reason=event.finish_reason,
                )
            elif event.type == "error":
                yield StreamChunk(event_type="error", content=event.error or "Tutoring error")

    async def get_conversation_id(self) -> str:
        if not self.conversation_id:
            conv = await self.memory.get_or_create()
            self.conversation_id = conv["id"]
        return self.conversation_id
