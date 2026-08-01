from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from apps.api.app.ai.agents.interview_agent import InterviewAgent
from apps.api.app.ai.schemas.models import (
    InterviewEvaluateResponse,
    InterviewStartResponse,
)


@pytest.fixture
def mock_llm_router():
    with patch("apps.api.app.ai.agents.interview_agent.llm_router") as mock:
        mock.complete = AsyncMock()

        async def fake_complete(*args, **kwargs):
            messages = args[0] if args else kwargs.get("messages", [])
            if messages and messages[0]["content"].startswith("You are conducting"):
                return MagicMock(
                    content="What is a closure?",
                    model="gpt-4o",
                    usage={"prompt_tokens": 40, "completion_tokens": 80},
                )
            return MagicMock(
                content='{"strengths": ["Clear example"], "improvements": ["Add edge cases"], "score": 7, "next_question": "Explain this further.", "is_complete": false}',
                model="gpt-4o",
                usage={"prompt_tokens": 40, "completion_tokens": 80},
            )

        mock.complete.side_effect = fake_complete
        yield mock


@pytest.fixture
def mock_memory():
    with patch("apps.api.app.ai.agents.interview_agent.ConversationMemory") as mock_cls:
        mock_memory = MagicMock()
        mock_memory.get_or_create = AsyncMock(return_value={
            "id": "interview-1",
            "user_id": "user-1",
            "title": "Interview session",
            "created_at": "",
            "updated_at": "",
            "message_count": 0,
            "metadata": {},
        })
        mock_memory.add_message = AsyncMock()
        mock_memory.get_history = AsyncMock(return_value=[])
        mock_memory.get_metadata = AsyncMock(return_value={
            "topic": "Python",
            "difficulty": "intermediate",
            "current_question": 1,
        })
        mock_memory.save_metadata = AsyncMock()
        mock_cls.return_value = mock_memory
        yield mock_memory


@pytest.mark.asyncio
async def test_interview_start(mock_llm_router, mock_memory):
    agent = InterviewAgent(user_id="user-1")
    response = await agent.start(conversation_id=None)

    assert isinstance(response, InterviewStartResponse)
    assert response.question != ""
    assert response.question_number == 1
    assert response.total_questions == InterviewAgent.TOTAL_QUESTIONS


@pytest.mark.asyncio
async def test_interview_evaluate(mock_llm_router, mock_memory):
    agent = InterviewAgent(user_id="user-1")
    response = await agent.evaluate(
        conversation_id="interview-1",
        question_index=0,
        answer="A closure is a function that remembers its enclosing scope.",
    )

    assert isinstance(response, InterviewEvaluateResponse)
    assert response.score is not None
