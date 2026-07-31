from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from apps.api.app.ai.agents.quiz_agent import QuizAgent
from apps.api.app.ai.schemas.models import (
    QuizGenerateResponse,
    QuizQuestion,
    QuizSubmitResponse,
)


@pytest.fixture
def mock_llm_router():
    with patch("apps.api.app.ai.agents.quiz_agent.llm_router") as mock:
        mock.generate = AsyncMock()

        async def fake_generate(*args, **kwargs):
            return MagicMock(
                content='[{"question":"What is Python?","options":["A","B","C","D"],"correct_answer":0,"explanation":"Test"}]',
                model="gpt-4o",
                usage={"prompt_tokens": 30, "completion_tokens": 60},
            )

        mock.generate.side_effect = fake_generate
        yield mock


@pytest.mark.asyncio
async def test_quiz_generate(mock_llm_router):
    agent = QuizAgent(user_id="user-1")
    response = await agent.generate(
        topic="Python basics",
        num_questions=3,
        difficulty="easy",
        conversation_id=None,
    )

    assert isinstance(response, QuizGenerateResponse)
    assert len(response.questions) == 1
    assert response.questions[0].question.startswith("What")


@pytest.mark.asyncio
async def test_quiz_evaluate(mock_llm_router):
    agent = QuizAgent(user_id="user-1")
    questions = [
        QuizQuestion(
            id="q1",
            question="What is Python?",
            options=["A", "B", "C", "D"],
            correct_answer=0,
            explanation="Test",
        )
    ]
    response = await agent.evaluate(
        quiz_data=questions,
        answers={"q1": 0},
    )

    assert isinstance(response, QuizSubmitResponse)


@pytest.mark.asyncio
async def test_quiz_evaluate_with_wrong_answer(mock_llm_router):
    agent = QuizAgent(user_id="user-1")
    questions = [
        QuizQuestion(
            id="q1",
            question="What is Python?",
            options=["A", "B", "C", "D"],
            correct_answer=0,
            explanation="Python is a language",
        )
    ]
    response = await agent.evaluate(
        quiz_data=questions,
        answers={"q1": 1},
    )

    assert isinstance(response, QuizSubmitResponse)
    assert response.score is not None