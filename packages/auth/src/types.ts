export interface User {
  id: string;
  email: string;
  display_name: string;
  avatar_url: string | null;
  is_verified: boolean;
  is_active: boolean;
  locale: string;
  roles: string[];
  permissions: string[];
  created_at: string;
}

export interface UserProfile {
  id: string;
  email: string;
  display_name: string;
  avatar_url: string | null;
  is_verified: boolean;
  locale: string;
  roles: string[];
  created_at: string;
}

export interface LoginRequest {
  email: string;
  password: string;
  device_info?: Record<string, unknown>;
}

export interface LoginResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
  session_id: string;
  user: User;
}

export interface RegisterRequest {
  email: string;
  password: string;
  display_name: string;
}

export interface RegisterResponse {
  id: string;
  email: string;
  display_name: string;
  is_verified: boolean;
  created_at: string;
  message: string;
}

export interface RefreshRequest {
  refresh_token: string;
}

export interface RefreshResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
}

export interface LogoutRequest {
  refresh_token?: string;
  all_sessions?: boolean;
}

export interface ForgotPasswordRequest {
  email: string;
}

export interface ResetPasswordRequest {
  token: string;
  new_password: string;
}

export interface ChangePasswordRequest {
  current_password: string;
  new_password: string;
}

export interface VerifyEmailRequest {
  token: string;
}

export interface SessionResponse {
  id: string;
  ip_address: string;
  user_agent: string;
  device_info: Record<string, unknown>;
  is_active: boolean;
  created_at: string;
  last_used_at: string;
  expires_at: string;
  current: boolean;
}

export interface SessionListResponse {
  sessions: SessionResponse[];
  total: number;
  active_count: number;
}

export interface UpdateProfileRequest {
  display_name?: string;
  avatar_url?: string;
  locale?: string;
}

export interface ApiError {
  error: string;
  error_code: string;
  details?: Record<string, unknown>;
  request_id?: string;
}

export type AuthState = "loading" | "authenticated" | "unauthenticated";