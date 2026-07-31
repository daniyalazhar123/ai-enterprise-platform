from __future__ import annotations

from typing import Any

from qdrant_client import QdrantClient
from qdrant_client.http import models
from qdrant_client.models import (
    Distance,
    FieldCondition,
    Filter,
    FilterSelector,
    HnswConfigDiff,
    MatchValue,
    PointIdsList,
    PointStruct,
    ScoredPoint,
    SearchParams,
    VectorParams,
)

from apps.api.app.ai.embeddings.cohere import cohere_embedding
from apps.api.app.core.config import settings
from apps.api.app.core.exceptions import VectorStoreError


class QdrantService:
    def __init__(self) -> None:
        self.collection_name = settings.QDRANT_COLLECTION
        self.vector_size = settings.QDRANT_VECTOR_SIZE
        self._client: QdrantClient | None = None

    def _get_client(self) -> QdrantClient:
        if self._client is None:
            self._client = QdrantClient(
                url=settings.QDRANT_URL,
                api_key=settings.QDRANT_API_KEY,
                timeout=30,
            )
        return self._client

    async def ensure_collection(self) -> None:
        client = self._get_client()
        collections = client.get_collections().collections
        names = [c.name for c in collections]

        if self.collection_name not in names:
            client.create_collection(
                collection_name=self.collection_name,
                vectors_config=VectorParams(
                    size=self.vector_size,
                    distance=Distance.COSINE,
                    hnsw_config=HnswConfigDiff(
                        m=16,
                        ef_construct=200,
                    ),
                ),
                on_disk_payload=True,
                shard_number=4,
                replication_factor=2,
            )

            client.create_payload_index(
                collection_name=self.collection_name,
                field_name="user_id",
                field_type=models.PayloadSchemaType.KEYWORD,
            )
            client.create_payload_index(
                collection_name=self.collection_name,
                field_name="chapter_id",
                field_type=models.PayloadSchemaType.KEYWORD,
            )
            client.create_payload_index(
                collection_name=self.collection_name,
                field_name="doc_id",
                field_type=models.PayloadSchemaType.KEYWORD,
            )

    async def upsert_points(
        self,
        points: list[dict[str, Any]],
    ) -> int:
        client = self._get_client()
        await self.ensure_collection()

        texts = [p["content"] for p in points]
        embeddings = await cohere_embedding.embed_documents(texts)

        if len(embeddings) != len(points):
            raise VectorStoreError("Embedding count mismatch")

        point_structs: list[PointStruct] = []
        for point, embedding in zip(points, embeddings):
            point_structs.append(PointStruct(
                id=point["id"],
                vector=embedding,
                payload={
                    "content": point["content"],
                    "doc_id": point.get("doc_id", ""),
                    "chunk_index": point.get("chunk_index", 0),
                    "title": point.get("metadata", {}).get("filename", ""),
                    "user_id": point.get("metadata", {}).get("user_id", ""),
                    "chapter_id": point.get("metadata", {}).get("chapter_id", ""),
                    "section": point.get("metadata", {}).get("section", ""),
                    "source": point.get("metadata", {}).get("content_type", ""),
                    **(point.get("metadata", {}) or {}),
                },
            ))

        operation_info = client.upsert(
            collection_name=self.collection_name,
            points=point_structs,
        )
        return len(point_structs)

    async def search(
        self,
        query: str,
        top_k: int = 5,
        score_threshold: float | None = None,
        filters: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        client = self._get_client()

        query_vector = await cohere_embedding.embed_query(query)

        filter_conditions: list[FieldCondition] = []
        if filters:
            for key, value in filters.items():
                if isinstance(value, list):
                    filter_conditions.append(
                        FieldCondition(key=key, match=models.MatchAny(any=value))
                    )
                else:
                    filter_conditions.append(
                        FieldCondition(key=key, match=MatchValue(value=value))
                    )

        search_filter = Filter(must=filter_conditions) if filter_conditions else None

        search_params = SearchParams(
            hnsw_ef=128,
            exact=False,
        )

        scored_points = client.search(
            collection_name=self.collection_name,
            query_vector=query_vector,
            limit=top_k,
            query_filter=search_filter,
            search_params=search_params,
            score_threshold=score_threshold or settings.RAG_SCORE_THRESHOLD,
        )

        results: list[dict[str, Any]] = []
        for point in scored_points:
            if point.payload:
                results.append({
                    "id": point.id,
                    "content": point.payload.get("content", ""),
                    "title": point.payload.get("title", ""),
                    "section": point.payload.get("section", ""),
                    "score": point.score,
                    "source": point.payload.get("source", ""),
                    "metadata": {k: v for k, v in point.payload.items() if k not in ("content",)},
                })

        return results

    async def delete_points(self, point_ids: list[str]) -> None:
        client = self._get_client()
        client.delete(
            collection_name=self.collection_name,
            points_selector=PointIdsList(
                points=point_ids,
            ),
        )

    async def delete_by_filter(self, filter_dict: dict[str, Any]) -> None:
        client = self._get_client()
        conditions = [
            FieldCondition(key=k, match=MatchValue(value=v))
            for k, v in filter_dict.items()
        ]
        client.delete(
            collection_name=self.collection_name,
            points_selector=FilterSelector(
                filter=Filter(must=conditions),
            ),
        )

    async def count_points(self, filter_dict: dict[str, Any] | None = None) -> int:
        client = self._get_client()
        conditions = None
        if filter_dict:
            conditions = [
                FieldCondition(key=k, match=MatchValue(value=v))
                for k, v in filter_dict.items()
            ]

        result = client.count(
            collection_name=self.collection_name,
            count_filter=Filter(must=conditions) if conditions else None,
        )
        return result.count


qdrant_service = QdrantService()