from __future__ import annotations

import json
from typing import Any

from fastapi import Request
from sse_starlette.sse import EventSourceResponse

from apps.api.app.ai.agents.chat_agent import ChatAgent
from apps.api.app.ai.agents.interview_agent import InterviewAgent
from apps.api.app.ai.agents.quiz_agent import QuizAgent
from apps.api.app.ai.agents.tutor_agent import TutorAgent
from apps.api.app.ai.schemas.models import (
    ChatRequest,
    StreamChunk,
    TutorRequest,
)
from apps.api.app.core.auth import get_current_user_optional


async def chat_stream(
    request: Request,
    body: ChatRequest,
) -> EventSourceResponse:
    user = await get_current_user_optional(request)
    user_id = user.id if user else "anonymous"

    agent = ChatAgent(user_id=user_id)

    async def event_generator():
        async for chunk in agent.run_stream(
            message=body.message,
            conversation_id=body.conversation_id,
            use_rag=body.use_rag,
        ):
            if await request.is_disconnected():
                break

            if isinstance(chunk, StreamChunk):
                yield {
                    "event": chunk.event_type,
                    "data": chunk.model_dump_json(),
                }
            elif isinstance(chunk, dict):
                yield {
                    "event": chunk.get("event", "message"),
                    "data": json.dumps(chunk),
                }
            else:
                yield {
                    "event": "message",
                    "data": json.dumps({"content": str(chunk)}),
                }

        yield {"event": "done", "data": "{}"}

    return EventSourceResponse(event_generator())


async def tutor_stream(
    request: Request,
    body: TutorRequest,
) -> EventSourceResponse:
    user = await get_current_user_optional(request)
    user_id = user.id if user else "anonymous"

    agent = TutorAgent(user_id=user_id)

    async def event_generator():
        async for chunk in agent.tutor_stream(
            topic=body.topic,
            question=body.question,
            conversation_id=body.conversation_id,
        ):
            if await request.is_disconnected():
                break

            if isinstance(chunk, StreamChunk):
                yield {
                    "event": chunk.event_type,
                    "data": chunk.model_dump_json(),
                }
            else:
                yield {
                    "event": "message",
                    "data": json.dumps({"content": str(chunk)}),
                }

        yield {"event": "done", "data": "{}"}

    return EventSourceResponse(event_generator())


async def quiz_generate_stream(
    request: Request,
    body: dict[str, Any],
) -> EventSourceResponse:
    user = await get_current_user_optional(request)
    user_id = user.id if user else "anonymous"

    agent = QuizAgent(user_id=user_id)

    async def event_generator():
        async for chunk in agent.generate_stream(
            topic=body.get("topic", ""),
            num_questions=body.get("num_questions", 5),
            difficulty=body.get("difficulty", "medium"),
            conversation_id=body.get("conversation_id"),
        ):
            if await request.is_disconnected():
                break

            if isinstance(chunk, StreamChunk):
                yield {
                    "event": chunk.event_type,
                    "data": chunk.model_dump_json(),
                }
            else:
                yield {
                    "event": "message",
                    "data": json.dumps({"content": str(chunk)}),
                }

        yield {"event": "done", "data": "{}"}

    return EventSourceResponse(event_generator())