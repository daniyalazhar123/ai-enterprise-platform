"use client";

import { motion } from "framer-motion";
import { Bot, ChevronLeft, Plus, Search } from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import { AiErrorBoundary } from "@/components/ai/error-boundary";
import { StreamingChat } from "@/components/ai/streaming-chat";
import { ChatSidebar } from "@/components/ai/chat-sidebar";
import { Button } from "@/components/ui/button";
import { useChat } from "@/hooks/use-ai-chat";
import { useConversations } from "@/hooks/use-ai-conversations";
import type { ChatMessage } from "@/lib/ai-types";

export default function AIChatPage() {
  const { messages, isStreaming, sendMessage, reset, setMessagesFromHistory } = useChat();
  const { conversations, loading: convLoading, removeConversation, loadMessages, refetch } = useConversations();
  const [sidebarOpen, setSidebarOpen] = useState(true);

  const handleSelectConversation = useCallback(async (id: string) => {
    const history = await loadMessages(id);
    if (history.length > 0) {
      setMessagesFromHistory(history, id);
    }
    if (window.innerWidth < 768) setSidebarOpen(false);
  }, [loadMessages, setMessagesFromHistory]);

  const handleNewChat = useCallback(() => {
    reset();
    refetch();
  }, [reset, refetch]);

  return (
    <AiErrorBoundary>
      <div className="flex h-[calc(100vh-3.5rem)]">
        <div
          className={`${
            sidebarOpen ? "w-72" : "w-0 md:w-0"
          } transition-all duration-200 overflow-hidden border-r bg-muted/10`}
        >
          <ChatSidebar
            conversations={conversations}
            activeId={undefined}
            onSelect={handleSelectConversation}
            onNew={handleNewChat}
            onDelete={removeConversation}
            loading={convLoading}
          />
        </div>
        <div className="flex-1 flex flex-col min-w-0">
          <div className="flex items-center gap-2 border-b px-4 py-2">
            <Button
              variant="ghost"
              size="icon"
              onClick={() => setSidebarOpen(!sidebarOpen)}
              aria-label="Toggle sidebar"
            >
              {sidebarOpen ? <ChevronLeft className="h-4 w-4" /> : <Bot className="h-4 w-4" />}
            </Button>
            <span className="text-sm font-medium">AI Chat</span>
            <Button variant="outline" size="sm" className="ml-auto gap-2" onClick={handleNewChat}>
              <Plus className="h-3 w-3" />
              New
            </Button>
          </div>
          <StreamingChat
            messages={messages}
            onSend={sendMessage}
            isStreaming={isStreaming}
          />
        </div>
      </div>
    </AiErrorBoundary>
  );
}