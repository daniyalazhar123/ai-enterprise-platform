from __future__ import annotations

from typing import Any

from apps.api.app.core.config import settings


class ContextManager:
    def __init__(self) -> None:
        self._providers: dict[str, ContextProvider] = {}

    def register(self, name: str, provider: ContextProvider) -> None:
        self._providers[name] = provider

    async def build_context(self, user_id: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        params = params or {}
        context: dict[str, Any] = {
            "display_name": params.get("display_name", "Student"),
            "chapter": params.get("chapter", "General"),
            "language": params.get("language", "en"),
            "difficulty": params.get("difficulty", "intermediate"),
            "user_id": user_id,
        }

        context["language_label"] = {
            "en": "Advanced English",
            "en-plain": "Plain English",
            "ur": "Urdu",
            "ur-rom": "Roman Urdu",
        }.get(context["language"], "English")

        for name, provider in self._providers.items():
            try:
                provider_context = await provider.get_context(user_id, params)
                context[name] = provider_context
            except Exception:
                context[name] = {}

        return context

    async def get_context_for_section(
        self,
        user_id: str,
        section_id: str,
        params: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        context = await self.build_context(user_id, params)
        context["section_id"] = section_id
        return context


class ContextProvider:
    async def get_context(self, user_id: str, params: dict[str, Any]) -> dict[str, Any]:
        return {}


class ProgressContextProvider(ContextProvider):
    async def get_context(self, user_id: str, params: dict[str, Any]) -> dict[str, Any]:
        return {
            "chapters_completed": 0,
            "current_chapter": params.get("chapter", "Introduction"),
            "quiz_average": 0,
        }


context_manager = ContextManager()
context_manager.register("progress", ProgressContextProvider())