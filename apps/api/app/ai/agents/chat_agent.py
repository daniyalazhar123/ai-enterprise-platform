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
                    sources = []
                    for r in rag_results:
                        sources.append({
                            "id": r.get("id", ""),
                            "title": r.get("title", ""),
                            "content": r.get("content", "")[:200],
                            "relevance": r.get("score", 0),
                        })
                    yield {"type": "done", "content": collected_content, "sources": sources}
                elif event.type == "error":
                    yield {"type": "error", "content": event.error}
        else:
            response = await llm_router.complete(messages_list)
            await self.memory.add_message({
                "role": "assistant",
                "content": response.content,
            })
            sources = []
            for r in rag_results:
                sources.append({
                    "id": r.get("id", ""),
                    "title": r.get("title", ""),
                    "content": r.get("content", "")[:200],
                    "relevance": r.get("score", 0),
                })
            yield {"type": "done", "content": response.content, "sources": sources}

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
            for tool_call in choice.message.tool_calls:
                result = await tool_registry.execute(
                    tool_call.function.name,
                    tool_call.function.arguments,
                    user_id=self.user_id,
                )
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
                    *[{"role": "tool", "tool_call_id": tc.id, "content": str(result)}
                      for tc, result in zip(choice.message.tool_calls, [])],
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