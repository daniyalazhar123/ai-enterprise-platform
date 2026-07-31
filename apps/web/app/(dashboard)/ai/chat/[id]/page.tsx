"use client";

import { useParams, useRouter } from "next/navigation";
import { useCallback, useEffect } from "react";
import { AiErrorBoundary } from "@/components/ai/error-boundary";
import { StreamingChat } from "@/components/ai/streaming-chat";
import { useChat } from "@/hooks/use-ai-chat";
import { useConversations } from "@/hooks/use-ai-conversations";

export default function AIChatConversationPage() {
  const params = useParams();
  const router = useRouter();
  const conversationId = params.id as string;
  const { messages, isStreaming, sendMessage, setMessagesFromHistory } = useChat();
  const { loadMessages } = useConversations();

  useEffect(() => {
    if (conversationId) {
      loadMessages(conversationId).then((history) => {
        if (history.length > 0) {
          setMessagesFromHistory(history, conversationId);
        }
      });
    }
  }, [conversationId, loadMessages, setMessagesFromHistory]);

  return (
    <AiErrorBoundary>
      <div className="flex h-[calc(100vh-3.5rem)]">
        <div className="flex-1 flex flex-col min-w-0">
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