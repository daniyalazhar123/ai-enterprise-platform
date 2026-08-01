from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from apps.api.app.core.cache import get_redis
from apps.api.app.core.config import settings


class ConversationMemory:
    def __init__(
        self,
        user_id: str | None = None,
        conversation_id: str | None = None,
        prefix: str = "chat",
    ) -> None:
        self.user_id = user_id
        self.conversation_id = conversation_id
        self.prefix = prefix
        self._key_prefix = f"conv:{self.prefix}"

    def _conversation_key(self, user_id: str, cid: str) -> str:
        return f"{self._key_prefix}:{user_id}:{cid}"

    def _messages_key(self, user_id: str, cid: str) -> str:
        return f"{self._key_prefix}:{user_id}:{cid}:messages"

    def _metadata_key(self, user_id: str, cid: str) -> str:
        return f"{self._key_prefix}:{user_id}:{cid}:meta"

    async def get_or_create(self) -> dict[str, Any]:
        r = await get_redis()
        user_id = self.user_id or "anonymous"

        if self.conversation_id:
            exists = await r.exists(self._conversation_key(user_id, self.conversation_id))
            if exists:
                return await self._load_conversation(r, user_id, self.conversation_id)

        cid = self.conversation_id or str(uuid4())
        now = datetime.now(timezone.utc).isoformat()

        conv_data = {
            "id": cid,
            "user_id": user_id,
            "title": f"{self.prefix.capitalize()} session",
            "created_at": now,
            "updated_at": now,
            "message_count": 0,
            "metadata": json.dumps({}),
        }

        await r.hset(self._conversation_key(user_id, cid), mapping=conv_data)
        await r.expire(self._conversation_key(user_id, cid), settings.MEMORY_REDIS_TTL)
        await r.expire(self._messages_key(user_id, cid), settings.MEMORY_REDIS_TTL)

        self.conversation_id = cid
        return {
            **conv_data,
            "metadata": json.loads(conv_data["metadata"]),
        }

    async def _load_conversation(self, r: Any, user_id: str, cid: str) -> dict[str, Any]:
        data = await r.hgetall(self._conversation_key(user_id, cid))
        return {
            "id": data.get("id", cid),
            "user_id": data.get("user_id", user_id),
            "title": data.get("title", "Chat session"),
            "created_at": data.get("created_at", ""),
            "updated_at": data.get("updated_at", ""),
            "message_count": int(data.get("message_count", 0)),
            "metadata": json.loads(data.get("metadata", "{}")),
        }

    async def get_conversation(self, cid: str) -> dict[str, Any]:
        r = await get_redis()
        user_id = self.user_id or "anonymous"
        data = await r.hgetall(self._conversation_key(user_id, cid))
        if not data:
            return await self.get_or_create()
        return await self._load_conversation(r, user_id, cid)

    async def add_message(self, message: dict[str, Any]) -> None:
        r = await get_redis()
        user_id = self.user_id or "anonymous"
        cid = self.conversation_id
        if not cid:
            conv = await self.get_or_create()
            cid = conv["id"]

        msg = {
            **message,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        await r.rpush(self._messages_key(user_id, cid), json.dumps(msg))

        now = datetime.now(timezone.utc).isoformat()
        await r.hset(self._conversation_key(user_id, cid), "updated_at", now)
        await r.hincrby(self._conversation_key(user_id, cid), "message_count", 1)

        ttl = settings.MEMORY_REDIS_TTL
        await r.expire(self._messages_key(user_id, cid), ttl)
        await r.expire(self._conversation_key(user_id, cid), ttl)

    async def get_history(self) -> list[dict[str, Any]]:
        r = await get_redis()
        user_id = self.user_id or "anonymous"
        cid = self.conversation_id
        if not cid:
            return []

        raw = await r.lrange(self._messages_key(user_id, cid), 0, -1)
        return [json.loads(m) for m in raw]

    async def list_conversations(
        self,
        user_id: str,
        limit: int = 50,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        r = await get_redis()
        pattern = f"{self._key_prefix}:{user_id}:*"
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
                conversations.append(await self._load_conversation(r, user_id, cid))
            except Exception:
                continue

        conversations.sort(key=lambda c: c.get("updated_at", ""), reverse=True)
        return conversations[offset:offset + limit]

    async def get_messages(self, conversation_id: str, user_id: str) -> list[dict[str, Any]]:
        r = await get_redis()
        exists = await r.exists(self._conversation_key(user_id, conversation_id))
        if not exists:
            return []

        raw = await r.lrange(self._messages_key(user_id, conversation_id), 0, -1)
        return [json.loads(m) for m in raw]

    async def delete_conversation(self, conversation_id: str, user_id: str) -> bool:
        r = await get_redis()
        key = self._conversation_key(user_id, conversation_id)
        existed = await r.exists(key)
        await r.delete(key)
        await r.delete(self._messages_key(user_id, conversation_id))
        await r.delete(self._metadata_key(user_id, conversation_id))
        return bool(existed)

    async def update_title(self, conversation_id: str, user_id: str, title: str) -> bool:
        r = await get_redis()
        key = self._conversation_key(user_id, conversation_id)
        existed = await r.exists(key)
        if existed:
            await r.hset(key, "title", title)
        return bool(existed)

    async def save_metadata(self, metadata: dict[str, Any]) -> None:
        r = await get_redis()
        user_id = self.user_id or "anonymous"
        cid = self.conversation_id
        if not cid:
            return
        await r.hset(self._conversation_key(user_id, cid), "metadata", json.dumps(metadata))

    async def get_metadata(self) -> dict[str, Any]:
        r = await get_redis()
        user_id = self.user_id or "anonymous"
        cid = self.conversation_id
        if not cid:
            return {}
        raw = await r.hget(self._conversation_key(user_id, cid), "metadata")
        if raw:
            return json.loads(raw)
        return {}


conversation_memory = ConversationMemory()
