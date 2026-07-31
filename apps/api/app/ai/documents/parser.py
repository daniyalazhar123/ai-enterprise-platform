from __future__ import annotations

import hashlib
import os
from pathlib import Path
from typing import Any
from uuid import uuid4

from apps.api.app.core.config import settings
from apps.api.app.core.exceptions import DocumentProcessingError, ValidationError


class DocumentParser:
    async def parse(self, file_path: str, content_type: str) -> str:
        raise NotImplementedError


class PdfParser(DocumentParser):
    async def parse(self, file_path: str, content_type: str) -> str:
        try:
            import pypdf
            text_parts: list[str] = []
            with open(file_path, "rb") as f:
                reader = pypdf.PdfReader(f)
                for page in reader.pages:
                    text = page.extract_text()
                    if text and text.strip():
                        text_parts.append(text.strip())
            return "\n\n".join(text_parts)
        except ImportError:
            raise DocumentProcessingError("pypdf is not installed. Install it with: pip install pypdf")
        except Exception as e:
            raise DocumentProcessingError(f"PDF parsing failed: {e}")


class MarkdownParser(DocumentParser):
    async def parse(self, file_path: str, content_type: str) -> str:
        try:
            path = Path(file_path)
            text = path.read_text(encoding="utf-8")
            return text
        except Exception as e:
            raise DocumentProcessingError(f"Markdown parsing failed: {e}")


class TextParser(DocumentParser):
    async def parse(self, file_path: str, content_type: str) -> str:
        try:
            path = Path(file_path)
            return path.read_text(encoding="utf-8")
        except Exception as e:
            raise DocumentProcessingError(f"Text parsing failed: {e}")


class DocumentProcessor:
    def __init__(self) -> None:
        self._parsers: dict[str, DocumentParser] = {
            "application/pdf": PdfParser(),
            "text/markdown": MarkdownParser(),
            "text/plain": TextParser(),
            "": TextParser(),
        }

    def get_parser(self, content_type: str, filename: str) -> DocumentParser:
        if content_type in self._parsers:
            return self._parsers[content_type]

        ext = Path(filename).suffix.lower()
        ext_map = {
            ".pdf": PdfParser(),
            ".md": MarkdownParser(),
            ".txt": TextParser(),
            ".mdx": MarkdownParser(),
        }
        parser = ext_map.get(ext)
        if parser:
            return parser
        raise ValidationError(f"Unsupported file type: {ext}")

    async def process(
        self,
        file_path: str,
        filename: str,
        content_type: str,
        metadata: dict[str, Any] | None = None,
    ) -> tuple[str, list[dict[str, Any]]]:
        file_size = os.path.getsize(file_path)
        max_size = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024
        if file_size > max_size:
            raise ValidationError(f"File size exceeds maximum of {settings.MAX_UPLOAD_SIZE_MB}MB")

        parser = self.get_parser(content_type, filename)
        text = await parser.parse(file_path, content_type)

        if not text.strip():
            raise DocumentProcessingError("No text content found in document")

        doc_id = str(uuid4())
        file_hash = hashlib.sha256(text.encode()).hexdigest()

        chunks = self.chunk_text(text)

        chunk_data = []
        for i, chunk in enumerate(chunks):
            chunk_data.append({
                "id": f"{doc_id}_{i}",
                "doc_id": doc_id,
                "chunk_index": i,
                "content": chunk,
                "metadata": {
                    "filename": filename,
                    "content_type": content_type,
                    "file_hash": file_hash,
                    "file_size": file_size,
                    **(metadata or {}),
                },
            })

        return doc_id, chunk_data

    def chunk_text(self, text: str) -> list[str]:
        if not text.strip():
            return []

        sentences = text.replace("\n\n", "\n").split("\n")
        chunks: list[str] = []
        current_chunk: list[str] = []
        current_length = 0

        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue

            sentence_len = len(sentence)

            if current_length + sentence_len > settings.CHUNK_SIZE and current_chunk:
                chunk_text = " ".join(current_chunk)
                if len(chunk_text) >= settings.CHUNK_MIN_SIZE:
                    chunks.append(chunk_text)

                overlap_text = []
                overlap_len = 0
                for s in reversed(current_chunk):
                    s_len = len(s)
                    if overlap_len + s_len > settings.CHUNK_OVERLAP:
                        break
                    overlap_text.insert(0, s)
                    overlap_len += s_len

                current_chunk = overlap_text
                current_length = overlap_len

            current_chunk.append(sentence)
            current_length += sentence_len

        if current_chunk:
            chunk_text = " ".join(current_chunk)
            if len(chunk_text) >= settings.CHUNK_MIN_SIZE:
                chunks.append(chunk_text)

        return chunks


document_processor = DocumentProcessor()