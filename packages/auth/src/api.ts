import type {
  ChangePasswordRequest,
  ForgotPasswordRequest,
  LoginRequest,
  LoginResponse,
  LogoutRequest,
  RefreshRequest,
  RefreshResponse,
  RegisterRequest,
  RegisterResponse,
  ResetPasswordRequest,
  SessionListResponse,
  SessionResponse,
  UpdateProfileRequest,
  UserProfile,
  VerifyEmailRequest,
} from "./types";

export class AuthApiError extends Error {
  constructor(
    message: string,
    public status: number,
    public error_code: string,
    public details?: Record<string, unknown>,
  ) {
    super(message);
    this.name = "AuthApiError";
  }
}

function getBaseUrl(): string {
  return process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
}

async function request<T>(
  path: string,
  options: RequestInit = {},
  token?: string,
): Promise<T> {
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(options.headers as Record<string, string>),
  };

  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }

  const response = await fetch(`${getBaseUrl()}${path}`, {
    ...options,
    headers,
  });

  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    throw new AuthApiError(
      body.error || "Request failed",
      response.status,
      body.error_code || "UNKNOWN_ERROR",
      body.details,
    );
  }

  if (response.status === 204) {
    return undefined as T;
  }

  return response.json();
}

export function getAccessToken(): string | null {
  if (typeof window === "undefined") return null;
  try {
    const stored = sessionStorage.getItem("access_token");
    return stored;
  } catch {
    return null;
  }
}

export function setAccessToken(token: string): void {
  if (typeof window === "undefined") return;
  try {
    sessionStorage.setItem("access_token", token);
  } catch {
    /* noop */
  }
}

export function clearAccessToken(): void {
  if (typeof window === "undefined") return;
  try {
    sessionStorage.removeItem("access_token");
  } catch {
    /* noop */
  }
}

export async function login(data: LoginRequest): Promise<LoginResponse> {
  const result = await request<LoginResponse>("/api/v1/auth/login", {
    method: "POST",
    body: JSON.stringify(data),
  });
  setAccessToken(result.access_token);
  return result;
}

export async function register(data: RegisterRequest): Promise<RegisterResponse> {
  const result = await request<RegisterResponse>("/api/v1/auth/register", {
    method: "POST",
    body: JSON.stringify(data),
  });
  return result;
}

export async function refresh(data: RefreshRequest): Promise<RefreshResponse> {
  const result = await request<RefreshResponse>("/api/v1/auth/refresh", {
    method: "POST",
    body: JSON.stringify(data),
  });
  setAccessToken(result.access_token);
  return result;
}

export async function logout(data: LogoutRequest = {}): Promise<void> {
  const token = getAccessToken();
  try {
    await request<void>(
      "/api/v1/auth/logout",
      {
        method: "POST",
        body: JSON.stringify(data),
      },
      token || undefined,
    );
  } finally {
    clearAccessToken();
  }
}

export async function getMe(): Promise<UserProfile> {
  const token = getAccessToken();
  if (!token) throw new AuthApiError("Not authenticated", 401, "NOT_AUTHENTICATED");
  return request<UserProfile>("/api/v1/auth/me", {}, token);
}

export async function updateProfile(data: UpdateProfileRequest): Promise<UserProfile> {
  const token = getAccessToken();
  if (!token) throw new AuthApiError("Not authenticated", 401, "NOT_AUTHENTICATED");
  return request<UserProfile>(
    "/api/v1/auth/me",
    { method: "PATCH", body: JSON.stringify(data) },
    token,
  );
}

export async function getSessions(): Promise<SessionListResponse> {
  const token = getAccessToken();
  if (!token) throw new AuthApiError("Not authenticated", 401, "NOT_AUTHENTICATED");
  return request<SessionListResponse>("/api/v1/auth/sessions", {}, token);
}

export async function deleteSession(sessionId: string): Promise<void> {
  const token = getAccessToken();
  if (!token) throw new AuthApiError("Not authenticated", 401, "NOT_AUTHENTICATED");
  return request<void>(
    `/api/v1/auth/sessions/${sessionId}`,
    { method: "DELETE" },
    token,
  );
}

export async function deleteOtherSessions(): Promise<{ revoked_count: number }> {
  const token = getAccessToken();
  if (!token) throw new AuthApiError("Not authenticated", 401, "NOT_AUTHENTICATED");
  return request<{ revoked_count: number }>(
    "/api/v1/auth/sessions",
    { method: "DELETE" },
    token,
  );
}

export async function changePassword(data: ChangePasswordRequest): Promise<{ message: string }> {
  const token = getAccessToken();
  if (!token) throw new AuthApiError("Not authenticated", 401, "NOT_AUTHENTICATED");
  return request<{ message: string }>(
    "/api/v1/auth/change-password",
    { method: "POST", body: JSON.stringify(data) },
    token,
  );
}

export async function forgotPassword(data: ForgotPasswordRequest): Promise<{ message: string }> {
  return request<{ message: string }>("/api/v1/auth/forgot-password", {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export async function resetPassword(data: ResetPasswordRequest): Promise<{ message: string }> {
  return request<{ message: string }>("/api/v1/auth/reset-password", {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export async function verifyEmail(data: VerifyEmailRequest): Promise<{ message: string }> {
  return request<{ message: string }>("/api/v1/auth/verify-email", {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export async function resendVerification(email: string): Promise<{ message: string }> {
  return request<{ message: string }>("/api/v1/auth/resend-verification", {
    method: "POST",
    body: JSON.stringify({ email }),
  });
}

export async function fetchWithAuth(path: string, options: RequestInit = {}): Promise<Response> {
  const token = getAccessToken();
  const headers: Record<string, string> = {
    ...(options.headers as Record<string, string>),
  };

  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }

  if (!(options.body instanceof FormData)) {
    headers["Content-Type"] = headers["Content-Type"] || "application/json";
  }

  const response = await fetch(`${getBaseUrl()}${path}`, {
    ...options,
    headers,
  });

  if (response.status === 401 && token) {
    try {
      const refreshResp = await fetch(`${getBaseUrl()}/api/v1/auth/refresh`, {
        method: "POST",
        credentials: "include",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ refresh_token: "" }),
      });

      if (refreshResp.ok) {
        const data = await refreshResp.json();
        setAccessToken(data.access_token);
        headers["Authorization"] = `Bearer ${data.access_token}`;
        return fetch(`${getBaseUrl()}${path}`, { ...options, headers });
      }
    } catch {
      clearAccessToken();
    }
  }

  return response;
}