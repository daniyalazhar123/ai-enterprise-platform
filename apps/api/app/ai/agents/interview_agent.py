from __future__ import annotations

import json
from typing import Any
from uuid import uuid4

from apps.api.app.ai.llm.router import llm_router
from apps.api.app.ai.memory.conversation_memory import ConversationMemory
from apps.api.app.ai.prompts.manager import prompt_manager
from apps.api.app.core.config import settings


class InterviewAgent:
    TOTAL_QUESTIONS = 8

    def __init__(self, user_id: str, session_id: str | None = None) -> None:
        self.user_id = user_id
        self.session_id = session_id or str(uuid4())
        self.memory = ConversationMemory(user_id, self.session_id, prefix="interview")

    async def start_interview(self, topic: str, difficulty: str = "intermediate") -> dict[str, Any]:
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

        return {
            "session_id": self.session_id,
            "question": response.content,
            "question_number": 1,
            "total_questions": self.TOTAL_QUESTIONS,
        }

    async def submit_answer(self, answer: str) -> dict[str, Any]:
        await self.memory.add_message({"role": "user", "content": answer})
        metadata = await self.memory.get_metadata()
        current_q = metadata.get("current_question", 1)
        history = await self.memory.get_history()

        prompt = prompt_manager.render("interview_evaluate", {
            "current_question": current_q,
            "total_questions": self.TOTAL_QUESTIONS,
        })

        messages: list[dict[str, Any]] = [
            {"role": "system", "content": prompt},
        ]
        for h in history[-20:]:
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

        return {
            "session_id": self.session_id,
            "strengths": result.get("strengths", []),
            "improvements": result.get("improvements", []),
            "score": result.get("score", 5),
            "next_question": result.get("next_question") if not is_complete else None,
            "is_complete": is_complete,
        }


interview_agent = InterviewAgent