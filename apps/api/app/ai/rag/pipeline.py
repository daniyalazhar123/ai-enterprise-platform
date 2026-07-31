from __future__ import annotations

from typing import Any

from apps.api.app.ai.llm.router import llm_router
from apps.api.app.ai.prompts.manager import prompt_manager
from apps.api.app.ai.rag.hybrid_search import hybrid_search
from apps.api.app.ai.schemas.models import SourceCitation
from apps.api.app.core.config import settings


class RagPipeline:
    def __init__(self) -> None:
        self.max_context_chunks = settings.RAG_MAX_CONTEXT_CHUNKS
        self.score_threshold = settings.RAG_SCORE_THRESHOLD

    async def retrieve(
        self,
        query: str,
        filters: dict[str, Any] | None = None,
        user_id: str | None = None,
    ) -> tuple[list[SourceCitation], str]:
        results = await hybrid_search.search(
            query=query,
            top_k=self.max_context_chunks,
            filters={
                **(filters or {}),
                **({"user_id": user_id} if user_id else {}),
            },
        )

        filtered = [r for r in results if r.get("score", 0) >= self.score_threshold]

        citations: list[SourceCitation] = []
        context_parts: list[str] = []

        for i, result in enumerate(filtered):
            citations.append(SourceCitation(
                id=result.get("id", ""),
                title=result.get("title", "Unknown Source"),
                content=result.get("content", "")[:500],
                score=result.get("score", 0),
                source=result.get("source", ""),
                section=result.get("section"),
                chunk_index=result.get("metadata", {}).get("chunk_index", 0),
                relevance=(
                    "high" if result.get("score", 0) > 0.8
                    else "medium" if result.get("score", 0) > 0.6
                    else "low"
                ),
            ))
            context_parts.append(
                f"[Source {i + 1}: {result.get('title', 'Unknown')} "
                f"(relevance: {citations[-1].relevance})]\n"
                f"{result.get('content', '')}"
            )

        context = "\n\n".join(context_parts) if context_parts else ""
        return citations, context

    async def augment(
        self,
        query: str,
        context: str,
        conversation_history: list[dict[str, str]] | None = None,
    ) -> str:
        if not context:
            return query

        template = prompt_manager.get_template("chat_default")
        if conversation_history:
            template = prompt_manager.get_template("chat_with_tools")

        augmented = f"""Context from knowledge base:
{context}

Original question: {query}

Based on the context above, provide an answer. If the context is insufficient, say so and suggest what additional information would be helpful. Include citations to relevant sources when possible."""

        return augmented

    async def generate_citations(self, citations: list[SourceCitation]) -> list[dict[str, Any]]:
        return [
            {
                "id": c.id,
                "title": c.title,
                "relevance": c.relevance,
                "source": c.source,
                "section": c.section,
                "score": round(c.score, 3),
            }
            for c in citations
        ]


rag_pipeline = RagPipeline()