"use client";

import { useCallback, useState } from "react";
import { tutorSend } from "@/lib/ai-api";
import type { ChatMessage } from "@/lib/ai-types";

export function useTutor() {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [topic, setTopic] = useState("");
  const [conversationId, setConversationId] = useState<string | undefined>();
  const [error, setError] = useState<string | null>(null);

  const askTutor = useCallback(async (question: string) => {
    setIsLoading(true);
    setError(null);

    const userMsg: ChatMessage = {
      id: `user-${Date.now()}`,
      role: "user",
      content: question,
      created_at: new Date().toISOString(),
    };
    setMessages((prev) => [...prev, userMsg]);

    try {
      const response = await tutorSend({
        topic,
        question,
        conversation_id: conversationId,
      });

      setConversationId(response.conversation_id);

      const assistantMsg: ChatMessage = {
        id: `tutor-${Date.now()}`,
        role: "assistant",
        content: response.response,
        created_at: new Date().toISOString(),
      };
      setMessages((prev) => [...prev, assistantMsg]);

      if (response.guided_questions && response.guided_questions.length > 0) {
        const guideMsg: ChatMessage = {
          id: `guide-${Date.now()}`,
          role: "assistant",
          content: `**Guiding questions:**\n${response.guided_questions.map((q, i) => `${i + 1}. ${q}`).join("\n")}`,
          created_at: new Date().toISOString(),
        };
        setMessages((prev) => [...prev, guideMsg]);
      }

      return response;
    } catch (err) {
      const message = err instanceof Error ? err.message : "Tutor request failed";
      setError(message);
      const errorMsg: ChatMessage = {
        id: `error-${Date.now()}`,
        role: "assistant",
        content: `I encountered an error: ${message}. Please try again.`,
        created_at: new Date().toISOString(),
      };
      setMessages((prev) => [...prev, errorMsg]);
    } finally {
      setIsLoading(false);
    }
  }, [topic, conversationId]);

  const startNew = useCallback((newTopic: string) => {
    setMessages([]);
    setTopic(newTopic);
    setConversationId(undefined);
    setError(null);
  }, []);

  return {
    messages,
    isLoading,
    topic,
    error,
    askTutor,
    startNew,
  };
}