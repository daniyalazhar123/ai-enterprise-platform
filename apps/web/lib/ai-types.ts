export interface ChatMessage {
  id: string;
  role: "user" | "assistant" | "system";
  content: string;
  created_at: string;
  citations?: SourceCitation[];
  model?: string;
}

export interface SourceCitation {
  id: string;
  title: string;
  content: string;
  score: number;
  source: string;
  section?: string;
  chunk_index: number;
  relevance: "high" | "medium" | "low";
}

export interface StreamChunk {
  content: string;
  event_type: "message" | "citation" | "done" | "error";
  citations?: SourceCitation[];
  error?: string;
}

export interface ChatRequest {
  message: string;
  conversation_id?: string;
  use_rag?: boolean;
}

export interface ChatResponse {
  message: ChatMessage;
  conversation_id: string;
  model: string;
  citations?: SourceCitation[];
}

export interface Conversation {
  id: string;
  title: string;
  created_at: string;
  updated_at: string;
  message_count: number;
  model?: string;
}

export interface TutorRequest {
  topic: string;
  question: string;
  conversation_id?: string;
}

export interface TutorResponse {
  response: string;
  topic: string;
  conversation_id: string;
  guided_questions?: string[];
}

export interface QuizQuestion {
  id: string;
  question: string;
  options: string[];
  correct_answer?: number;
  explanation: string;
}

export interface QuizGenerateRequest {
  topic: string;
  num_questions: number;
  difficulty: "easy" | "medium" | "hard";
  conversation_id?: string;
}

export interface QuizGenerateResponse {
  questions: QuizQuestion[];
  conversation_id: string;
  topic: string;
  difficulty: string;
}

export interface QuizSubmitRequest {
  quiz_data: QuizQuestion[];
  answers: Record<string, number>;
}

export interface QuizResult {
  question_id: string;
  correct: boolean;
  selected: number;
  correct_answer: number;
  explanation: string;
}

export interface QuizSubmitResponse {
  score: number;
  total: number;
  correct_count: number;
  results: QuizResult[];
}

export interface InterviewQuestion {
  question: string;
  category: string;
  difficulty: string;
  hints: string[];
}

export interface InterviewStartResponse {
  interview_id: string;
  questions: InterviewQuestion[];
  total_questions: number;
}

export interface InterviewEvaluateRequest {
  conversation_id: string;
  question_index: number;
  answer: string;
}

export interface InterviewFeedback {
  question_index: number;
  answer: string;
  feedback: string;
  strengths: string[];
  improvements: string[];
  score: number;
  next_question?: InterviewQuestion;
  is_complete?: boolean;
  overall_score?: number;
  summary?: string;
}

export interface InterviewEvaluateResponse {
  feedback: InterviewFeedback;
  is_complete: boolean;
  next_question?: InterviewQuestion;
}

export interface DocumentInfo {
  id: string;
  filename: string;
  content_type: string;
  chunk_count: number;
  file_size: number;
  created_at?: string;
}

export interface DocumentUploadResponse {
  id: string;
  filename: string;
  content_type: string;
  chunks: number;
}

export interface SearchResult {
  id: string;
  content: string;
  title: string;
  section?: string;
  score: number;
  source: string;
  metadata: Record<string, unknown>;
}

export interface SearchRequest {
  query: string;
  top_k?: number;
}

export interface AiError {
  error: {
    type: string;
    message: string;
    status_code: number;
  };
}

export interface ProgressData {
  current_chapter: string | null;
  completed_modules: string[];
  quiz_scores: Record<string, number>;
  interview_scores: Record<string, number>;
  total_chat_messages: number;
  documents_uploaded: number;
}

export interface UserPreferences {
  locale: string;
  theme: "light" | "dark" | "system";
  voice_enabled: boolean;
  voice_speed: number;
  voice_gender: "male" | "female";
}

export type VoiceState = "idle" | "recording" | "processing" | "playing";

export interface Language {
  code: string;
  name: string;
  native_name: string;
}