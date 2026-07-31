from __future__ import annotations

import json
from typing import Any, Callable

from apps.api.app.ai.tools.textbook_tools import TextbookSearchTool
from apps.api.app.ai.tools.user_context_tools import UserContextTool


class ToolRegistry:
    def __init__(self) -> None:
        self._tools: dict[str, tuple[Callable, dict[str, Any]]] = {}
        self._register_defaults()

    def _register_defaults(self) -> None:
        self.register(TextbookSearchTool())
        self.register(UserContextTool())

    def register(self, tool: Any) -> None:
        self._tools[tool.name] = (tool.execute, {
            "type": "function",
            "function": {
                "name": tool.name,
                "description": tool.description,
                "parameters": tool.parameters,
            },
        })

    def get_openai_tools(self) -> list[dict[str, Any]]:
        return [info[1] for info in self._tools.values()]

    async def execute(self, name: str, arguments: str, **kwargs: Any) -> Any:
        tool_fn, _ = self._tools.get(name, (None, None))
        if tool_fn is None:
            return f"Error: Tool '{name}' not found"

        try:
            args = json.loads(arguments) if isinstance(arguments, str) else arguments
            return await tool_fn(**args, **kwargs)
        except Exception as e:
            return f"Tool execution error: {e}"


tool_registry = ToolRegistry()