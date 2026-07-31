"use client";

import { useCallback, useRef, useState } from "react";
import { chatSend } from "@/lib/ai-api";
import type { ChatMessage, SourceCitation } from "@/lib/ai-types";

interface UseChatOptions {
  onError?: (error: Error) => void;
}

export function useChat({ onError }: UseChatOptions = {}) {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [isStreaming, setIsStreaming] = useState(false);
  const [streamingContent, setStreamingContent] = useState("");
  const [conversationId, setConversationId] = useState<string | undefined>();
  const abortRef = useRef<AbortController | null>(null);

  const sendMessage = useCallback(async (content: string, useRag = false) => {
    setIsStreaming(true);
    const userMsg: ChatMessage = {
      id: `user-${Date.now()}`,
      role: "user",
      content,
      created_at: new Date().toISOString(),
    };

    setMessages((prev) => [...prev, userMsg]);
    setStreamingContent("");

    try {
      const response = await chatSend({
        message: content,
        conversation_id: conversationId,
        use_rag: useRag,
      });

      setConversationId(response.conversation_id);

      setMessages((prev) => [
        ...prev,
        {
          id: `assistant-${Date.now()}`,
          role: "assistant",
          content: response.message.content,
          created_at: response.message.created_at,
          citations: response.citations,
          model: response.model,
        },
      ]);
    } catch (err) {
      const error = err instanceof Error ? err : new Error("Chat failed");
      onError?.(error);
      setMessages((prev) => [
        ...prev,
        {
          id: `error-${Date.now()}`,
          role: "assistant",
          content: `I'm sorry, I encountered an error: ${error.message}. Please try again.`,
          created_at: new Date().toISOString(),
        },
      ]);
    } finally {
      setIsStreaming(false);
      setStreamingContent("");
    }
  }, [conversationId, onError]);

  const stopStreaming = useCallback(() => {
    abortRef.current?.abort();
    setIsStreaming(false);
  }, []);

  const reset = useCallback(() => {
    setMessages([]);
    setConversationId(undefined);
    setStreamingContent("");
    setIsStreaming(false);
  }, []);

  const setMessagesFromHistory = useCallback((history: ChatMessage[], convId: string) => {
    setMessages(history);
    setConversationId(convId);
  }, []);

  return {
    messages,
    isStreaming,
    streamingContent,
    conversationId,
    sendMessage,
    stopStreaming,
    reset,
    setMessagesFromHistory,
  };
}