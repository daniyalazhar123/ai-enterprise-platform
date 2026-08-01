from __future__ import annotations

import json
from collections.abc import AsyncGenerator
from typing import Any
from uuid import uuid4

from apps.api.app.ai.llm.router import llm_router
from apps.api.app.ai.prompts.manager import prompt_manager
from apps.api.app.ai.rag.pipeline import rag_pipeline
from apps.api.app.ai.schemas.models import (
    QuizGenerateResponse,
    QuizQuestion,
    QuizResponse,
    QuizSubmitResponse,
    StreamChunk,
)
from apps.api.app.core.config import settings


class QuizAgent:
    def __init__(self, user_id: str = "anonymous", conversation_id: str | None = None) -> None:
        self.user_id = user_id
        self.conversation_id = conversation_id

    async def generate_quiz(
        self,
        chapter_id: str,
        count: int = 10,
        difficulty: str = "intermediate",
    ) -> QuizResponse:
        rag_results = await rag_pipeline.search(
            f"Chapter {chapter_id} key concepts",
            top_k=5,
            filters={"chapter_id": chapter_id} if chapter_id else {},
        )

        context = "\n".join(f"[{r['title']}] {r['content'][:1000]}" for r in rag_results)

        prompt = prompt_manager.render("quiz_generation", {
            "chapter_id": chapter_id,
            "count": count,
            "difficulty": difficulty,
            "context": context,
        })

        response = await llm_router.complete(
            messages=[{"role": "system", "content": prompt}],
        )

        try:
            raw = response.content
            if raw.startswith("```json"):
                raw = raw[7:]
            if raw.endswith("```"):
                raw = raw[:-3]
            questions_data = json.loads(raw.strip())
        except (json.JSONDecodeError, ValueError):
            questions_data = {"questions": []}

        questions_list = questions_data if isinstance(questions_data, list) else questions_data.get("questions", [])

        questions = []
        for q in questions_list[:count]:
            questions.append(QuizQuestion(
                id=str(uuid4()),
                type=q.get("type", "multiple_choice"),
                question=q.get("question", ""),
                options=q.get("options"),
                correct_answer=q.get("correct_answer", ""),
                explanation=q.get("explanation", ""),
                difficulty=q.get("difficulty", difficulty),
                section=q.get("section"),
            ))

        return QuizResponse(
            id=str(uuid4()),
            chapter_id=chapter_id,
            title=f"Chapter {chapter_id} Quiz ({difficulty})",
            questions=questions,
            difficulty=difficulty,
        )

    async def generate(
        self,
        topic: str,
        num_questions: int = 10,
        difficulty: str = "medium",
        conversation_id: str | None = None,
    ) -> QuizGenerateResponse:
        if conversation_id:
            self.conversation_id = conversation_id

        chapter_id = topic
        quiz = await self.generate_quiz(
            chapter_id=chapter_id,
            count=num_questions,
            difficulty=difficulty,
        )
        return QuizGenerateResponse(
            id=quiz.id,
            chapter_id=quiz.chapter_id,
            title=quiz.title,
            questions=quiz.questions,
            difficulty=quiz.difficulty,
            status="generated",
        )

    async def generate_stream(
        self,
        topic: str,
        num_questions: int = 10,
        difficulty: str = "medium",
        conversation_id: str | None = None,
    ) -> AsyncGenerator[StreamChunk, None]:
        if conversation_id:
            self.conversation_id = conversation_id

        yield StreamChunk(event_type="token", token="", content="")

        quiz = await self.generate(
            topic=topic,
            num_questions=num_questions,
            difficulty=difficulty,
            conversation_id=conversation_id,
        )

        payload = quiz.model_dump_json()
        yield StreamChunk(
            event_type="done",
            content=payload,
            finish_reason="stop",
        )

    async def evaluate_answers(
        self,
        quiz: QuizResponse,
        answers: dict[str, str | list[str]],
    ) -> dict[str, Any]:
        correct_count = 0
        feedback: dict[str, str] = {}
        correct_answers: dict[str, str | list[str]] = {}

        for question in quiz.questions:
            correct_answers[question.id] = question.correct_answer
            user_answer = answers.get(question.id)

            if isinstance(question.correct_answer, list) and isinstance(user_answer, list):
                is_correct = sorted(question.correct_answer) == sorted(user_answer)
            else:
                is_correct = str(user_answer).lower().strip() == str(question.correct_answer).lower().strip()

            if is_correct:
                correct_count += 1
                feedback[question.id] = "Correct!"
            else:
                feedback[question.id] = question.explanation

        total = len(quiz.questions)
        percentage = (correct_count / total * 100) if total > 0 else 0

        return {
            "score": correct_count,
            "total": total,
            "percentage": round(percentage, 1),
            "answers": answers,
            "correct_answers": correct_answers,
            "feedback": feedback,
        }

    async def evaluate(
        self,
        quiz_data: list[QuizQuestion],
        answers: dict[str, str | list[str]],
        quiz_id: str = "",
    ) -> QuizSubmitResponse:
        quiz = QuizResponse(
            id=quiz_id or str(uuid4()),
            chapter_id="",
            title="",
            questions=quiz_data,
            difficulty="",
        )
        result = await self.evaluate_answers(quiz, answers)
        return QuizSubmitResponse(
            quiz_id=quiz.id,
            score=result["score"],
            total=result["total"],
            percentage=result["percentage"],
            answers=result["answers"],
            correct_answers=result["correct_answers"],
            feedback=result["feedback"],
            status="submitted",
        )


quiz_agent = QuizAgent()
