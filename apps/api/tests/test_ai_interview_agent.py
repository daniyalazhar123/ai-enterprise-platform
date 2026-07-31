from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from apps.api.app.ai.agents.interview_agent import InterviewAgent
from apps.api.app.ai.schemas.models import InterviewFeedback, InterviewStartResponse


@pytest.fixture
def mock_llm_router():
    with patch("apps.api.app.ai.agents.interview_agent.llm_router") as mock:
        mock.generate = AsyncMock()

        async def fake_generate(*args, **kwargs):
            return MagicMock(
                content='[{"question":"What is a closure?","category":"Python","difficulty":"medium","hints":["Think about scope"]}]',
                model="gpt-4o",
                usage={"prompt_tokens": 40, "completion_tokens": 80},
            )

        mock.generate.side_effect = fake_generate
        yield mock


@pytest.mark.asyncio
async def test_interview_start(mock_llm_router):
    agent = InterviewAgent(user_id="user-1")
    response = await agent.start(conversation_id=None)

    assert isinstance(response, InterviewStartResponse)
    assert len(response.questions) > 0
    assert response.questions[0].category == "Python"


@pytest.mark.asyncio
async def test_interview_evaluate(mock_llm_router):
    agent = InterviewAgent(user_id="user-1")
    response = await agent.evaluate(
        conversation_id="interview-1",
        question_index=0,
        answer="A closure is a function that remembers its enclosing scope.",
    )

    assert isinstance(response, InterviewFeedback)
    assert response.score is not None or response.feedback is not None


@pytest.mark.asyncio
async def test_interview_agent_user_context(mock_llm_router):
    with patch("apps.api.app.ai.agents.interview_agent.context_manager") as mock_context:
        mock_context.get_progress = AsyncMock()
        mock_context.get_progress.return_value = {
            "current_chapter": "Functions",
            "completed_modules": ["Basics", "Data Types"],
        }

        agent = InterviewAgent(user_id="user-1")
        response = await agent.start(conversation_id=None)

        assert isinstance(response, InterviewStartResponse)