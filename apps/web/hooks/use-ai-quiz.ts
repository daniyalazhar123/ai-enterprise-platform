"use client";

import { useCallback, useState } from "react";
import { quizGenerate, quizSubmit } from "@/lib/ai-api";
import type { QuizQuestion, QuizResult } from "@/lib/ai-types";

export function useQuiz() {
  const [questions, setQuestions] = useState<QuizQuestion[]>([]);
  const [currentIndex, setCurrentIndex] = useState(0);
  const [answers, setAnswers] = useState<Record<string, number>>({});
  const [results, setResults] = useState<QuizResult[] | null>(null);
  const [score, setScore] = useState(0);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [topic, setTopic] = useState("");
  const [difficulty, setDifficulty] = useState<"easy" | "medium" | "hard">("medium");

  const generate = useCallback(async (quizTopic: string, num = 5, diff: "easy" | "medium" | "hard" = "medium") => {
    setIsLoading(true);
    setError(null);
    setResults(null);
    setAnswers({});
    setCurrentIndex(0);
    setTopic(quizTopic);
    setDifficulty(diff);

    try {
      const response = await quizGenerate({
        topic: quizTopic,
        num_questions: num,
        difficulty: diff,
      });
      setQuestions(response.questions);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to generate quiz");
    } finally {
      setIsLoading(false);
    }
  }, []);

  const answer = useCallback((questionId: string, optionIndex: number) => {
    setAnswers((prev) => ({ ...prev, [questionId]: optionIndex }));
  }, []);

  const nextQuestion = useCallback(() => {
    if (currentIndex < questions.length - 1) {
      setCurrentIndex((prev) => prev + 1);
    }
  }, [currentIndex, questions.length]);

  const prevQuestion = useCallback(() => {
    if (currentIndex > 0) {
      setCurrentIndex((prev) => prev - 1);
    }
  }, [currentIndex]);

  const submit = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const response = await quizSubmit({
        quiz_data: questions,
        answers,
      });
      setResults(response.results);
      setScore(response.score);
      return response;
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to submit quiz");
    } finally {
      setIsLoading(false);
    }
  }, [questions, answers]);

  const reset = useCallback(() => {
    setQuestions([]);
    setCurrentIndex(0);
    setAnswers({});
    setResults(null);
    setScore(0);
    setError(null);
  }, []);

  return {
    questions,
    currentIndex,
    answers,
    results,
    score,
    isLoading,
    error,
    topic,
    difficulty,
    generate,
    answer,
    nextQuestion,
    prevQuestion,
    submit,
    reset,
  };
}