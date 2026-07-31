"use client";

import { motion } from "framer-motion";
import { BookOpen, Brain, FileText, MessageSquare, Star, TrendingUp, Zap } from "lucide-react";
import { AiErrorBoundary } from "@/components/ai/error-boundary";
import { Badge } from "@/components/ui/badge";
import { Card } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import { ScrollArea } from "@/components/ui/scroll-area";
import type { ProgressData } from "@/lib/ai-types";

const MOCK_PROGRESS: ProgressData = {
  current_chapter: "Functions & Scope",
  completed_modules: ["Variables", "Data Types", "Control Flow", "Loops"],
  quiz_scores: { "Python Basics": 85, "Data Structures": 72 },
  interview_scores: { "Technical Interview 1": 78 },
  total_chat_messages: 47,
  documents_uploaded: 3,
};

export default function ProgressPage() {
  const progress = MOCK_PROGRESS;

  const moduleProgress = (progress.completed_modules.length / 10) * 100;
  const avgQuizScore = Object.values(progress.quiz_scores).reduce((a, b) => a + b, 0) / Math.max(Object.values(progress.quiz_scores).length, 1);
  const avgInterviewScore = Object.values(progress.interview_scores).reduce((a, b) => a + b, 0) / Math.max(Object.values(progress.interview_scores).length, 1);

  return (
    <AiErrorBoundary>
      <div className="flex h-[calc(100vh-3.5rem)] flex-col">
        <div className="border-b px-6 py-3">
          <h1 className="text-lg font-semibold">Progress Dashboard</h1>
        </div>

        <ScrollArea className="flex-1">
          <div className="mx-auto max-w-4xl py-6 px-6 space-y-6">
            <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
              <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0 }}>
                <Card className="p-4 space-y-2">
                  <div className="flex items-center gap-2 text-primary">
                    <BookOpen className="h-4 w-4" />
                    <span className="text-xs font-medium">Current Chapter</span>
                  </div>
                  <p className="text-lg font-semibold">{progress.current_chapter || "Not started"}</p>
                </Card>
              </motion.div>

              <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.1 }}>
                <Card className="p-4 space-y-2">
                  <div className="flex items-center gap-2 text-emerald-500">
                    <Zap className="h-4 w-4" />
                    <span className="text-xs font-medium">Modules</span>
                  </div>
                  <p className="text-lg font-semibold">{progress.completed_modules.length}/10</p>
                  <Progress value={moduleProgress} className="h-1.5" />
                </Card>
              </motion.div>

              <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.2 }}>
                <Card className="p-4 space-y-2">
                  <div className="flex items-center gap-2 text-amber-500">
                    <Brain className="h-4 w-4" />
                    <span className="text-xs font-medium">Quiz Avg</span>
                  </div>
                  <p className="text-lg font-semibold">{avgQuizScore.toFixed(0)}%</p>
                  <Progress value={avgQuizScore} className="h-1.5" />
                </Card>
              </motion.div>

              <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.3 }}>
                <Card className="p-4 space-y-2">
                  <div className="flex items-center gap-2 text-purple-500">
                    <MessageSquare className="h-4 w-4" />
                    <span className="text-xs font-medium">Chat Messages</span>
                  </div>
                  <p className="text-lg font-semibold">{progress.total_chat_messages}</p>
                </Card>
              </motion.div>
            </div>

            <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.2 }}>
              <Card className="p-6">
                <h3 className="font-semibold mb-4 flex items-center gap-2">
                  <TrendingUp className="h-4 w-4 text-primary" />
                  Completed Modules
                </h3>
                {progress.completed_modules.length === 0 ? (
                  <p className="text-sm text-muted-foreground">No modules completed yet.</p>
                ) : (
                  <div className="grid gap-2 sm:grid-cols-2">
                    {progress.completed_modules.map((module) => (
                      <div key={module} className="flex items-center gap-2 rounded-lg bg-muted/50 px-3 py-2 text-sm">
                        <Star className="h-3 w-3 text-emerald-500" />
                        {module}
                      </div>
                    ))}
                  </div>
                )}
              </Card>
            </motion.div>

            <div className="grid gap-4 sm:grid-cols-2">
              <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.3 }}>
                <Card className="p-6">
                  <h3 className="font-semibold mb-4 flex items-center gap-2">
                    <Brain className="h-4 w-4 text-amber-500" />
                    Quiz Scores
                  </h3>
                  {Object.keys(progress.quiz_scores).length === 0 ? (
                    <p className="text-sm text-muted-foreground">No quizzes taken yet.</p>
                  ) : (
                    <div className="space-y-3">
                      {Object.entries(progress.quiz_scores).map(([topic, score]) => (
                        <div key={topic}>
                          <div className="flex items-center justify-between text-sm mb-1">
                            <span className="font-medium">{topic}</span>
                            <Badge variant={score >= 80 ? "success" : score >= 60 ? "warning" : "destructive"}>
                              {score}%
                            </Badge>
                          </div>
                          <Progress value={score} className="h-1.5" />
                        </div>
                      ))}
                    </div>
                  )}
                </Card>
              </motion.div>

              <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.4 }}>
                <Card className="p-6">
                  <h3 className="font-semibold mb-4 flex items-center gap-2">
                    <MessageSquare className="h-4 w-4 text-purple-500" />
                    Interview Scores
                  </h3>
                  {Object.keys(progress.interview_scores).length === 0 ? (
                    <p className="text-sm text-muted-foreground">No interviews completed yet.</p>
                  ) : (
                    <div className="space-y-3">
                      {Object.entries(progress.interview_scores).map(([name, score]) => (
                        <div key={name}>
                          <div className="flex items-center justify-between text-sm mb-1">
                            <span className="font-medium">{name}</span>
                            <Badge variant={score >= 80 ? "success" : score >= 60 ? "warning" : "destructive"}>
                              {score}%
                            </Badge>
                          </div>
                          <Progress value={score} className="h-1.5" />
                        </div>
                      ))}
                    </div>
                  )}
                </Card>
              </motion.div>
            </div>

            <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.5 }}>
              <Card className="p-6">
                <h3 className="font-semibold mb-4 flex items-center gap-2">
                  <FileText className="h-4 w-4 text-blue-500" />
                  Activity Summary
                </h3>
                <div className="grid grid-cols-2 gap-4 text-sm">
                  <div className="rounded-lg bg-muted/50 p-3">
                    <p className="text-muted-foreground">Documents Uploaded</p>
                    <p className="text-2xl font-bold">{progress.documents_uploaded}</p>
                  </div>
                  <div className="rounded-lg bg-muted/50 p-3">
                    <p className="text-muted-foreground">Total Chat Messages</p>
                    <p className="text-2xl font-bold">{progress.total_chat_messages}</p>
                  </div>
                </div>
              </Card>
            </motion.div>
          </div>
        </ScrollArea>
      </div>
    </AiErrorBoundary>
  );
}