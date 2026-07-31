from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from apps.api.app.core.cache import get_redis
from apps.api.app.core.config import settings


class ConversationMemory:
    def __init__(self, user_id: str, conversation_id: str | None = None, prefix: str = "chat") -> None:
        self.user_id = user_id
        self.conversation_id = conversation_id
        self.prefix = prefix
        self._key_prefix = f"conv:{self.prefix}"

    def _conversation_key(self, cid: str) -> str:
        return f"{self._key_prefix}:{self.user_id}:{cid}"

    def _messages_key(self, cid: str) -> str:
        return f"{self._key_prefix}:{self.user_id}:{cid}:messages"

    def _metadata_key(self, cid: str) -> str:
        return f"{self._key_prefix}:{self.user_id}:{cid}:meta"

    async def get_or_create(self) -> dict[str, Any]:
        r = await get_redis()

        if self.conversation_id:
            exists = await r.exists(self._conversation_key(self.conversation_id))
            if exists:
                return await self.get_conversation(self.conversation_id)

        cid = self.conversation_id or str(uuid4())
        now = datetime.now(timezone.utc).isoformat()

        conv_data = {
            "id": cid,
            "user_id": self.user_id,
            "title": f"{self.prefix.capitalize()} session",
            "created_at": now,
            "updated_at": now,
            "message_count": 0,
            "metadata": json.dumps({}),
        }

        await r.hset(self._conversation_key(cid), mapping=conv_data)
        await r.expire(self._conversation_key(cid), settings.MEMORY_REDIS_TTL)
        await r.expire(self._messages_key(cid), settings.MEMORY_REDIS_TTL)

        self.conversation_id = cid
        return conv_data

    async def get_conversation(self, cid: str) -> dict[str, Any]:
        r = await get_redis()
        data = await r.hgetall(self._conversation_key(cid))
        if not data:
            return await self.get_or_create()
        return {
            "id": data.get("id", cid),
            "user_id": data.get("user_id", self.user_id),
            "title": data.get("title", "Chat session"),
            "created_at": data.get("created_at", ""),
            "updated_at": data.get("updated_at", ""),
            "message_count": int(data.get("message_count", 0)),
            "metadata": json.loads(data.get("metadata", "{}")),
        }

    async def add_message(self, message: dict[str, Any]) -> None:
        r = await get_redis()
        cid = self.conversation_id
        if not cid:
            conv = await self.get_or_create()
            cid = conv["id"]

        msg = {
            **message,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        await r.rpush(self._messages_key(cid), json.dumps(msg))

        now = datetime.now(timezone.utc).isoformat()
        await r.hset(self._conversation_key(cid), "updated_at", now)
        await r.hincrby(self._conversation_key(cid), "message_count", 1)

        ttl = settings.MEMORY_REDIS_TTL
        await r.expire(self._messages_key(cid), ttl)
        await r.expire(self._conversation_key(cid), ttl)

    async def get_history(self) -> list[dict[str, Any]]:
        r = await get_redis()
        cid = self.conversation_id
        if not cid:
            return []

        raw = await r.lrange(self._messages_key(cid), 0, -1)
        messages = [json.loads(m) for m in raw]
        return messages

    async def list_conversations(self) -> list[dict[str, Any]]:
        r = await get_redis()
        pattern = f"{self._key_prefix}:{self.user_id}:*"
        keys = await r.keys(pattern)
        conv_ids = set()
        for key in keys:
            parts = key.split(":")
            if len(parts) >= 3:
                cid = parts[-1]
                if cid != "messages" and cid != "meta":
                    conv_ids.add(cid)

        conversations = []
        for cid in conv_ids:
            try:
                conv = await self.get_conversation(cid)
                conversations.append(conv)
            except Exception:
                continue

        conversations.sort(key=lambda c: c.get("updated_at", ""), reverse=True)
        return conversations

    async def delete_conversation(self, cid: str) -> None:
        r = await get_redis()
        await r.delete(self._conversation_key(cid))
        await r.delete(self._messages_key(cid))
        await r.delete(self._metadata_key(cid))

    async def save_metadata(self, metadata: dict[str, Any]) -> None:
        r = await get_redis()
        cid = self.conversation_id
        if not cid:
            return
        await r.hset(self._conversation_key(cid), "metadata", json.dumps(metadata))

    async def get_metadata(self) -> dict[str, Any]:
        r = await get_redis()
        cid = self.conversation_id
        if not cid:
            return {}
        raw = await r.hget(self._conversation_key(cid), "metadata")
        if raw:
            return json.loads(raw)
        return {}