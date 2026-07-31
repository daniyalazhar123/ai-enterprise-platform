import { fetchWithAuth } from "@ai-enterprises/auth";
import type {
  ChatRequest,
  ChatResponse,
  Conversation,
  DocumentInfo,
  DocumentUploadResponse,
  InterviewEvaluateRequest,
  InterviewEvaluateResponse,
  InterviewStartResponse,
  QuizGenerateRequest,
  QuizGenerateResponse,
  QuizSubmitRequest,
  QuizSubmitResponse,
  SearchResult,
  TutorRequest,
  TutorResponse,
} from "./ai-types";

const API_BASE = "/api/v1";

export class AiApiError extends Error {
  constructor(
    message: string,
    public status: number,
    public type: string,
  ) {
    super(message);
    this.name = "AiApiError";
  }
}

async function handleResponse<T>(response: Response): Promise<T> {
  if (!response.ok) {
    let body: Record<string, unknown> = {};
    try {
      body = await response.json();
    } catch {
      /* ignore */
    }
    const errorData = body?.error as Record<string, unknown> | undefined;
    throw new AiApiError(
      (errorData?.message as string) || `Request failed with status ${response.status}`,
      response.status,
      (errorData?.type as string) || "UNKNOWN",
    );
  }
  if (response.status === 204) return undefined as T;
  return response.json();
}

export async function chatSend(data: ChatRequest): Promise<ChatResponse> {
  const response = await fetchWithAuth(`${API_BASE}/ai/chat`, {
    method: "POST",
    body: JSON.stringify(data),
  });
  return handleResponse<ChatResponse>(response);
}

export function chatStream(data: ChatRequest): EventSource {
  const token = typeof window !== "undefined" ? sessionStorage.getItem("access_token") : null;
  const url = new URL(`${API_BASE}/ai/chat/stream`, window.location.origin);
  const body = JSON.stringify(data);
  return new EventSource(url.toString());
}

export async function tutorSend(data: TutorRequest): Promise<TutorResponse> {
  const response = await fetchWithAuth(`${API_BASE}/ai/tutor`, {
    method: "POST",
    body: JSON.stringify(data),
  });
  return handleResponse<TutorResponse>(response);
}

export async function quizGenerate(data: QuizGenerateRequest): Promise<QuizGenerateResponse> {
  const response = await fetchWithAuth(`${API_BASE}/ai/quiz/generate`, {
    method: "POST",
    body: JSON.stringify(data),
  });
  return handleResponse<QuizGenerateResponse>(response);
}

export async function quizSubmit(data: QuizSubmitRequest): Promise<QuizSubmitResponse> {
  const response = await fetchWithAuth(`${API_BASE}/ai/quiz/submit`, {
    method: "POST",
    body: JSON.stringify(data),
  });
  return handleResponse<QuizSubmitResponse>(response);
}

export async function interviewStart(): Promise<InterviewStartResponse> {
  const response = await fetchWithAuth(`${API_BASE}/ai/interview/start`, {
    method: "POST",
  });
  return handleResponse<InterviewStartResponse>(response);
}

export async function interviewEvaluate(data: InterviewEvaluateRequest): Promise<InterviewEvaluateResponse> {
  const response = await fetchWithAuth(`${API_BASE}/ai/interview/evaluate`, {
    method: "POST",
    body: JSON.stringify(data),
  });
  return handleResponse<InterviewEvaluateResponse>(response);
}

export async function listConversations(limit = 50, offset = 0): Promise<Conversation[]> {
  const response = await fetchWithAuth(`${API_BASE}/ai/conversations?limit=${limit}&offset=${offset}`);
  return handleResponse<Conversation[]>(response);
}

export async function getConversationMessages(conversationId: string): Promise<ChatResponse["message"][]> {
  const response = await fetchWithAuth(`${API_BASE}/ai/conversations/${conversationId}/messages`);
  return handleResponse(response);
}

export async function deleteConversation(conversationId: string): Promise<void> {
  const response = await fetchWithAuth(`${API_BASE}/ai/conversations/${conversationId}`, {
    method: "DELETE",
  });
  return handleResponse<void>(response);
}

export async function updateConversationTitle(conversationId: string, title: string): Promise<void> {
  const formData = new FormData();
  formData.append("title", title);
  const response = await fetchWithAuth(`${API_BASE}/ai/conversations/${conversationId}`, {
    method: "PATCH",
    body: formData,
  });
  return handleResponse<void>(response);
}

export async function uploadDocument(file: File, chapterId?: string, section?: string): Promise<DocumentUploadResponse> {
  const formData = new FormData();
  formData.append("file", file);
  if (chapterId) formData.append("chapter_id", chapterId);
  if (section) formData.append("section", section);
  const response = await fetchWithAuth(`${API_BASE}/ai/documents/upload`, {
    method: "POST",
    body: formData,
  });
  return handleResponse<DocumentUploadResponse>(response);
}

export async function listDocuments(limit = 50, offset = 0): Promise<DocumentInfo[]> {
  const response = await fetchWithAuth(`${API_BASE}/ai/documents?limit=${limit}&offset=${offset}`);
  return handleResponse<DocumentInfo[]>(response);
}

export async function deleteDocument(docId: string): Promise<void> {
  const response = await fetchWithAuth(`${API_BASE}/ai/documents/${docId}`, {
    method: "DELETE",
  });
  return handleResponse<void>(response);
}

export async function searchDocuments(query: string, topK = 5): Promise<SearchResult[]> {
  const formData = new FormData();
  formData.append("query", query);
  formData.append("top_k", String(topK));
  const response = await fetchWithAuth(`${API_BASE}/ai/search`, {
    method: "POST",
    body: formData,
  });
  return handleResponse<SearchResult[]>(response);
}

export async function startTutorStream(data: TutorRequest, onChunk: (text: string) => void): Promise<string> {
  const response = await fetchWithAuth(`${API_BASE}/ai/tutor/stream`, {
    method: "POST",
    body: JSON.stringify(data),
  });

  if (!response.ok) throw new AiApiError("Stream failed", response.status, "STREAM_ERROR");
  return response.text();
}