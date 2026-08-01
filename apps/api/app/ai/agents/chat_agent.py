from __future__ import annotations

from collections.abc import AsyncGenerator
from typing import Any

from openai import AsyncOpenAI
from openai.types.chat import ChatCompletionMessageParam

from apps.api.app.ai.llm.router import llm_router
from apps.api.app.ai.memory.conversation_memory import ConversationMemory
from apps.api.app.ai.prompts.manager import prompt_manager
from apps.api.app.ai.context.manager import context_manager
from apps.api.app.ai.tools.registry import tool_registry
from apps.api.app.ai.rag.pipeline import rag_pipeline
from apps.api.app.ai.schemas.models import ChatMessage, ChatResponse, SourceCitation, StreamChunk
from apps.api.app.core.config import settings
from apps.api.app.core.exceptions import AiProviderError, ContextLengthExceededError


class ChatAgent:
    def __init__(self, user_id: str, conversation_id: str | None = None) -> None:
        self.user_id = user_id
        self.conversation_id = conversation_id
        self.memory = ConversationMemory(user_id, conversation_id)
        self._openai_client: AsyncOpenAI | None = None

    def _get_openai_client(self) -> AsyncOpenAI:
        if self._openai_client is None:
            self._openai_client = AsyncOpenAI(
                api_key=settings.OPENAI_API_KEY,
                timeout=settings.LLM_REQUEST_TIMEOUT,
            )
        return self._openai_client

    async def _build_sources(self, rag_results: list[dict[str, Any]]) -> list[SourceCitation]:
        sources: list[SourceCitation] = []
        for r in rag_results:
            sources.append(SourceCitation(
                id=r.get("id", ""),
                title=r.get("title", ""),
                content=r.get("content", "")[:200],
                score=r.get("score", 0.0),
                source=r.get("source", ""),
                relevance="high" if r.get("score", 0) > 0.8 else "medium" if r.get("score", 0) > 0.6 else "low",
            ))
        return sources

    async def run(
        self,
        message: str,
        conversation_id: str | None = None,
        use_rag: bool = True,
    ) -> ChatResponse:
        if conversation_id:
            self.conversation_id = conversation_id
            self.memory = ConversationMemory(self.user_id, conversation_id)

        conversation = await self.memory.get_or_create()
        self.conversation_id = conversation["id"]

        await self.memory.add_message({"role": "user", "content": message})

        history = await self.memory.get_history()
        enriched_context = await context_manager.build_context(self.user_id, {})
        system_prompt = prompt_manager.render("chat_default", enriched_context)

        rag_results: list[dict[str, Any]] = []
        rag_context = ""
        if use_rag:
            rag_results = await rag_pipeline.search(message, top_k=3)
            if rag_results:
                rag_context = "\n\nRelevant textbook content:\n" + "\n".join(
                    f"[{r['title']}] {r['content'][:500]}" for r in rag_results
                )

        full_system = system_prompt + rag_context

        messages_list: list[dict[str, Any]] = [
            {"role": "system", "content": full_system},
        ]
        for h in history[-settings.MAX_CONVERSATION_HISTORY:]:
            msg: dict[str, Any] = {"role": h["role"], "content": h["content"]}
            if h.get("tool_calls"):
                msg["tool_calls"] = h["tool_calls"]
            if h.get("tool_call_id"):
                msg["tool_call_id"] = h["tool_call_id"]
                msg["role"] = "tool"
            messages_list.append(msg)

        response = await llm_router.complete(messages_list)
        await self.memory.add_message({"role": "assistant", "content": response.content})

        sources = await self._build_sources(rag_results)

        return ChatResponse(
            conversation_id=self.conversation_id,
            message=ChatMessage(role="assistant", content=response.content),
            sources=sources,
            model=response.model,
        )

    async def run_stream(
        self,
        message: str,
        conversation_id: str | None = None,
        use_rag: bool = True,
    ) -> AsyncGenerator[StreamChunk, None]:
        if conversation_id:
            self.conversation_id = conversation_id
            self.memory = ConversationMemory(self.user_id, conversation_id)

        conversation = await self.memory.get_or_create()
        self.conversation_id = conversation["id"]

        await self.memory.add_message({"role": "user", "content": message})

        history = await self.memory.get_history()
        enriched_context = await context_manager.build_context(self.user_id, {})
        system_prompt = prompt_manager.render("chat_default", enriched_context)

        rag_results: list[dict[str, Any]] = []
        rag_context = ""
        if use_rag:
            rag_results = await rag_pipeline.search(message, top_k=3)
            if rag_results:
                rag_context = "\n\nRelevant textbook content:\n" + "\n".join(
                    f"[{r['title']}] {r['content'][:500]}" for r in rag_results
                )

        full_system = system_prompt + rag_context

        messages_list: list[dict[str, Any]] = [
            {"role": "system", "content": full_system},
        ]
        for h in history[-settings.MAX_CONVERSATION_HISTORY:]:
            msg: dict[str, Any] = {"role": h["role"], "content": h["content"]}
            if h.get("tool_calls"):
                msg["tool_calls"] = h["tool_calls"]
            if h.get("tool_call_id"):
                msg["tool_call_id"] = h["tool_call_id"]
                msg["role"] = "tool"
            messages_list.append(msg)

        collected_content = ""
        async for event in llm_router.complete_stream(messages_list):
            if event.type == "token":
                collected_content += event.token
                yield StreamChunk(event_type="token", token=event.token, content=event.token)
            elif event.type == "done":
                await self.memory.add_message({"role": "assistant", "content": collected_content})
                sources = await self._build_sources(rag_results)
                yield StreamChunk(
                    event_type="done",
                    content=collected_content,
                    finish_reason=event.finish_reason,
                )
            elif event.type == "error":
                yield StreamChunk(event_type="error", content=event.error or "Streaming error")

    async def process_message(
        self,
        message: str,
        stream: bool = True,
        context: dict[str, Any] | None = None,
    ) -> AsyncGenerator[dict[str, Any], None]:
        ctx = context or {}
        conversation = await self.memory.get_or_create()
        self.conversation_id = conversation["id"]

        await self.memory.add_message({"role": "user", "content": message})

        history = await self.memory.get_history()
        enriched_context = await context_manager.build_context(self.user_id, ctx)
        system_prompt = prompt_manager.render("chat_default", enriched_context)

        rag_results = await rag_pipeline.search(message, top_k=3)
        rag_context = ""
        if rag_results:
            rag_context = "\n\nRelevant textbook content:\n" + "\n".join(
                f"[{r['title']}] {r['content'][:500]}" for r in rag_results
            )

        full_system = system_prompt + rag_context

        messages_list: list[dict[str, Any]] = [
            {"role": "system", "content": full_system},
        ]
        for h in history[-settings.MAX_CONVERSATION_HISTORY:]:
            msg: dict[str, Any] = {"role": h["role"], "content": h["content"]}
            if h.get("tool_calls"):
                msg["tool_calls"] = h["tool_calls"]
            if h.get("tool_call_id"):
                msg["tool_call_id"] = h["tool_call_id"]
                msg["role"] = "tool"
            messages_list.append(msg)

        if stream:
            collected_content = ""
            async for event in llm_router.complete_stream(messages_list):
                if event.type == "token":
                    collected_content += event.token
                    yield {"type": "token", "content": event.token}
                elif event.type == "done":
                    await self.memory.add_message({
                        "role": "assistant",
                        "content": collected_content,
                    })
                    sources = await self._build_sources(rag_results)
                    yield {"type": "done", "content": collected_content, "sources": [s.model_dump() for s in sources]}
                elif event.type == "error":
                    yield {"type": "error", "content": event.error}
        else:
            response = await llm_router.complete(messages_list)
            await self.memory.add_message({
                "role": "assistant",
                "content": response.content,
            })
            sources = await self._build_sources(rag_results)
            yield {"type": "done", "content": response.content, "sources": [s.model_dump() for s in sources]}

    async def process_with_tools(
        self,
        message: str,
        stream: bool = True,
    ) -> AsyncGenerator[dict[str, Any], None]:
        client = self._get_openai_client()
        conversation = await self.memory.get_or_create()
        self.conversation_id = conversation["id"]

        await self.memory.add_message({"role": "user", "content": message})
        history = await self.memory.get_history()
        context_data = await context_manager.build_context(self.user_id, {})
        system_prompt = prompt_manager.render("chat_with_tools", context_data)

        openai_messages: list[ChatCompletionMessageParam] = [
            {"role": "system", "content": system_prompt},
        ]
        for h in history[-settings.MAX_CONVERSATION_HISTORY:]:
            role = h["role"]
            if role in ("user", "assistant", "system"):
                openai_messages.append({"role": role, "content": h["content"]})

        tools = tool_registry.get_openai_tools()

        response = await client.chat.completions.create(
            model=settings.LLM_DEFAULT_MODEL,
            messages=openai_messages,
            tools=tools,
            tool_choice="auto",
            temperature=settings.LLM_TEMPERATURE,
            max_tokens=settings.LLM_MAX_TOKENS,
        )

        choice = response.choices[0]
        message_content = choice.message.content or ""

        if choice.message.tool_calls:
            results = []
            for tool_call in choice.message.tool_calls:
                result = await tool_registry.execute(
                    tool_call.function.name,
                    tool_call.function.arguments,
                    user_id=self.user_id,
                )
                results.append(result)
                await self.memory.add_message({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": str(result),
                })

            final_response = await client.chat.completions.create(
                model=settings.LLM_DEFAULT_MODEL,
                messages=[
                    *openai_messages,
                    {"role": "assistant", "content": message_content, "tool_calls": choice.message.tool_calls},
                    *[{"role": "tool", "tool_call_id": tc.id, "content": str(res)}
                      for tc, res in zip(choice.message.tool_calls, results)],
                ],
                temperature=settings.LLM_TEMPERATURE,
            )
            final_content = final_response.choices[0].message.content or ""
            await self.memory.add_message({"role": "assistant", "content": final_content})
            yield {"type": "done", "content": final_content, "sources": []}
        else:
            await self.memory.add_message({"role": "assistant", "content": message_content})
            yield {"type": "done", "content": message_content, "sources": []}

    async def get_conversation_id(self) -> str:
        if not self.conversation_id:
            conv = await self.memory.get_or_create()
            self.conversation_id = conv["id"]
        return self.conversation_id
