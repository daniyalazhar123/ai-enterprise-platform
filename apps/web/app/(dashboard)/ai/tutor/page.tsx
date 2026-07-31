"use client";

import { motion } from "framer-motion";
import { Bot, BookOpen, Sparkles, Loader2, Send, RefreshCw } from "lucide-react";
import { useCallback, useState } from "react";
import { AiErrorBoundary } from "@/components/ai/error-boundary";
import { ChatMessageBubble } from "@/components/ai/chat-message";
import { EmptyState } from "@/components/ai/empty-state";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { ScrollArea } from "@/components/ui/scroll-area";
import { useTutor } from "@/hooks/use-ai-tutor";
import type { ChatMessage } from "@/lib/ai-types";

const TOPICS = [
  { id: "python", label: "Python", icon: "🐍", desc: "Variables, functions, OOP" },
  { id: "javascript", label: "JavaScript", icon: "📜", desc: "Async, closures, DOM" },
  { id: "algorithms", label: "Algorithms", icon: "🧮", desc: "Sorting, searching, DP" },
  { id: "data-structures", label: "Data Structures", icon: "📊", desc: "Trees, graphs, hash tables" },
  { id: "react", label: "React", icon: "⚛️", desc: "Hooks, state, components" },
  { id: "sql", label: "SQL", icon: "🗄️", desc: "Queries, joins, indexing" },
];

export default function AITutorPage() {
  const { messages, isLoading, topic, error, askTutor, startNew } = useTutor();
  const [question, setQuestion] = useState("");
  const [selectedTopic, setSelectedTopic] = useState<string | null>(null);

  const handleTopicSelect = useCallback((topicId: string) => {
    setSelectedTopic(topicId);
    startNew(topicId);
  }, [startNew]);

  const handleAsk = useCallback(() => {
    if (!question.trim() || isLoading) return;
    askTutor(question.trim());
    setQuestion("");
  }, [question, isLoading, askTutor]);

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleAsk();
    }
  };

  return (
    <AiErrorBoundary>
      <div className="flex h-[calc(100vh-3.5rem)] flex-col">
        <div className="border-b px-6 py-3">
          <div className="flex items-center gap-2">
            <Bot className="h-5 w-5 text-primary" />
            <h1 className="text-lg font-semibold">AI Tutor</h1>
            {topic && (
              <span className="text-sm text-muted-foreground ml-2">
                — {TOPICS.find((t) => t.id === topic)?.label || topic}
              </span>
            )}
          </div>
        </div>

        <ScrollArea className="flex-1">
          <div className="mx-auto max-w-3xl py-6">
            {!selectedTopic ? (
              <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="px-6">
                <div className="text-center mb-8">
                  <div className="inline-flex rounded-full bg-primary/10 p-4 mb-4">
                    <BookOpen className="h-8 w-8 text-primary" />
                  </div>
                  <h2 className="text-2xl font-bold mb-2">What would you like to learn?</h2>
                  <p className="text-muted-foreground">
                    Select a topic and ask questions. I&apos;ll guide you step by step.
                  </p>
                </div>
                <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
                  {TOPICS.map((t) => (
                    <motion.button
                      key={t.id}
                      whileHover={{ scale: 1.02 }}
                      whileTap={{ scale: 0.98 }}
                      onClick={() => handleTopicSelect(t.id)}
                      className="flex flex-col items-center gap-3 rounded-xl border p-6 text-center transition-colors hover:border-primary hover:bg-accent"
                    >
                      <span className="text-3xl">{t.icon}</span>
                      <div>
                        <p className="font-semibold">{t.label}</p>
                        <p className="text-xs text-muted-foreground mt-1">{t.desc}</p>
                      </div>
                    </motion.button>
                  ))}
                </div>
              </motion.div>
            ) : messages.length === 0 && !isLoading ? (
              <div className="flex flex-col items-center justify-center py-24 px-6 text-center">
                <Sparkles className="h-12 w-12 text-primary mb-4" />
                <h3 className="text-xl font-semibold mb-2">
                  Ask me about {TOPICS.find((t) => t.id === selectedTopic)?.label || selectedTopic}
                </h3>
                <p className="text-sm text-muted-foreground mb-6 max-w-md">
                  I use the Socratic method — I&apos;ll guide you with questions rather than giving direct answers.
                </p>
                <Button variant="outline" onClick={() => { setSelectedTopic(null); startNew(""); }}>
                  <RefreshCw className="h-4 w-4 mr-2" />
                  Change topic
                </Button>
              </div>
            ) : (
              <div className="divide-y px-6">
                {messages.map((msg, i) => (
                  <motion.div
                    key={msg.id}
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: i * 0.03 }}
                  >
                    <ChatMessageBubble message={msg} />
                  </motion.div>
                ))}
                {isLoading && (
                  <div className="flex items-center gap-3 p-4 text-muted-foreground">
                    <Loader2 className="h-4 w-4 animate-spin" />
                    <span className="text-sm">Thinking...</span>
                  </div>
                )}
              </div>
            )}
          </div>
        </ScrollArea>

        {selectedTopic && (
          <div className="border-t bg-background p-4">
            <div className="mx-auto flex max-w-3xl items-center gap-2">
              <Input
                value={question}
                onChange={(e) => setQuestion(e.target.value)}
                onKeyDown={handleKeyDown}
                placeholder={isLoading ? "Waiting for response..." : "Ask your question..."}
                disabled={isLoading}
                className="flex-1"
              />
              <Button onClick={handleAsk} disabled={isLoading || !question.trim()} size="icon">
                {isLoading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Send className="h-4 w-4" />}
              </Button>
            </div>
          </div>
        )}
      </div>
    </AiErrorBoundary>
  );
}