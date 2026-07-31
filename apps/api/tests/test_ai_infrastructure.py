from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from apps.api.app.ai.llm.router import LlmRouter
from apps.api.app.ai.llm.base import ModelConfig, ProviderResponse
from apps.api.app.ai.rag.hybrid_search import HybridSearchService
from apps.api.app.ai.rag.pipeline import RagPipeline
from apps.api.app.ai.memory.conversation_memory import ConversationMemory
from apps.api.app.ai.tools.registry import ToolRegistry
from apps.api.app.ai.prompts.manager import PromptManager
from apps.api.app.ai.context.manager import ContextManager


class TestLlmRouter:
    @pytest.mark.asyncio
    async def test_router_with_no_providers(self):
        router = LlmRouter()
        with pytest.raises(Exception):
            await router.generate(prompt="test", system_prompt="test")


class TestHybridSearch:
    @pytest.mark.asyncio
    async def test_hybrid_search_empty_query(self):
        service = HybridSearchService()
        with patch("apps.api.app.ai.rag.hybrid_search.qdrant_service") as mock_q:
            mock_q.search = AsyncMock(return_value=[])
            with patch("apps.api.app.ai.rag.hybrid_search.pgvector_service") as mock_p:
                mock_p.search = AsyncMock(return_value=[])
                results = await service.search(query="test", top_k=5)
                assert results == []


class TestRagPipeline:
    @pytest.mark.asyncio
    async def test_pipeline_no_results(self):
        pipeline = RagPipeline()
        with patch("apps.api.app.ai.rag.pipeline.hybrid_search") as mock_hs:
            mock_hs.search = AsyncMock(return_value=[])
            citations, context = await pipeline.retrieve(query="test")
            assert citations == []
            assert context == ""


class TestConversationMemory:
    @pytest.mark.asyncio
    async def test_list_conversations_empty(self):
        memory = ConversationMemory()
        with patch("apps.api.app.ai.memory.conversation_memory.redis_client") as mock_redis:
            mock_redis.keys = MagicMock(return_value=[])
            results = await memory.list_conversations(user_id="user-1")
            assert results == []


class TestToolRegistry:
    def test_register_and_get_tool(self):
        registry = ToolRegistry()
        mock_tool = MagicMock()
        mock_tool.name = "test_tool"
        registry.register(mock_tool)
        assert registry.get_tool("test_tool") == mock_tool

    def test_get_nonexistent_tool(self):
        registry = ToolRegistry()
        assert registry.get_tool("nonexistent") is None

    def test_list_tools(self):
        registry = ToolRegistry()
        mock_tool = MagicMock()
        mock_tool.name = "test_tool"
        registry.register(mock_tool)
        tools = registry.list_tools()
        assert len(tools) == 1
        assert tools[0]["name"] == "test_tool"


class TestPromptManager:
    def test_get_template(self):
        manager = PromptManager()
        template = manager.get_template("chat_default")
        assert template is not None
        assert "assistant" in template.lower()

    def test_get_nonexistent_template(self):
        manager = PromptManager()
        template = manager.get_template("nonexistent")
        assert template is not None
        assert "helpful" in template.lower()

    def test_custom_template(self):
        manager = PromptManager()
        template = manager.get_template("tutor_socratic")
        assert template is not None
        assert "question" in template.lower()


class TestContextManager:
    @pytest.mark.asyncio
    async def test_get_progress_nonexistent(self):
        manager = ContextManager()
        with patch("apps.api.app.ai.context.manager.redis_client") as mock_redis:
            mock_redis.get = AsyncMock(return_value=None)
            progress = await manager.get_progress(user_id="user-1")
            assert progress["current_chapter"] is None

    @pytest.mark.asyncio
    async def test_update_progress(self):
        manager = ContextManager()
        with patch("apps.api.app.ai.context.manager.redis_client") as mock_redis:
            mock_redis.set = AsyncMock()
            await manager.update_progress(user_id="user-1", chapter="Chapter 1")
            mock_redis.set.assert_called_once()