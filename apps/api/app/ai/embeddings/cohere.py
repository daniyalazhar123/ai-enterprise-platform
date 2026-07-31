from __future__ import annotations

from typing import Any

import httpx

from apps.api.app.core.config import settings
from apps.api.app.core.exceptions import EmbeddingError


class CohereEmbeddingService:
    def __init__(self) -> None:
        self.api_key = settings.COHERE_API_KEY
        self.model = settings.EMBEDDING_MODEL
        self.base_url = "https://api.cohere.com/v2"
        self._batch_size = settings.EMBEDDING_BATCH_SIZE

    async def is_available(self) -> bool:
        return bool(self.api_key)

    async def embed(self, texts: list[str], input_type: str = "search_document") -> list[list[float]]:
        if not texts:
            return []

        if not await self.is_available():
            raise EmbeddingError("Cohere API key not configured")

        all_embeddings: list[list[float]] = []

        for i in range(0, len(texts), self._batch_size):
            batch = texts[i : i + self._batch_size]
            embeddings = await self._embed_batch(batch, input_type)
            all_embeddings.extend(embeddings)

        return all_embeddings

    async def _embed_batch(self, texts: list[str], input_type: str) -> list[list[float]]:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                f"{self.base_url}/embed",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                    "Accept": "application/json",
                },
                json={
                    "texts": texts,
                    "model": self.model,
                    "input_type": input_type,
                    "embedding_types": ["float"],
                },
            )

            if resp.status_code != 200:
                raise EmbeddingError(f"Cohere embedding failed: {resp.text}")

            data = resp.json()
            embeddings = data.get("embeddings", {}).get("float", [])

            if not embeddings:
                raise EmbeddingError("No embeddings returned from Cohere")

            return embeddings

    async def embed_query(self, text: str) -> list[float]:
        embeddings = await self.embed([text], input_type="search_query")
        return embeddings[0] if embeddings else []

    async def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return await self.embed(texts, input_type="search_document")


cohere_embedding = CohereEmbeddingService()