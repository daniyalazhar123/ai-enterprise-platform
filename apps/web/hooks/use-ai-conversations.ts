"use client";

import { useCallback, useEffect, useState } from "react";
import {
  deleteConversation,
  getConversationMessages,
  listConversations,
} from "@/lib/ai-api";
import type { ChatMessage, Conversation } from "@/lib/ai-types";

export function useConversations() {
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchConversations = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await listConversations();
      setConversations(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load conversations");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchConversations();
  }, [fetchConversations]);

  const removeConversation = useCallback(async (id: string) => {
    try {
      await deleteConversation(id);
      setConversations((prev) => prev.filter((c) => c.id !== id));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to delete conversation");
    }
  }, []);

  const loadMessages = useCallback(async (id: string): Promise<ChatMessage[]> => {
    try {
      const data = await getConversationMessages(id);
      return data as unknown as ChatMessage[];
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load messages");
      return [];
    }
  }, []);

  return {
    conversations,
    loading,
    error,
    refetch: fetchConversations,
    removeConversation,
    loadMessages,
  };
}