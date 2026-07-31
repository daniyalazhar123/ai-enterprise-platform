from __future__ import annotations

import logging
from collections.abc import AsyncGenerator
from typing import Any

from apps.api.app.ai.llm.base import LlmProvider, ModelConfig, ProviderResponse, StreamEvent
from apps.api.app.ai.llm.gemini_provider import GeminiProvider
from apps.api.app.ai.llm.grok_provider import GrokProvider
from apps.api.app.ai.llm.openai_provider import OpenAIProvider
from apps.api.app.ai.llm.openrouter_provider import OpenRouterProvider
from apps.api.app.core.config import settings
from apps.api.app.core.exceptions import AiProviderError

logger = logging.getLogger(__name__)


class LlmRouter:
    def __init__(self) -> None:
        self._providers: dict[str, LlmProvider] = {}
        self._priority: list[str] = []
        self._initialize()

    def _initialize(self) -> None:
        providers: list[LlmProvider] = [
            OpenAIProvider(),
            GeminiProvider(),
            GrokProvider(),
            OpenRouterProvider(),
        ]

        for provider in providers:
            self._providers[provider.name] = provider

        self._priority = ["openai", "gemini", "grok", "openrouter"]

    def get_provider(self, name: str) -> LlmProvider | None:
        return self._providers.get(name)

    async def get_available_providers(self) -> list[tuple[str, LlmProvider]]:
        available: list[tuple[str, LlmProvider]] = []
        for name in self._priority:
            provider = self._providers.get(name)
            if provider and await provider.is_available():
                available.append((name, provider))
        return available

    async def complete(
        self,
        messages: list[dict[str, Any]],
        config: ModelConfig | None = None,
        preferred_provider: str | None = None,
    ) -> ProviderResponse:
        available = await self.get_available_providers()
        if not available:
            raise AiProviderError("No AI providers available")

        if preferred_provider:
            for name, provider in available:
                if name == preferred_provider:
                    try:
                        return await provider.complete(messages, config)
                    except Exception as e:
                        logger.warning("Preferred provider %s failed: %s", name, e)

        errors: list[str] = []
        for name, provider in available:
            try:
                return await provider.complete(messages, config)
            except Exception as e:
                logger.warning("Provider %s failed: %s", name, e)
                errors.append(f"{name}: {e}")

        raise AiProviderError(f"All providers failed: {'; '.join(errors)}")

    async def complete_stream(
        self,
        messages: list[dict[str, Any]],
        config: ModelConfig | None = None,
        preferred_provider: str | None = None,
    ) -> AsyncGenerator[StreamEvent, None]:
        available = await self.get_available_providers()
        if not available:
            yield StreamEvent(type="error", error="No AI providers available")
            return

        providers_to_try: list[tuple[str, LlmProvider]] = []

        if preferred_provider:
            for name, provider in available:
                if name == preferred_provider:
                    providers_to_try.append((name, provider))
                    break

        for pair in available:
            if pair not in providers_to_try:
                providers_to_try.append(pair)

        for name, provider in providers_to_try:
            try:
                async for event in provider.complete_stream(messages, config):
                    yield event
                return
            except Exception as e:
                logger.warning("Stream provider %s failed: %s", name, e)

        yield StreamEvent(type="error", error="All providers failed for streaming")

    async def complete_with_fallback(
        self,
        messages: list[dict[str, Any]],
        config: ModelConfig | None = None,
    ) -> ProviderResponse:
        try:
            return await self.complete(messages, config, preferred_provider="openai")
        except AiProviderError:
            try:
                fallback_config = ModelConfig(model=settings.LLM_FALLBACK_MODEL)
                return await self.complete(messages, fallback_config, preferred_provider="gemini")
            except AiProviderError:
                return await self.complete(messages, config)


llm_router = LlmRouter()