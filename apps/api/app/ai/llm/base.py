from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import AsyncGenerator
from typing import Any

from pydantic import BaseModel


class ModelConfig(BaseModel):
    model: str
    temperature: float = 0.7
    max_tokens: int = 4096
    top_p: float = 0.95
    presence_penalty: float = 0.0
    frequency_penalty: float = 0.0
    stop: list[str] | None = None


class ProviderResponse(BaseModel):
    content: str
    finish_reason: str = "stop"
    usage: dict[str, int] = {}
    model: str = ""
    provider: str = ""


class StreamEvent(BaseModel):
    type: str = "token"
    token: str = ""
    finish_reason: str | None = None
    usage: dict[str, int] = {}
    error: str | None = None


class LlmProvider(ABC):
    @property
    @abstractmethod
    def name(self) -> str:
        ...

    @abstractmethod
    async def complete(
        self,
        messages: list[dict[str, Any]],
        config: ModelConfig | None = None,
    ) -> ProviderResponse:
        ...

    @abstractmethod
    async def complete_stream(
        self,
        messages: list[dict[str, Any]],
        config: ModelConfig | None = None,
    ) -> AsyncGenerator[StreamEvent, None]:
        ...

    @abstractmethod
    async def is_available(self) -> bool:
        ...

    @abstractmethod
    def get_models(self) -> list[str]:
        ...