from __future__ import annotations

import json
from typing import Any

import asyncpg
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.app.ai.embeddings.cohere import cohere_embedding
from apps.api.app.core.config import settings


class PgVectorService:
    def __init__(self) -> None:
        self._pool: asyncpg.Pool | None = None

    async def _get_pool(self) -> asyncpg.Pool:
        if self._pool is None:
            dsn = settings.DATABASE_URL.replace("+asyncpg", "")
            self._pool = await asyncpg.create_pool(dsn, min_size=2, max_size=10)
        return self._pool

    async def ensure_extension(self, db: AsyncSession) -> None:
        await db.execute(text("CREATE EXTENSION IF NOT EXISTS vector;"))
        await db.commit()

    async def ensure_table(self, db: AsyncSession) -> None:
        await db.execute(
            text("""
                CREATE TABLE IF NOT EXISTS embeddings (
                    id UUID PRIMARY KEY,
                    content TEXT NOT NULL,
                    embedding vector(1024),
                    metadata JSONB NOT NULL DEFAULT '{}',
                    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
                );
            """)
        )
        await db.execute(
            text("""
                CREATE INDEX IF NOT EXISTS idx_embeddings_hnsw
                ON embeddings
                USING hnsw (embedding vector_cosine_ops)
                WITH (m = 16, ef_construction = 200);
            """)
        )
        await db.execute(
            text("""
                CREATE INDEX IF NOT EXISTS idx_embeddings_metadata
                ON embeddings USING gin (metadata);
            """)
        )
        await db.commit()

    async def insert_embedding(
        self,
        point_id: str,
        content: str,
        metadata: dict[str, Any],
        db: AsyncSession,
    ) -> None:
        embedding = await cohere_embedding.embed_query(content)
        embedding_str = "[" + ",".join(str(v) for v in embedding) + "]"

        await db.execute(
            text("""
                INSERT INTO embeddings (id, content, embedding, metadata)
                VALUES (:id, :content, :embedding::vector, :metadata)
                ON CONFLICT (id) DO UPDATE
                SET content = EXCLUDED.content,
                    embedding = EXCLUDED.embedding,
                    metadata = EXCLUDED.metadata
            """),
            {
                "id": point_id,
                "content": content,
                "embedding": embedding_str,
                "metadata": json.dumps(metadata),
            },
        )
        await db.commit()

    async def search(
        self,
        query: str,
        top_k: int = 5,
        filters: dict[str, Any] | None = None,
        db: AsyncSession | None = None,
    ) -> list[dict[str, Any]]:
        query_embedding = await cohere_embedding.embed_query(query)
        embedding_str = "[" + ",".join(str(v) for v in query_embedding) + "]"

        filter_clause = ""
        params: dict[str, Any] = {
            "embedding": embedding_str,
            "limit": top_k,
        }

        if filters:
            filter_parts = []
            for i, (key, value) in enumerate(filters.items()):
                param_key = f"f_{i}"
                filter_parts.append(f"metadata->>'{key}' = :{param_key}")
                params[param_key] = str(value)
            if filter_parts:
                filter_clause = "AND " + " AND ".join(filter_parts)

        sql = text(f"""
            SELECT
                id,
                content,
                metadata,
                1 - (embedding <=> :embedding::vector) as similarity
            FROM embeddings
            WHERE 1=1 {filter_clause}
            ORDER BY embedding <=> :embedding::vector
            LIMIT :limit
        """)

        if db:
            result = await db.execute(sql, params)
            rows = result.fetchall()
        else:
            pool = await self._get_pool()
            async with pool.acquire() as conn:
                rows = await conn.fetch(sql, *params.values())

        results: list[dict[str, Any]] = []
        for row in rows:
            metadata = row.get("metadata") if isinstance(row, dict) else row._mapping.get("metadata", {})
            results.append({
                "id": str(row[0]),
                "content": row[1],
                "metadata": json.loads(metadata) if isinstance(metadata, str) else (metadata or {}),
                "score": float(row[3]),
            })

        return results

    async def delete_by_filter(self, filter_dict: dict[str, Any], db: AsyncSession) -> None:
        conditions = " AND ".join(f"metadata->>'{k}' = :{k}" for k in filter_dict)
        await db.execute(
            text(f"DELETE FROM embeddings WHERE {conditions}"),
            filter_dict,
        )
        await db.commit()

    async def close(self) -> None:
        if self._pool:
            await self._pool.close()


pgvector_service = PgVectorService()