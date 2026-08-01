from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from apps.api.app.ai.agents.chat_agent import ChatAgent
from apps.api.app.ai.schemas.models import ChatMessage, SourceCitation


@pytest.fixture
def mock_llm_router():
    with patch("apps.api.app.ai.agents.chat_agent.llm_router") as mock:
        mock.complete = AsyncMock()
        mock.complete.return_value = MagicMock(
            content="Test response",
            model="gpt-4o",
            usage={"prompt_tokens": 10, "completion_tokens": 20},
        )
        yield mock


@pytest.fixture
def mock_conversation_memory():
    with patch("apps.api.app.ai.agents.chat_agent.ConversationMemory") as mock_cls:
        mock_memory = MagicMock()
        mock_memory.get_or_create = AsyncMock(return_value={
            "id": "conv-123",
            "user_id": "user-1",
            "title": "Chat session",
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
        mock_rag.search = AsyncMock(return_value=[
            {
                "id": "src-1",
                "title": "Test",
                "content": "Test content",
                "score": 0.95,
                "source": "pdf",
            }
        ])

        agent = ChatAgent(user_id="user-1")
        response = await agent.run(message="Hello", conversation_id=None, use_rag=True)

        assert response.message.content == "Test response"
        mock_rag.search.assert_called_once()


@pytest.mark.asyncio
async def test_chat_agent_existing_conversation(mock_llm_router, mock_conversation_memory):
    mock_conversation_memory.get_or_create.return_value = {
        "id": "conv-456",
        "user_id": "user-1",
        "title": "Chat session",
        "created_at": "",
        "updated_at": "",
        "message_count": 2,
        "metadata": {},
    }
    mock_conversation_memory.get_history.return_value = [
        {"role": "user", "content": "Previous question"},
        {"role": "assistant", "content": "Previous answer"},
    ]

    agent = ChatAgent(user_id="user-1")
    response = await agent.run(message="Follow up", conversation_id="conv-456")

    assert response.conversation_id == "conv-456"
    assert response.message.content == "Test response"
