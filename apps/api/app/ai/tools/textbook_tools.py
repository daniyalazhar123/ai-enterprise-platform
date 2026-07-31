from __future__ import annotations

from typing import Any

from apps.api.app.ai.rag.pipeline import rag_pipeline


class TextbookSearchTool:
    name = "textbook_search"
    description = "Search the textbook content for relevant information. Use this to find specific concepts, definitions, or explanations across all chapters."
    parameters: dict[str, Any] = {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "The search query to find relevant textbook content",
            },
            "top_k": {
                "type": "integer",
                "description": "Number of results to return (default: 5)",
                "default": 5,
            },
        },
        "required": ["query"],
    }

    async def execute(self, query: str, top_k: int = 5, **kwargs: Any) -> str:
        results = await rag_pipeline.search(query, top_k=top_k)
        if not results:
            return "No relevant content found."

        formatted = []
        for i, r in enumerate(results, 1):
            formatted.append(
                f"[{i}] {r.get('title', 'Untitled')}\n"
                f"   Relevance: {r.get('score', 0):.2f}\n"
                f"   Content: {r.get('content', '')[:500]}"
            )
        return "\n\n".join(formatted)


class TextbookSectionLookupTool:
    name = "textbook_section"
    description = "Get the full content of a specific textbook section by its ID."
    parameters: dict[str, Any] = {
        "type": "object",
        "properties": {
            "section_id": {
                "type": "string",
                "description": "The section ID to look up",
            },
        },
        "required": ["section_id"],
    }

    async def execute(self, section_id: str, **kwargs: Any) -> str:
        results = await rag_pipeline.search(
            section_id.replace("-", " "),
            top_k=1,
            filters={"section_id": section_id} if section_id else {},
        )
        if results:
            return results[0].get("content", "Content not found.")
        return "Section not found."