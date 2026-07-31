"use client";

import { AnimatePresence, motion } from "framer-motion";
import {
  CheckCircle2,
  ChevronLeft,
  ChevronRight,
  GraduationCap,
  Loader2,
  RefreshCw,
  Sparkles,
  XCircle,
} from "lucide-react";
import { useCallback } from "react";
import { AiErrorBoundary } from "@/components/ai/error-boundary";
import { EmptyState } from "@/components/ai/empty-state";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { SkeletonQuiz } from "@/components/ui/skeleton";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Input } from "@/components/ui/input";
import { useQuiz } from "@/hooks/use-ai-quiz";
import { cn } from "@/lib/utils";

const DIFFICULTIES = [
  { value: "easy", label: "Easy" },
  { value: "medium", label: "Medium" },
  { value: "hard", label: "Hard" },
];

export default function AIQuizPage() {
  const {
    questions,
    currentIndex,
    answers,
    results,
    score,
    isLoading,
    error,
    topic,
    generate,
    answer,
    nextQuestion,
    prevQuestion,
    submit,
    reset,
  } = useQuiz();

  const handleGenerate = useCallback(async () => {
    const topicInput = (document.getElementById("quiz-topic") as HTMLInputElement)?.value;
    if (!topicInput?.trim()) return;
    const diffSelect = (document.querySelector("[data-difficulty]") as HTMLElement);
    await generate(topicInput.trim(), 5, "medium");
  }, [generate]);

  const isAnswered = (id: string) => id in answers;
  const allAnswered = questions.length > 0 && questions.every((q) => q.id in answers);

  return (
    <AiErrorBoundary>
      <div className="flex h-[calc(100vh-3.5rem)] flex-col">
        <div className="border-b px-6 py-3">
          <div className="flex items-center gap-2">
            <GraduationCap className="h-5 w-5 text-primary" />
            <h1 className="text-lg font-semibold">AI Quiz</h1>
          </div>
        </div>

        <ScrollArea className="flex-1">
          <div className="mx-auto max-w-3xl py-6 px-6">
            {questions.length === 0 && !results ? (
              <div className="space-y-8">
                <div className="text-center">
                  <div className="inline-flex rounded-full bg-primary/10 p-4 mb-4">
                    <Sparkles className="h-8 w-8 text-primary" />
                  </div>
                  <h2 className="text-2xl font-bold mb-2">Generate a Quiz</h2>
                  <p className="text-muted-foreground">
                    Enter a topic and generate questions to test your knowledge.
                  </p>
                </div>

                <Card className="p-6 max-w-md mx-auto space-y-4">
                  <div className="space-y-2">
                    <label className="text-sm font-medium">Topic</label>
                    <Input id="quiz-topic" placeholder="e.g., Python basics" />
                  </div>
                  <div className="space-y-2">
                    <label className="text-sm font-medium">Difficulty</label>
                    <Select defaultValue="medium">
                      <SelectTrigger data-difficulty>
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        {DIFFICULTIES.map((d) => (
                          <SelectItem key={d.value} value={d.value}>{d.label}</SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>
                  <Button onClick={handleGenerate} disabled={isLoading} className="w-full" size="lg">
                    {isLoading ? <Loader2 className="h-4 w-4 mr-2 animate-spin" /> : <Sparkles className="h-4 w-4 mr-2" />}
                    Generate Quiz
                  </Button>
                  {error && <p className="text-sm text-destructive text-center">{error}</p>}
                </Card>
              </div>
            ) : isLoading ? (
              <SkeletonQuiz />
            ) : results ? (
              <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="space-y-6">
                <div className="text-center">
                  <div className="inline-flex rounded-full bg-primary/10 p-4 mb-4">
                    <CheckCircle2 className="h-8 w-8 text-primary" />
                  </div>
                  <h2 className="text-2xl font-bold mb-1">Quiz Complete!</h2>
                  <p className="text-muted-foreground mb-4">{topic}</p>
                  <div className="flex items-center justify-center gap-4">
                    <div className="text-4xl font-bold text-primary">{score}%</div>
                    <Badge variant={score >= 80 ? "success" : score >= 50 ? "warning" : "destructive"} className="text-sm">
                      {score >= 80 ? "Excellent" : score >= 50 ? "Good" : "Needs Practice"}
                    </Badge>
                  </div>
                </div>

                <div className="space-y-4">
                  {results.map((result, i) => (
                    <Card key={result.question_id} className="p-4">
                      <div className="flex items-start gap-3">
                        {result.correct ? (
                          <CheckCircle2 className="h-5 w-5 text-emerald-500 mt-0.5 shrink-0" />
                        ) : (
                          <XCircle className="h-5 w-5 text-destructive mt-0.5 shrink-0" />
                        )}
                        <div className="flex-1">
                          <p className="font-medium text-sm">
                            {questions.find((q) => q.id === result.question_id)?.question || `Question ${i + 1}`}
                          </p>
                          <p className="text-xs text-muted-foreground mt-1">
                            {result.correct ? "Correct!" : `Correct answer: ${questions.find((q) => q.id === result.question_id)?.options[result.correct_answer]}`}
                          </p>
                          <p className="text-xs text-muted-foreground mt-1">{result.explanation}</p>
                        </div>
                      </div>
                    </Card>
                  ))}
                </div>

                <div className="text-center">
                  <Button onClick={reset} variant="outline" size="lg">
                    <RefreshCw className="h-4 w-4 mr-2" />
                    Try Another Quiz
                  </Button>
                </div>
              </motion.div>
            ) : (
              <div className="space-y-6">
                <div className="flex items-center justify-between">
                  <div>
                    <h2 className="text-lg font-semibold">{topic}</h2>
                    <p className="text-sm text-muted-foreground">
                      Question {currentIndex + 1} of {questions.length}
                    </p>
                  </div>
                  <Badge variant="secondary">
                    {Object.keys(answers).length}/{questions.length} answered
                  </Badge>
                </div>

                <Progress value={((currentIndex + 1) / questions.length) * 100} className="h-2" />

                <AnimatePresence mode="wait">
                  <motion.div
                    key={currentIndex}
                    initial={{ opacity: 0, x: 20 }}
                    animate={{ opacity: 1, x: 0 }}
                    exit={{ opacity: 0, x: -20 }}
                    className="space-y-4"
                  >
                    <Card className="p-6">
                      <h3 className="text-lg font-medium mb-4">
                        {questions[currentIndex]?.question}
                      </h3>
                      <div className="space-y-2">
                        {questions[currentIndex]?.options.map((option, optIndex) => (
                          <button
                            key={optIndex}
                            onClick={() => answer(questions[currentIndex].id, optIndex)}
                            className={cn(
                              "w-full text-left rounded-lg border p-3 text-sm transition-colors",
                              answers[questions[currentIndex].id] === optIndex
                                ? "border-primary bg-primary/10 text-primary"
                                : "hover:bg-accent hover:border-border",
                            )}
                          >
                            <span className="inline-flex items-center justify-center w-6 h-6 rounded-full bg-muted text-xs font-medium mr-3">
                              {String.fromCharCode(65 + optIndex)}
                            </span>
                            {option}
                          </button>
                        ))}
                      </div>
                    </Card>
                  </motion.div>
                </AnimatePresence>

                <div className="flex items-center justify-between">
                  <Button variant="outline" onClick={prevQuestion} disabled={currentIndex === 0}>
                    <ChevronLeft className="h-4 w-4 mr-1" /> Previous
                  </Button>

                  {currentIndex === questions.length - 1 ? (
                    <Button onClick={submit} disabled={!allAnswered || isLoading} size="lg">
                      {isLoading ? <Loader2 className="h-4 w-4 mr-2 animate-spin" /> : null}
                      Submit Quiz
                    </Button>
                  ) : (
                    <Button onClick={nextQuestion}>
                      Next <ChevronRight className="h-4 w-4 ml-1" />
                    </Button>
                  )}
                </div>
              </div>
            )}
          </div>
        </ScrollArea>
      </div>
    </AiErrorBoundary>
  );
}