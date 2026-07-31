from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from apps.api.app.ai.agents.tutor_agent import TutorAgent
from apps.api.app.ai.schemas.models import TutorResponse


@pytest.fixture
def mock_llm_router():
    with patch("apps.api.app.ai.agents.tutor_agent.llm_router") as mock:
        mock.generate = AsyncMock()
        mock.generate.return_value = MagicMock(
            content="Let me guide you through this step by step...",
            model="gpt-4o",
            usage={"prompt_tokens": 50, "completion_tokens": 100},
        )
        yield mock


@pytest.mark.asyncio
async def test_tutor_agent_basic(mock_llm_router):
    agent = TutorAgent(user_id="user-1")
    response = await agent.tutor(
        topic="Python decorators",
        question="How do decorators work?",
        conversation_id=None,
    )

    assert isinstance(response, TutorResponse)
    assert "guide" in response.response.lower() or "step" in response.response.lower()


@pytest.mark.asyncio
async def test_tutor_agent_socratic_method(mock_llm_router):
    agent = TutorAgent(user_id="user-1")
    response = await agent.tutor(
        topic="Binary trees",
        question="What is tree traversal?",
        conversation_id=None,
    )

    assert response.topic == "Binary trees"
    assert response.conversation_id is not None


@pytest.mark.asyncio
async def test_tutor_agent_with_history(mock_llm_router):
    with patch("apps.api.app.ai.agents.tutor_agent.conversation_memory") as mock_memory:
        mock_memory.get_or_create = AsyncMock()
        mock_memory.get_or_create.return_value = ("conv-789", [])

        agent = TutorAgent(user_id="user-1")
        response = await agent.tutor(
            topic="Recursion",
            question="Explain base cases",
            conversation_id="conv-789",
        )

        assert response.conversation_id == "conv-789"