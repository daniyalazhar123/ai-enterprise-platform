"use client";

import { useCallback, useContext, useEffect, useRef, useState } from "react";
import {
  clearAccessToken,
  getAccessToken,
  getMe,
  login as apiLogin,
  logout as apiLogout,
  register as apiRegister,
  setAccessToken,
} from "./api";
import { AuthContext } from "./components/AuthProvider";
import type {
  AuthState,
  LoginRequest,
  LoginResponse,
  RegisterRequest,
  RegisterResponse,
  UserProfile,
} from "./types";

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
}

export function useUser(): UserProfile | null {
  const { user } = useAuth();
  return user;
}

export function useAuthState(): AuthState {
  const { state } = useAuth();
  return state;
}

export function useIsAuthenticated(): boolean {
  const { state } = useAuth();
  return state === "authenticated";
}

export function useLogin() {
  const { setUser, setState } = useContext(AuthContext);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const login = useCallback(
    async (data: LoginRequest): Promise<LoginResponse> => {
      setLoading(true);
      setError(null);
      try {
        const result = await apiLogin(data);
        setUser(result.user);
        setState("authenticated");
        return result;
      } catch (err: unknown) {
        const message =
          err instanceof Error ? err.message : "Login failed";
        setError(message);
        throw err;
      } finally {
        setLoading(false);
      }
    },
    [setUser, setState],
  );

  return { login, loading, error };
}

export function useRegister() {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const register = useCallback(
    async (data: RegisterRequest): Promise<RegisterResponse> => {
      setLoading(true);
      setError(null);
      try {
        const result = await apiRegister(data);
        return result;
      } catch (err: unknown) {
        const message =
          err instanceof Error ? err.message : "Registration failed";
        setError(message);
        throw err;
      } finally {
        setLoading(false);
      }
    },
    [],
  );

  return { register, loading, error };
}

export function useLogout() {
  const { setUser, setState } = useContext(AuthContext);
  const [loading, setLoading] = useState(false);

  const logout = useCallback(
    async (allSessions = false) => {
      setLoading(true);
      try {
        await apiLogout({ all_sessions: allSessions });
      } finally {
        clearAccessToken();
        setUser(null);
        setState("unauthenticated");
        setLoading(false);
      }
    },
    [setUser, setState],
  );

  return { logout, loading };
}

export function useProfile() {
  const { setUser } = useContext(AuthContext);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const profile = await getMe();
      setUser(profile);
      return profile;
    } catch (err: unknown) {
      const message =
        err instanceof Error ? err.message : "Failed to load profile";
      setError(message);
      return null;
    } finally {
      setLoading(false);
    }
  }, [setUser]);

  return { refresh, loading, error };
}

export function useRefreshToken() {
  const [loading, setLoading] = useState(false);

  const attemptRefresh = useCallback(async (): Promise<boolean> => {
    setLoading(true);
    try {
      const response = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}/api/v1/auth/refresh`,
        {
          method: "POST",
          credentials: "include",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ refresh_token: "" }),
        },
      );

      if (response.ok) {
        const data = await response.json();
        setAccessToken(data.access_token);
        return true;
      }
      return false;
    } catch {
      return false;
    } finally {
      setLoading(false);
    }
  }, []);

  return { attemptRefresh, loading };
}