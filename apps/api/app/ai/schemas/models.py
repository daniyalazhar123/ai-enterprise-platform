from __future__ import annotations

from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field


class ChatMessage(BaseModel):
    role: Literal["user", "assistant", "system", "tool"]
    content: str
    tool_calls: list[dict[str, Any]] | None = None
    tool_call_id: str | None = None
    name: str | None = None
    timestamp: datetime | None = None


class ConversationCreate(BaseModel):
    title: str | None = None
    metadata: dict[str, Any] = {}


class ConversationResponse(BaseModel):
    id: str
    title: str
    user_id: str
    metadata: dict[str, Any]
    created_at: datetime
    updated_at: datetime
    message_count: int


class ConversationListResponse(BaseModel):
    conversations: list[ConversationResponse]
    total: int


class ChatRequest(BaseModel):
    conversation_id: str | None = None
    message: str
    stream: bool = True
    temperature: float | None = None
    max_tokens: int | None = None
    context: dict[str, Any] = {}


class ChatResponse(BaseModel):
    conversation_id: str
    message: ChatMessage
    sources: list[SourceCitation] = []


class StreamChunk(BaseModel):
    token: str
    index: int = 0
    finish_reason: str | None = None


class SourceCitation(BaseModel):
    id: str
    title: str
    section: str | None = None
    content: str
    relevance: float = 0.0
    url: str | None = None
    page: int | None = None


class TutorRequest(BaseModel):
    conversation_id: str | None = None
    topic: str
    message: str
    stream: bool = True


class QuizGenerateRequest(BaseModel):
    chapter_id: str
    count: int = 10
    difficulty: Literal["beginner", "intermediate", "advanced"] = "intermediate"


class QuizQuestion(BaseModel):
    id: str
    type: Literal["multiple_choice", "true_false", "fill_blank", "multiple_select"]
    question: str
    options: list[str] | None = None
    correct_answer: str | list[str]
    explanation: str
    difficulty: str
    section: str | None = None


class QuizResponse(BaseModel):
    id: str
    chapter_id: str
    title: str
    questions: list[QuizQuestion]
    difficulty: str


class QuizSubmitRequest(BaseModel):
    quiz_id: str
    answers: dict[str, str | list[str]]


class QuizResult(BaseModel):
    quiz_id: str
    score: int
    total: int
    percentage: float
    answers: dict[str, str | list[str]]
    correct_answers: dict[str, str | list[str]]
    feedback: dict[str, str]


class InterviewRequest(BaseModel):
    topic: str
    difficulty: Literal["beginner", "intermediate", "advanced"] = "intermediate"
    session_id: str | None = None


class InterviewResponse(BaseModel):
    session_id: str
    question: str
    question_number: int
    total_questions: int


class InterviewSubmitRequest(BaseModel):
    session_id: str
    answer: str


class InterviewFeedback(BaseModel):
    session_id: str
    strengths: list[str]
    improvements: list[str]
    score: int
    next_question: str | None = None
    is_complete: bool = False


class DocumentUploadResponse(BaseModel):
    id: str
    filename: str
    content_type: str
    size: int
    chunks: int
    status: str


class SearchRequest(BaseModel):
    query: str
    top_k: int = 5
    filters: dict[str, Any] = {}
    hybrid: bool = True


class SearchResult(BaseModel):
    id: str
    content: str
    title: str
    section: str | None = None
    score: float
    source: str
    metadata: dict[str, Any] = {}


class SearchResponse(BaseModel):
    results: list[SearchResult]
    total: int
    query: str


class AiError(BaseModel):
    error: str
    error_code: str
    provider: str | None = None
    details: dict[str, Any] | None = None