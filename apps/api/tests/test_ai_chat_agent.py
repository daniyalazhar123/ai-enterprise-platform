from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from apps.api.app.ai.agents.chat_agent import ChatAgent
from apps.api.app.ai.schemas.models import ChatMessage, SourceCitation


@pytest.fixture
def mock_llm_router():
    with patch("apps.api.app.ai.agents.chat_agent.llm_router") as mock:
        mock.generate = AsyncMock()
        mock.generate.return_value = MagicMock(
            content="Test response",
            model="gpt-4o",
            usage={"prompt_tokens": 10, "completion_tokens": 20},
        )
        yield mock


@pytest.fixture
def mock_conversation_memory():
    with patch("apps.api.app.ai.agents.chat_agent.conversation_memory") as mock:
        mock.get_or_create = AsyncMock()
        mock.get_or_create.return_value = ("conv-123", [])
        mock.add_message = AsyncMock()
        yield mock


@pytest.mark.asyncio
async def test_chat_agent_basic(mock_llm_router, mock_conversation_memory):
    agent = ChatAgent(user_id="user-1")
    response = await agent.run(message="Hello", conversation_id=None)

    assert response.message.content == "Test response"
    assert response.message.role == "assistant"
    assert response.conversation_id == "conv-123"
    assert response.model == "gpt-4o"


@pytest.mark.asyncio
async def test_chat_agent_with_rag(mock_llm_router, mock_conversation_memory):
    with patch("apps.api.app.ai.agents.chat_agent.rag_pipeline") as mock_rag:
        mock_rag.retrieve = AsyncMock()
        mock_rag.retrieve.return_value = (
            [SourceCitation(id="src-1", title="Test", content="Test content", score=0.95, source="pdf")],
            "Retrieved context",
        )
        mock_rag.augment = AsyncMock()
        mock_rag.augment.return_value = "Augmented query"

        agent = ChatAgent(user_id="user-1")
        response = await agent.run(message="Hello", conversation_id=None, use_rag=True)

        assert response.message.content == "Test response"
        mock_rag.retrieve.assert_called_once()
        mock_rag.augment.assert_called_once()


@pytest.mark.asyncio
async def test_chat_agent_existing_conversation(mock_llm_router, mock_conversation_memory):
    mock_conversation_memory.get_or_create.return_value = ("conv-456", [
        ChatMessage(role="user", content="Previous question"),
        ChatMessage(role="assistant", content="Previous answer"),
    ])

    agent = ChatAgent(user_id="user-1")
    response = await agent.run(message="Follow up", conversation_id="conv-456")

    assert response.conversation_id == "conv-456"
    assert response.message.content == "Test response"