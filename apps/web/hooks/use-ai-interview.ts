"use client";

import { useCallback, useState } from "react";
import { interviewEvaluate, interviewStart } from "@/lib/ai-api";
import type { InterviewFeedback, InterviewQuestion } from "@/lib/ai-types";

export function useInterview() {
  const [questions, setQuestions] = useState<InterviewQuestion[]>([]);
  const [currentIndex, setCurrentIndex] = useState(0);
  const [answers, setAnswers] = useState<string[]>([]);
  const [feedbacks, setFeedbacks] = useState<InterviewFeedback[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [isComplete, setIsComplete] = useState(false);
  const [conversationId, setConversationId] = useState<string | undefined>();
  const [error, setError] = useState<string | null>(null);
  const [overallScore, setOverallScore] = useState(0);

  const start = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    setIsComplete(false);
    setCurrentIndex(0);
    setAnswers([]);
    setFeedbacks([]);

    try {
      const response = await interviewStart();
      setQuestions(response.questions);
      setConversationId(response.interview_id);
      return response;
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to start interview");
    } finally {
      setIsLoading(false);
    }
  }, []);

  const submitAnswer = useCallback(async (answer: string) => {
    if (!conversationId) return;
    setIsLoading(true);
    setError(null);

    setAnswers((prev) => {
      const next = [...prev];
      next[currentIndex] = answer;
      return next;
    });

    try {
      const response = await interviewEvaluate({
        conversation_id: conversationId,
        question_index: currentIndex,
        answer,
      });

      setFeedbacks((prev) => [...prev, response.feedback]);
      setIsComplete(response.is_complete);

      if (response.is_complete) {
        setOverallScore(response.feedback.overall_score || 0);
      } else if (response.next_question) {
        setQuestions((prev) => {
          const exists = prev.some((q) => q.question === response.next_question!.question);
          if (!exists) return [...prev, response.next_question!];
          return prev;
        });
        setCurrentIndex((prev) => prev + 1);
      } else {
        setCurrentIndex((prev) => prev + 1);
      }

      return response;
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to evaluate answer");
    } finally {
      setIsLoading(false);
    }
  }, [conversationId, currentIndex]);

  const reset = useCallback(() => {
    setQuestions([]);
    setCurrentIndex(0);
    setAnswers([]);
    setFeedbacks([]);
    setIsComplete(false);
    setConversationId(undefined);
    setError(null);
    setOverallScore(0);
  }, []);

  const currentQuestion = questions[currentIndex] || null;

  return {
    questions,
    currentIndex,
    currentQuestion,
    answers,
    feedbacks,
    isLoading,
    isComplete,
    overallScore,
    error,
    start,
    submitAnswer,
    reset,
  };
}