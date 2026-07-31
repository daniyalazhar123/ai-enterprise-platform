"use client";

import { Bot, Loader2, MessageSquare, Sparkles, User } from "lucide-react";
import { MarkdownRenderer } from "@/components/ai/markdown-renderer";
import { CitationCard } from "@/components/ai/citation-card";
import { cn } from "@/lib/utils";
import type { ChatMessage, SourceCitation } from "@/lib/ai-types";

interface ChatMessageProps {
  message: ChatMessage;
  isStreaming?: boolean;
}

export function ChatMessageBubble({ message, isStreaming }: ChatMessageProps) {
  const isUser = message.role === "user";
  const isAssistant = message.role === "assistant";

  return (
    <div
      className={cn(
        "flex gap-3 p-4 md:p-6 group",
        isUser && "bg-muted/30",
      )}
    >
      <div
        className={cn(
          "flex h-8 w-8 shrink-0 items-center justify-center rounded-full",
          isUser && "bg-primary text-primary-foreground",
          isAssistant && "bg-gradient-to-br from-indigo-500 to-purple-600 text-white",
        )}
      >
        {isUser ? <User className="h-4 w-4" /> : <Bot className="h-4 w-4" />}
      </div>
      <div className="flex-1 min-w-0 space-y-2">
        <div className="flex items-center gap-2">
          <span className="text-xs font-medium">
            {isUser ? "You" : "AI Assistant"}
          </span>
          {message.model && !isUser && (
            <span className="text-[10px] text-muted-foreground bg-muted px-1.5 py-0.5 rounded">
              {message.model}
            </span>
          )}
          {isStreaming && (
            <span className="flex items-center gap-1 text-xs text-muted-foreground">
              <Sparkles className="h-3 w-3 animate-pulse text-primary" />
              Streaming
            </span>
          )}
        </div>
        <div className="text-sm leading-relaxed">
          <MarkdownRenderer content={message.content} />
        </div>
        {message.citations && message.citations.length > 0 && (
          <div className="space-y-2 pt-2 border-t">
            <p className="text-xs font-medium text-muted-foreground flex items-center gap-1">
              <MessageSquare className="h-3 w-3" />
              Sources
            </p>
            <div className="grid gap-2 sm:grid-cols-2">
              {message.citations.map((citation: SourceCitation, i: number) => (
                <CitationCard key={citation.id} citation={citation} index={i} />
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

export function TypingIndicator() {
  return (
    <div className="flex gap-3 p-4 md:p-6">
      <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-gradient-to-br from-indigo-500 to-purple-600 text-white">
        <Bot className="h-4 w-4" />
      </div>
      <div className="flex items-center gap-2">
        <Loader2 className="h-4 w-4 animate-spin text-muted-foreground" />
        <span className="text-sm text-muted-foreground">Thinking...</span>
      </div>
    </div>
  );
}