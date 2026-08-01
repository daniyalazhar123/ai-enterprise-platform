from __future__ import annotations

import json
from typing import Any
from uuid import uuid4

from apps.api.app.ai.llm.router import llm_router
from apps.api.app.ai.memory.conversation_memory import ConversationMemory
from apps.api.app.ai.prompts.manager import prompt_manager
from apps.api.app.ai.schemas.models import (
    InterviewEvaluateResponse,
    InterviewStartResponse,
)
from apps.api.app.core.config import settings


class InterviewAgent:
    TOTAL_QUESTIONS = 8

    def __init__(self, user_id: str, session_id: str | None = None) -> None:
        self.user_id = user_id
        self.session_id = session_id or str(uuid4())
        self.memory = ConversationMemory(user_id, self.session_id, prefix="interview")

    def _use_conversation(self, conversation_id: str) -> None:
        if conversation_id:
            self.session_id = conversation_id
            self.memory = ConversationMemory(self.user_id, conversation_id, prefix="interview")

    async def start(
        self,
        conversation_id: str | None = None,
        topic: str | None = None,
        difficulty: str = "intermediate",
    ) -> InterviewStartResponse:
        if conversation_id:
            self._use_conversation(conversation_id)
            metadata = await self.memory.get_metadata()
            topic = topic or metadata.get("topic", "General software engineering")
            difficulty = metadata.get("difficulty", difficulty)
        else:
            topic = topic or "General software engineering"

        await self.memory.get_or_create()

        prompt = prompt_manager.render("interview_start", {
            "topic": topic,
            "difficulty": difficulty,
            "total_questions": self.TOTAL_QUESTIONS,
        })

        response = await llm_router.complete(
            messages=[{"role": "system", "content": prompt}],
        )

        await self.memory.add_message({"role": "assistant", "content": response.content})
        await self.memory.save_metadata({
            "topic": topic,
            "difficulty": difficulty,
            "current_question": 1,
        })

        return InterviewStartResponse(
            session_id=self.session_id,
            question=response.content,
            question_number=1,
            total_questions=self.TOTAL_QUESTIONS,
        )

    async def evaluate(
        self,
        conversation_id: str,
        question_index: int = 0,
        answer: str = "",
    ) -> InterviewEvaluateResponse:
        self._use_conversation(conversation_id)
        await self.memory.get_or_create()

        await self.memory.add_message({"role": "user", "content": answer})
        metadata = await self.memory.get_metadata()
        current_q = metadata.get("current_question", question_index + 1)
        history = await self.memory.get_history()

        prompt = prompt_manager.render("interview_evaluate", {
            "difficulty": metadata.get("difficulty", "intermediate"),
            "current_question": current_q,
            "total_questions": self.TOTAL_QUESTIONS,
        })

        messages: list[dict[str, Any]] = [
            {"role": "system", "content": prompt},
        ]
        for h in history[-settings.MAX_CONVERSATION_HISTORY:]:
            messages.append({"role": h["role"], "content": h["content"]})

        response = await llm_router.complete(messages)

        try:
            raw = response.content
            if raw.startswith("```json"):
                raw = raw[7:]
            if raw.endswith("```"):
                raw = raw[:-3]
            result = json.loads(raw.strip())
        except (json.JSONDecodeError, ValueError):
            result = {
                "strengths": [],
                "improvements": [],
                "score": 5,
                "next_question": response.content,
                "is_complete": current_q >= self.TOTAL_QUESTIONS,
            }

        is_complete = result.get("is_complete", current_q >= self.TOTAL_QUESTIONS)

        if not is_complete:
            next_q = result.get("next_question", "")
            await self.memory.add_message({"role": "assistant", "content": next_q})
            await self.memory.save_metadata({
                **metadata,
                "current_question": current_q + 1,
            })
        else:
            await self.memory.save_metadata({
                **metadata,
                "current_question": current_q,
                "completed": True,
            })

        return InterviewEvaluateResponse(
            session_id=self.session_id,
            strengths=result.get("strengths", []),
            improvements=result.get("improvements", []),
            score=result.get("score", 5),
            next_question=result.get("next_question") if not is_complete else None,
            is_complete=is_complete,
        )

    async def start_interview(self, topic: str, difficulty: str = "intermediate") -> InterviewStartResponse:
        return await self.start(topic=topic, difficulty=difficulty)

    async def submit_answer(self, answer: str) -> InterviewEvaluateResponse:
        return await self.evaluate(conversation_id=self.session_id, answer=answer)


interview_agent = InterviewAgent
