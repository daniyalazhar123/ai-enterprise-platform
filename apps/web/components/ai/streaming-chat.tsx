"use client";

import { motion } from "framer-motion";
import { useState } from "react";
import { ScrollArea } from "@/components/ui/scroll-area";
import { ChatInput } from "./chat-input";
import { ChatMessageBubble, TypingIndicator } from "./chat-message";
import type { ChatMessage } from "@/lib/ai-types";

interface StreamingChatProps {
  messages: ChatMessage[];
  onSend: (message: string) => void;
  isStreaming: boolean;
  streamingContent?: string;
  disabled?: boolean;
  placeholder?: string;
}

export function StreamingChat({
  messages,
  onSend,
  isStreaming,
  streamingContent,
  disabled,
  placeholder,
}: StreamingChatProps) {
  return (
    <div className="flex h-full flex-col">
      <ScrollArea className="flex-1">
        <div className="mx-auto max-w-3xl">
          {messages.length === 0 && !isStreaming ? (
            <div className="flex flex-col items-center justify-center py-24 text-center px-4">
              <div className="rounded-full bg-gradient-to-br from-indigo-500/10 to-purple-600/10 p-6 mb-6">
                <motion.div
                  animate={{ rotate: 360 }}
                  transition={{ duration: 20, repeat: Infinity, ease: "linear" }}
                  className="h-12 w-12 rounded-full bg-gradient-to-br from-indigo-500 to-purple-600"
                />
              </div>
              <h2 className="text-2xl font-bold mb-2">How can I help you today?</h2>
              <p className="text-muted-foreground text-sm max-w-md">
                Ask me anything about your textbook content, or enable RAG to search through your uploaded documents.
              </p>
            </div>
          ) : (
            <div className="divide-y">
              {messages.map((msg, i) => (
                <motion.div
                  key={msg.id}
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ duration: 0.2, delay: i * 0.02 }}
                >
                  <ChatMessageBubble message={msg} />
                </motion.div>
              ))}
              {isStreaming && streamingContent && (
                <ChatMessageBubble
                  message={{
                    id: "streaming",
                    role: "assistant",
                    content: streamingContent,
                    created_at: new Date().toISOString(),
                  }}
                  isStreaming
                />
              )}
              {isStreaming && !streamingContent && <TypingIndicator />}
            </div>
          )}
        </div>
      </ScrollArea>
      <ChatInput onSend={onSend} disabled={disabled} placeholder={placeholder} />
    </div>
  );
}