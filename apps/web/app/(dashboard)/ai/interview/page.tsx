"use client";

import { motion } from "framer-motion";
import { Briefcase, CheckCircle2, Loader2, Send, Star, TrendingUp } from "lucide-react";
import { useCallback, useState } from "react";
import { AiErrorBoundary } from "@/components/ai/error-boundary";
import { EmptyState } from "@/components/ai/empty-state";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Textarea } from "@/components/ui/textarea";
import { useInterview } from "@/hooks/use-ai-interview";

export default function AIInterviewPage() {
  const {
    currentQuestion,
    currentIndex,
    feedbacks,
    isLoading,
    isComplete,
    overallScore,
    error,
    start,
    submitAnswer,
    reset,
  } = useInterview();
  const [answer, setAnswer] = useState("");

  const handleStart = useCallback(async () => {
    await start();
  }, [start]);

  const handleSubmit = useCallback(async () => {
    if (!answer.trim() || isLoading) return;
    await submitAnswer(answer.trim());
    setAnswer("");
  }, [answer, isLoading, submitAnswer]);

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  return (
    <AiErrorBoundary>
      <div className="flex h-[calc(100vh-3.5rem)] flex-col">
        <div className="border-b px-6 py-3">
          <div className="flex items-center gap-2">
            <Briefcase className="h-5 w-5 text-primary" />
            <h1 className="text-lg font-semibold">Technical Interview</h1>
          </div>
        </div>

        <ScrollArea className="flex-1">
          <div className="mx-auto max-w-3xl py-6 px-6">
            {!currentQuestion && !isComplete ? (
              <div className="flex flex-col items-center justify-center py-24 text-center">
                <div className="inline-flex rounded-full bg-primary/10 p-4 mb-4">
                  <Briefcase className="h-8 w-8 text-primary" />
                </div>
                <h2 className="text-2xl font-bold mb-2">Practice Technical Interview</h2>
                <p className="text-muted-foreground max-w-md mb-8">
                  Get asked 8 technical questions across various topics. Each answer receives
                  detailed feedback with strengths and areas for improvement.
                </p>
                <Button onClick={handleStart} disabled={isLoading} size="lg">
                  {isLoading ? <Loader2 className="h-4 w-4 mr-2 animate-spin" /> : <TrendingUp className="h-4 w-4 mr-2" />}
                  Start Interview
                </Button>
                {error && <p className="text-sm text-destructive mt-4">{error}</p>}
              </div>
            ) : isComplete ? (
              <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="space-y-6">
                <div className="text-center">
                  <div className="inline-flex rounded-full bg-emerald-500/10 p-4 mb-4">
                    <CheckCircle2 className="h-8 w-8 text-emerald-500" />
                  </div>
                  <h2 className="text-2xl font-bold mb-1">Interview Complete!</h2>
                  <p className="text-muted-foreground mb-6">Great job completing all questions.</p>
                  <div className="flex items-center justify-center gap-4 mb-8">
                    <div className="text-4xl font-bold text-primary">{overallScore}%</div>
                    <Badge variant={overallScore >= 80 ? "success" : overallScore >= 60 ? "warning" : "destructive"} className="text-sm">
                      {overallScore >= 80 ? "Strong Hire" : overallScore >= 60 ? "Hire" : "Needs Improvement"}
                    </Badge>
                  </div>
                </div>

                <div className="space-y-4">
                  {feedbacks.map((fb, i) => (
                    <Card key={i} className="p-4">
                      <div className="flex items-center gap-2 mb-2">
                        <Star className="h-4 w-4 text-amber-500" />
                        <span className="font-medium text-sm">Question {i + 1}</span>
                        <Badge variant="secondary" className="ml-auto">{fb.score}/100</Badge>
                      </div>
                      <p className="text-xs text-muted-foreground mb-2">{fb.answer?.slice(0, 200)}</p>
                      <p className="text-sm mb-2">{fb.feedback}</p>
                      {fb.strengths?.length > 0 && (
                        <div className="mb-1">
                          <p className="text-xs font-medium text-emerald-600 dark:text-emerald-400">Strengths:</p>
                          <ul className="text-xs text-muted-foreground list-disc list-inside">
                            {fb.strengths.map((s, j) => <li key={j}>{s}</li>)}
                          </ul>
                        </div>
                      )}
                      {fb.improvements?.length > 0 && (
                        <div>
                          <p className="text-xs font-medium text-amber-600 dark:text-amber-400">Improvements:</p>
                          <ul className="text-xs text-muted-foreground list-disc list-inside">
                            {fb.improvements.map((imp, j) => <li key={j}>{imp}</li>)}
                          </ul>
                        </div>
                      )}
                    </Card>
                  ))}
                </div>

                <div className="text-center">
                  <Button onClick={reset} variant="outline" size="lg">
                    Try Again
                  </Button>
                </div>
              </motion.div>
            ) : (
              <div className="space-y-6">
                <div className="flex items-center justify-between">
                  <p className="text-sm text-muted-foreground">
                    Question {currentIndex + 1} of 8
                  </p>
                  <Badge variant="secondary">{currentQuestion?.category}</Badge>
                </div>

                <Progress value={((currentIndex + 1) / 8) * 100} className="h-2" />

                <motion.div
                  key={currentIndex}
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                >
                  <Card className="p-6 space-y-4">
                    <div className="flex items-start gap-3">
                      <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-primary/10 text-sm font-medium text-primary">
                        {currentIndex + 1}
                      </div>
                      <div>
                        <h3 className="text-lg font-medium mb-1">{currentQuestion?.question}</h3>
                        <Badge variant="outline" className="text-xs">
                          {currentQuestion?.difficulty}
                        </Badge>
                        {currentQuestion?.hints && currentQuestion.hints.length > 0 && (
                          <div className="mt-3">
                            <details className="text-sm">
                              <summary className="cursor-pointer text-primary text-xs">Need a hint?</summary>
                              <ul className="mt-2 space-y-1 text-muted-foreground">
                                {currentQuestion.hints.map((hint, i) => (
                                  <li key={i} className="text-xs">💡 {hint}</li>
                                ))}
                              </ul>
                            </details>
                          </div>
                        )}
                      </div>
                    </div>
                  </Card>
                </motion.div>

                {feedbacks.length > currentIndex && feedbacks[currentIndex] && (
                  <Card className="p-4 border-l-4 border-l-primary bg-muted/30">
                    <p className="text-xs font-medium text-primary mb-1">Feedback on your answer:</p>
                    <p className="text-sm">{feedbacks[currentIndex].feedback}</p>
                  </Card>
                )}

                {feedbacks.length <= currentIndex && (
                  <div className="space-y-3">
                    <Textarea
                      value={answer}
                      onChange={(e) => setAnswer(e.target.value)}
                      onKeyDown={handleKeyDown}
                      placeholder="Type your answer..."
                      disabled={isLoading}
                      rows={5}
                      className="resize-none"
                    />
                    <div className="flex justify-end">
                      <Button onClick={handleSubmit} disabled={isLoading || !answer.trim()}>
                        {isLoading ? <Loader2 className="h-4 w-4 mr-2 animate-spin" /> : <Send className="h-4 w-4 mr-2" />}
                        Submit Answer
                      </Button>
                    </div>
                  </div>
                )}

                {error && <p className="text-sm text-destructive text-center">{error}</p>}
              </div>
            )}
          </div>
        </ScrollArea>
      </div>
    </AiErrorBoundary>
  );
}