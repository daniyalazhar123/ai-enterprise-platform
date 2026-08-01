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
            await router.complete(messages=[{"role": "user", "content": "test"}])


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
        with patch("apps.api.app.ai.memory.conversation_memory.get_redis") as mock_get_redis:
            mock_redis = AsyncMock()
            mock_redis.keys = AsyncMock(return_value=[])
            mock_get_redis.return_value = mock_redis
            results = await memory.list_conversations(user_id="user-1")
            assert results == []


class TestToolRegistry:
    def test_register_and_get_tool(self):
        registry = ToolRegistry()
        mock_tool = MagicMock()
        mock_tool.name = "test_tool"
        registry.register(mock_tool)
        tools = registry.get_openai_tools()
        names = [t["function"]["name"] for t in tools]
        assert "test_tool" in names

    def test_register_duplicate(self):
        registry = ToolRegistry()
        mock_tool = MagicMock()
        mock_tool.name = "test_tool"
        registry.register(mock_tool)
        registry.register(mock_tool)
        tools = registry.get_openai_tools()
        names = [t["function"]["name"] for t in tools]
        assert len([n for n in names if n == "test_tool"]) == 1


class TestPromptManager:
    def test_get_template(self):
        manager = PromptManager()
        template = manager.render("chat_default", {})
        assert template != ""
        assert "expert" in template.lower()

    def test_get_nonexistent_template(self):
        manager = PromptManager()
        template = manager.render("nonexistent", {})
        assert template == ""

    def test_custom_template(self):
        manager = PromptManager()
        template = manager.render("tutor_socratic", {"topic": "Python", "display_name": "x", "difficulty": "intermediate"})
        assert template != ""
        assert "question" in template.lower()


class TestContextManager:
    @pytest.mark.asyncio
    async def test_build_context(self):
        manager = ContextManager()
        context = await manager.build_context(user_id="user-1")
        assert context["user_id"] == "user-1"
        assert context["display_name"] == "Student"

    @pytest.mark.asyncio
    async def test_get_context_for_section(self):
        manager = ContextManager()
        context = await manager.get_context_for_section(user_id="user-1", section_id="03-2")
        assert context["section_id"] == "03-2"
