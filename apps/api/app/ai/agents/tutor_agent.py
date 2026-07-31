from __future__ import annotations

from collections.abc import AsyncGenerator
from typing import Any

from apps.api.app.ai.llm.router import llm_router
from apps.api.app.ai.memory.conversation_memory import ConversationMemory
from apps.api.app.ai.prompts.manager import prompt_manager
from apps.api.app.ai.context.manager import context_manager
from apps.api.app.core.config import settings


class TutorAgent:
    def __init__(self, user_id: str, conversation_id: str | None = None) -> None:
        self.user_id = user_id
        self.conversation_id = conversation_id
        self.memory = ConversationMemory(user_id, conversation_id, prefix="tutor")

    async def tutor(
        self,
        topic: str,
        message: str,
        stream: bool = True,
    ) -> AsyncGenerator[dict[str, Any], None]:
        conversation = await self.memory.get_or_create()
        self.conversation_id = conversation["id"]

        await self.memory.add_message({"role": "user", "content": message})
        history = await self.memory.get_history()
        context_data = await context_manager.build_context(self.user_id, {"topic": topic})
        system_prompt = prompt_manager.render("tutor_socratic", {"topic": topic, **context_data})

        messages: list[dict[str, Any]] = [
            {"role": "system", "content": system_prompt},
        ]
        for h in history[-20:]:
            messages.append({"role": h["role"], "content": h["content"]})

        if stream:
            collected = ""
            async for event in llm_router.complete_stream(messages):
                if event.type == "token":
                    collected += event.token
                    yield {"type": "token", "content": event.token}
                elif event.type == "done":
                    await self.memory.add_message({"role": "assistant", "content": collected})
                    yield {"type": "done", "content": collected}
                elif event.type == "error":
                    yield {"type": "error", "content": event.error}
        else:
            response = await llm_router.complete(messages)
            await self.memory.add_message({"role": "assistant", "content": response.content})
            yield {"type": "done", "content": response.content}

    async def get_conversation_id(self) -> str:
        if not self.conversation_id:
            conv = await self.memory.get_or_create()
            self.conversation_id = conv["id"]
        return self.conversation_id