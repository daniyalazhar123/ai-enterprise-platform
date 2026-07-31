from __future__ import annotations

import json
from collections.abc import AsyncGenerator
from typing import Any

import httpx

from apps.api.app.ai.llm.base import LlmProvider, ModelConfig, ProviderResponse, StreamEvent
from apps.api.app.core.config import settings


class GrokProvider(LlmProvider):
    @property
    def name(self) -> str:
        return "grok"

    def __init__(self) -> None:
        self.api_key = settings.GROK_API_KEY
        self.base_url = "https://api.x.ai/v1"
        self._models = ["grok-3", "grok-2", "grok-2-mini"]

    async def is_available(self) -> bool:
        return bool(self.api_key)

    def get_models(self) -> list[str]:
        return self._models

    async def complete(
        self,
        messages: list[dict[str, Any]],
        config: ModelConfig | None = None,
    ) -> ProviderResponse:
        cfg = config or ModelConfig(model=self._models[0])
        body = {
            "model": cfg.model,
            "messages": messages,
            "temperature": cfg.temperature,
            "max_tokens": cfg.max_tokens,
            "top_p": cfg.top_p,
        }

        async with httpx.AsyncClient(timeout=settings.LLM_REQUEST_TIMEOUT) as client:
            resp = await client.post(
                f"{self.base_url}/chat/completions",
                headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
                json=body,
            )
            resp.raise_for_status()
            data = resp.json()

        choice = data.get("choices", [{}])[0]
        return ProviderResponse(
            content=choice.get("message", {}).get("content", ""),
            finish_reason=choice.get("finish_reason", "stop"),
            usage=data.get("usage", {}),
            model=cfg.model,
            provider=self.name,
        )

    async def complete_stream(
        self,
        messages: list[dict[str, Any]],
        config: ModelConfig | None = None,
    ) -> AsyncGenerator[StreamEvent, None]:
        cfg = config or ModelConfig(model=self._models[0])
        body = {
            "model": cfg.model,
            "messages": messages,
            "temperature": cfg.temperature,
            "max_tokens": cfg.max_tokens,
            "stream": True,
        }

        async with httpx.AsyncClient(timeout=settings.LLM_REQUEST_TIMEOUT) as client:
            async with client.stream(
                "POST",
                f"{self.base_url}/chat/completions",
                headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
                json=body,
            ) as resp:
                resp.raise_for_status()
                async for line in resp.aiter_lines():
                    if line.startswith("data: "):
                        data_str = line[6:]
                        if data_str == "[DONE]":
                            yield StreamEvent(type="done", finish_reason="stop")
                            return
                        data = json.loads(data_str)
                        choice = data.get("choices", [{}])[0]
                        delta = choice.get("delta", {})
                        content = delta.get("content", "")
                        if content:
                            yield StreamEvent(type="token", token=content)
                        finish = choice.get("finish_reason")
                        if finish:
                            yield StreamEvent(type="done", finish_reason=finish)