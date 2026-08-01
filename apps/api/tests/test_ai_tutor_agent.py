from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from apps.api.app.ai.agents.tutor_agent import TutorAgent
from apps.api.app.ai.schemas.models import TutorResponse


@pytest.fixture
def mock_llm_router():
    with patch("apps.api.app.ai.agents.tutor_agent.llm_router") as mock:
        mock.complete = AsyncMock()
        mock.complete.return_value = MagicMock(
            content="Let me guide you through this step by step...",
            model="gpt-4o",
            usage={"prompt_tokens": 50, "completion_tokens": 100},
        )
        yield mock


@pytest.fixture
def mock_memory():
    with patch("apps.api.app.ai.agents.tutor_agent.ConversationMemory") as mock_cls:
        mock_memory = MagicMock()
        mock_memory.get_or_create = AsyncMock(return_value={
            "id": "conv-123",
            "user_id": "user-1",
            "title": "Tutor session",
            "created_at": "",
            "updated_at": "",
            "message_count": 0,
            "metadata": {},
        })
        mock_memory.add_message = AsyncMock()
        mock_memory.get_history = AsyncMock(return_value=[])
        mock_cls.return_value = mock_memory
        yield mock_memory


@pytest.mark.asyncio
async def test_tutor_agent_basic(mock_llm_router, mock_memory):
    agent = TutorAgent(user_id="user-1")
    response = await agent.tutor(
        topic="Python decorators",
        question="How do decorators work?",
        conversation_id=None,
    )

    assert isinstance(response, TutorResponse)
    assert "guide" in response.response.lower() or "step" in response.response.lower()


@pytest.mark.asyncio
async def test_tutor_agent_socratic_method(mock_llm_router, mock_memory):
    agent = TutorAgent(user_id="user-1")
    response = await agent.tutor(
        topic="Binary trees",
        question="What is tree traversal?",
        conversation_id=None,
    )

    assert response.topic == "Binary trees"
    assert response.conversation_id is not None


@pytest.mark.asyncio
async def test_tutor_agent_with_history(mock_llm_router, mock_memory):
    mock_memory.get_or_create.return_value = {
        "id": "conv-789",
        "user_id": "user-1",
        "title": "Tutor session",
        "created_at": "",
        "updated_at": "",
        "message_count": 1,
        "metadata": {},
    }

    agent = TutorAgent(user_id="user-1")
    response = await agent.tutor(
        topic="Recursion",
        question="Explain base cases",
        conversation_id="conv-789",
    )

    assert response.conversation_id == "conv-789"
