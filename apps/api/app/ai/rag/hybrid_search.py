from __future__ import annotations

from typing import Any

from apps.api.app.ai.embeddings.cohere import cohere_embedding
from apps.api.app.ai.vectorstore.qdrant_service import qdrant_service
from apps.api.app.ai.vectorstore.pgvector_service import pgvector_service
from apps.api.app.core.config import settings
from apps.api.app.core.exceptions import VectorStoreError


RRF_K = 60


def reciprocal_rank_fusion(
    qdrant_results: list[dict[str, Any]],
    pgvector_results: list[dict[str, Any]],
    k: int = RRF_K,
) -> list[dict[str, Any]]:
    scores: dict[str, dict[str, Any]] = {}

    for rank, result in enumerate(qdrant_results):
        doc_id = str(result["id"])
        if doc_id not in scores:
            scores[doc_id] = {**result, "fusion_score": 0.0, "sources": []}
        scores[doc_id]["fusion_score"] += 1.0 / (k + rank + 1)
        scores[doc_id]["sources"].append("qdrant")

    for rank, result in enumerate(pgvector_results):
        doc_id = str(result["id"])
        if doc_id not in scores:
            scores[doc_id] = {**result, "fusion_score": 0.0, "sources": []}
        scores[doc_id]["fusion_score"] += 1.0 / (k + rank + 1)
        scores[doc_id]["sources"].append("pgvector")

    ranked = sorted(
        scores.values(),
        key=lambda x: x["fusion_score"],
        reverse=True,
    )

    return ranked


class HybridSearchService:
    async def search(
        self,
        query: str,
        top_k: int = 5,
        filters: dict[str, Any] | None = None,
        use_qdrant: bool = True,
        use_pgvector: bool = True,
    ) -> list[dict[str, Any]]:
        if not use_qdrant and not use_pgvector:
            raise VectorStoreError("At least one vector store must be enabled")

        qdrant_results: list[dict[str, Any]] = []
        pgvector_results: list[dict[str, Any]] = []

        if use_qdrant:
            try:
                qdrant_results = await qdrant_service.search(
                    query=query,
                    top_k=top_k * 2,
                    filters=filters,
                )
            except Exception as e:
                if not use_pgvector:
                    raise VectorStoreError(f"Qdrant search failed: {e}")

        if use_pgvector:
            try:
                pgvector_results = await pgvector_service.search(
                    query=query,
                    top_k=top_k * 2,
                    filters=filters,
                )
            except Exception as e:
                if not use_qdrant:
                    raise VectorStoreError(f"pgvector search failed: {e}")

        if not qdrant_results and not pgvector_results:
            return []

        fused = reciprocal_rank_fusion(qdrant_results, pgvector_results)
        return fused[:top_k]


hybrid_search = HybridSearchService()