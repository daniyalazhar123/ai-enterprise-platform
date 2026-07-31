from __future__ import annotations

import json
from collections.abc import AsyncGenerator
from typing import Any

import httpx

from apps.api.app.ai.llm.base import LlmProvider, ModelConfig, ProviderResponse, StreamEvent
from apps.api.app.core.config import settings


class GeminiProvider(LlmProvider):
    @property
    def name(self) -> str:
        return "gemini"

    def __init__(self) -> None:
        self.api_key = settings.GEMINI_API_KEY
        self.base_url = "https://generativelanguage.googleapis.com/v1beta/models"
        self._models = ["gemini-2.5-pro", "gemini-2.0-flash", "gemini-1.5-pro", "gemini-1.5-flash"]

    async def is_available(self) -> bool:
        return bool(self.api_key)

    def get_models(self) -> list[str]:
        return self._models

    def _build_request(self, messages: list[dict[str, Any]], config: ModelConfig | None = None) -> dict[str, Any]:
        cfg = config or ModelConfig(model=self._models[0])
        system: str | None = None
        contents: list[dict[str, Any]] = []

        for msg in messages:
            if msg["role"] == "system":
                system = msg["content"]
            elif msg["role"] == "tool":
                contents.append({"role": "user", "parts": [{"text": f"Tool result: {msg['content']}"}]})
            else:
                role = "model" if msg["role"] == "assistant" else "user"
                contents.append({"role": role, "parts": [{"text": msg["content"]}]})

        body: dict[str, Any] = {
            "contents": contents,
            "generationConfig": {
                "temperature": cfg.temperature,
                "maxOutputTokens": cfg.max_tokens,
                "topP": cfg.top_p,
            },
        }
        if system:
            body["systemInstruction"] = {"parts": [{"text": system}]}
        return body

    async def complete(
        self,
        messages: list[dict[str, Any]],
        config: ModelConfig | None = None,
    ) -> ProviderResponse:
        cfg = config or ModelConfig(model=self._models[0])
        body = self._build_request(messages, cfg)
        url = f"{self.base_url}/{cfg.model}:generateContent?key={self.api_key}"

        async with httpx.AsyncClient(timeout=settings.LLM_REQUEST_TIMEOUT) as client:
            resp = await client.post(url, json=body)
            resp.raise_for_status()
            data = resp.json()

        candidate = data.get("candidates", [{}])[0]
        content = candidate.get("content", {}).get("parts", [{}])[0].get("text", "")
        usage = data.get("usageMetadata", {})

        return ProviderResponse(
            content=content,
            finish_reason=candidate.get("finishReason", "stop"),
            usage={"prompt_tokens": usage.get("promptTokenCount", 0), "completion_tokens": usage.get("candidatesTokenCount", 0)},
            model=cfg.model,
            provider=self.name,
        )

    async def complete_stream(
        self,
        messages: list[dict[str, Any]],
        config: ModelConfig | None = None,
    ) -> AsyncGenerator[StreamEvent, None]:
        cfg = config or ModelConfig(model=self._models[0])
        body = self._build_request(messages, cfg)
        body["generationConfig"]["candidateCount"] = 1
        url = f"{self.base_url}/{cfg.model}:streamGenerateContent?alt=sse&key={self.api_key}"

        async with httpx.AsyncClient(timeout=settings.LLM_REQUEST_TIMEOUT) as client:
            async with client.stream("POST", url, json=body) as resp:
                resp.raise_for_status()
                index = 0
                async for line in resp.aiter_lines():
                    if line.startswith("data: "):
                        data = json.loads(line[6:])
                        candidates = data.get("candidates", [{}])
                        if candidates:
                            parts = candidates[0].get("content", {}).get("parts", [{}])
                            if parts:
                                text = parts[0].get("text", "")
                                if text:
                                    yield StreamEvent(type="token", token=text, finish_reason=None)
                                    index += 1
                        finish = candidates[0].get("finishReason") if candidates else None
                        if finish:
                            yield StreamEvent(type="done", finish_reason=finish)