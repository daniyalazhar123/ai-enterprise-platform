from __future__ import annotations

from typing import Any

from apps.api.app.ai.documents.parser import document_processor
from apps.api.app.ai.vectorstore.qdrant_service import qdrant_service
from apps.api.app.core.exceptions import DocumentProcessingError, NotFoundError


_DOCUMENTS_STORE: dict[str, list[dict[str, Any]]] = {}


class DocumentService:
    async def process_and_store(
        self,
        file_path: str,
        filename: str,
        content_type: str,
        user_id: str,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        doc_id, chunks = await document_processor.process(
            file_path=file_path,
            filename=filename,
            content_type=content_type,
            metadata={
                "user_id": user_id,
                **(metadata or {}),
            },
        )

        stored_chunks = await qdrant_service.upsert_points(chunks)

        _DOCUMENTS_STORE[doc_id] = chunks

        return {
            "id": doc_id,
            "filename": filename,
            "content_type": content_type,
            "chunks": stored_chunks,
            "metadata": metadata or {},
        }

    async def list_documents(
        self,
        user_id: str,
        limit: int = 50,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        all_docs: list[dict[str, Any]] = []
        seen_ids: set[str] = set()

        for doc_id, chunks in _DOCUMENTS_STORE.items():
            if chunks and any(
                c.get("metadata", {}).get("user_id") == user_id
                for c in chunks
            ):
                if doc_id not in seen_ids:
                    seen_ids.add(doc_id)
                    first_chunk = chunks[0]
                    md = first_chunk.get("metadata", {})
                    all_docs.append({
                        "id": doc_id,
                        "filename": md.get("filename", "Unknown"),
                        "content_type": md.get("content_type", "Unknown"),
                        "chunk_count": len(chunks),
                        "file_size": md.get("file_size", 0),
                        "created_at": md.get("created_at"),
                    })

        return all_docs[offset:offset + limit]

    async def delete_document(self, doc_id: str, user_id: str) -> bool:
        chunks = _DOCUMENTS_STORE.pop(doc_id, None)
        if not chunks:
            return False

        point_ids = [c.get("id", f"{doc_id}_{i}") for i, c in enumerate(chunks)]
        await qdrant_service.delete_points(point_ids)
        return True


document_service = DocumentService()