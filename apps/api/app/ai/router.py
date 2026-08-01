from __future__ import annotations

from typing import Any

from fastapi import APIRouter, File, Form, UploadFile, status
from fastapi.responses import JSONResponse

from apps.api.app.ai.endpoints import (
    chat_stream,
    quiz_generate_stream,
    tutor_stream,
)
from apps.api.app.ai.schemas.models import (
    ChatRequest,
    ChatResponse,
    DocumentUploadResponse,
    InterviewEvaluateRequest,
    InterviewEvaluateResponse,
    InterviewStartResponse,
    QuizGenerateRequest,
    QuizGenerateResponse,
    QuizSubmitRequest,
    QuizSubmitResponse,
    TutorRequest,
    TutorResponse,
)

from apps.api.app.ai.agents.chat_agent import ChatAgent
from apps.api.app.ai.agents.interview_agent import InterviewAgent
from apps.api.app.ai.agents.quiz_agent import QuizAgent
from apps.api.app.ai.agents.tutor_agent import TutorAgent
from apps.api.app.ai.documents.upload import document_service
from apps.api.app.ai.memory.conversation_memory import conversation_memory
from apps.api.app.core.deps import CurrentUser
from apps.api.app.core.exceptions import NotFoundError, ValidationError

ai_router = APIRouter(prefix="/api/v1", tags=["AI"])


@ai_router.post("/ai/chat", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    user: CurrentUser,
) -> ChatResponse:
    agent = ChatAgent(user_id=user.id)
    return await agent.run(
        message=request.message,
        conversation_id=request.conversation_id,
        use_rag=request.use_rag,
    )


@ai_router.post("/ai/chat/stream")
async def chat_stream_endpoint(
    request: ChatRequest,
    _user: CurrentUser,
) -> Any:
    return await chat_stream(request=request, body=request)


@ai_router.post("/ai/tutor", response_model=TutorResponse)
async def tutor(
    request: TutorRequest,
    user: CurrentUser,
) -> TutorResponse:
    agent = TutorAgent(user_id=user.id)
    return await agent.tutor(
        topic=request.topic,
        question=request.question,
        conversation_id=request.conversation_id,
    )


@ai_router.post("/ai/tutor/stream")
async def tutor_stream_endpoint(
    request: TutorRequest,
    _user: CurrentUser,
) -> Any:
    return await tutor_stream(request=request, body=request)


@ai_router.post("/ai/quiz/generate", response_model=QuizGenerateResponse)
async def generate_quiz(
    request: QuizGenerateRequest,
    user: CurrentUser,
) -> QuizGenerateResponse:
    agent = QuizAgent(user_id=user.id)
    return await agent.generate(
        topic=request.topic,
        num_questions=request.num_questions,
        difficulty=request.difficulty,
        conversation_id=request.conversation_id,
    )


@ai_router.post("/ai/quiz/generate/stream")
async def generate_quiz_stream_endpoint(
    request: QuizGenerateRequest,
    _user: CurrentUser,
) -> Any:
    return await quiz_generate_stream(
        request=request,
        body=request.model_dump(),
    )


@ai_router.post("/ai/quiz/submit", response_model=QuizSubmitResponse)
async def submit_quiz(
    request: QuizSubmitRequest,
    user: CurrentUser,
) -> QuizSubmitResponse:
    agent = QuizAgent(user_id=user.id)
    return await agent.evaluate(
        quiz_data=request.quiz_data,
        answers=request.answers,
    )


@ai_router.post("/ai/interview/start", response_model=InterviewStartResponse)
async def start_interview(
    user: CurrentUser,
) -> InterviewStartResponse:
    agent = InterviewAgent(user_id=user.id)
    return await agent.start(conversation_id=None)


@ai_router.post("/ai/interview/evaluate", response_model=InterviewEvaluateResponse)
async def evaluate_interview(
    request: InterviewEvaluateRequest,
    user: CurrentUser,
) -> InterviewEvaluateResponse:
    agent = InterviewAgent(user_id=user.id)
    return await agent.evaluate(
        conversation_id=request.conversation_id,
        question_index=request.question_index,
        answer=request.answer,
    )


@ai_router.get("/ai/conversations")
async def list_conversations(
    user: CurrentUser,
    limit: int = 50,
    offset: int = 0,
) -> list[dict[str, Any]]:
    return await conversation_memory.list_conversations(
        user_id=user.id,
        limit=limit,
        offset=offset,
    )


@ai_router.get("/ai/conversations/{conversation_id}")
async def get_conversation_messages(
    conversation_id: str,
    user: CurrentUser,
) -> list[dict[str, Any]]:
    return await conversation_memory.get_messages(
        conversation_id=conversation_id,
        user_id=user.id,
    )


@ai_router.delete("/ai/conversations/{conversation_id}")
async def delete_conversation(
    conversation_id: str,
    user: CurrentUser,
) -> dict[str, str]:
    success = await conversation_memory.delete_conversation(
        conversation_id=conversation_id,
        user_id=user.id,
    )
    if not success:
        raise NotFoundError("Conversation not found")
    return {"status": "deleted"}


@ai_router.patch("/ai/conversations/{conversation_id}")
async def update_conversation(
    conversation_id: str,
    user: CurrentUser,
    title: str = Form(...),
) -> dict[str, str]:
    success = await conversation_memory.update_title(
        conversation_id=conversation_id,
        user_id=user.id,
        title=title,
    )
    if not success:
        raise NotFoundError("Conversation not found")
    return {"status": "updated"}


@ai_router.post("/ai/documents/upload", response_model=DocumentUploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_document(
    user: CurrentUser,
    file: UploadFile = File(...),
    chapter_id: str = Form(default=""),
    section: str = Form(default=""),
) -> DocumentUploadResponse:
    content = await file.read()
    temp_path = f"/tmp/{file.filename}"
    with open(temp_path, "wb") as f:
        f.write(content)

    try:
        result = await document_service.process_and_store(
            file_path=temp_path,
            filename=file.filename or "unknown",
            content_type=file.content_type or "application/octet-stream",
            user_id=user.id,
            metadata={
                "chapter_id": chapter_id,
                "section": section,
                "created_at": None,
            },
        )
    finally:
        import os
        os.remove(temp_path)

    return DocumentUploadResponse(
        id=result["id"],
        filename=result["filename"],
        content_type=result["content_type"],
        chunks=result["chunks"],
    )


@ai_router.get("/ai/documents")
async def list_documents(
    user: CurrentUser,
    limit: int = 50,
    offset: int = 0,
) -> list[dict[str, Any]]:
    return await document_service.list_documents(
        user_id=user.id,
        limit=limit,
        offset=offset,
    )


@ai_router.delete("/ai/documents/{doc_id}")
async def delete_document(
    doc_id: str,
    user: CurrentUser,
) -> dict[str, str]:
    success = await document_service.delete_document(
        doc_id=doc_id,
        user_id=user.id,
    )
    if not success:
        raise NotFoundError("Document not found")
    return {"status": "deleted"}


@ai_router.post("/ai/search")
async def search_documents(
    user: CurrentUser,
    query: str = Form(...),
    top_k: int = Form(default=5),
) -> list[dict[str, Any]]:
    from apps.api.app.ai.rag.hybrid_search import hybrid_search
    results = await hybrid_search.search(
        query=query,
        top_k=top_k,
        filters={"user_id": user.id},
    )
    return results