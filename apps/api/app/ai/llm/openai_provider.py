from __future__ import annotations

import json
from collections.abc import AsyncGenerator
from typing import Any

from openai import AsyncOpenAI, AsyncStream
from openai.types.chat import ChatCompletionChunk

from apps.api.app.ai.llm.base import LlmProvider, ModelConfig, ProviderResponse, StreamEvent
from apps.api.app.core.config import settings


class OpenAIProvider(LlmProvider):
    @property
    def name(self) -> str:
        return "openai"

    def __init__(self) -> None:
        self._models = ["gpt-4o", "gpt-4o-mini", "gpt-4-turbo", "gpt-3.5-turbo"]

    async def is_available(self) -> bool:
        return bool(settings.OPENAI_API_KEY)

    def get_models(self) -> list[str]:
        return self._models

    def _get_client(self) -> AsyncOpenAI:
        return AsyncOpenAI(api_key=settings.OPENAI_API_KEY, timeout=settings.LLM_REQUEST_TIMEOUT)

    async def complete(
        self,
        messages: list[dict[str, Any]],
        config: ModelConfig | None = None,
    ) -> ProviderResponse:
        cfg = config or ModelConfig(model=self._models[0])
        client = self._get_client()

        response = await client.chat.completions.create(
            model=cfg.model,
            messages=messages,
            temperature=cfg.temperature,
            max_tokens=cfg.max_tokens,
            top_p=cfg.top_p,
            presence_penalty=cfg.presence_penalty,
            frequency_penalty=cfg.frequency_penalty,
            stop=cfg.stop,
        )

        choice = response.choices[0]
        return ProviderResponse(
            content=choice.message.content or "",
            finish_reason=choice.finish_reason or "stop",
            usage={
                "prompt_tokens": response.usage.prompt_tokens if response.usage else 0,
                "completion_tokens": response.usage.completion_tokens if response.usage else 0,
                "total_tokens": response.usage.total_tokens if response.usage else 0,
            },
            model=response.model,
            provider=self.name,
        )

    async def complete_stream(
        self,
        messages: list[dict[str, Any]],
        config: ModelConfig | None = None,
    ) -> AsyncGenerator[StreamEvent, None]:
        cfg = config or ModelConfig(model=self._models[0])
        client = self._get_client()

        stream = await client.chat.completions.create(
            model=cfg.model,
            messages=messages,
            temperature=cfg.temperature,
            max_tokens=cfg.max_tokens,
            top_p=cfg.top_p,
            stream=True,
            stream_options={"include_usage": True},
        )

        async for chunk in stream:
            if not chunk.choices and chunk.usage:
                yield StreamEvent(type="usage", usage={
                    "prompt_tokens": chunk.usage.prompt_tokens or 0,
                    "completion_tokens": chunk.usage.completion_tokens or 0,
                    "total_tokens": chunk.usage.total_tokens or 0,
                })
                continue

            if chunk.choices:
                delta = chunk.choices[0].delta
                if delta.content:
                    yield StreamEvent(type="token", token=delta.content)
                finish = chunk.choices[0].finish_reason
                if finish:
                    yield StreamEvent(type="done", finish_reason=finish)