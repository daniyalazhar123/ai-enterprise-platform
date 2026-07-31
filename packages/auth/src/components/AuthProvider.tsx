"use client";

import { createContext, useCallback, useEffect, useMemo, useState } from "react";
import { clearAccessToken, getAccessToken, getMe } from "../api";
import type { AuthState, UserProfile } from "../types";

export interface AuthContextValue {
  user: UserProfile | null;
  state: AuthState;
  setUser: (user: UserProfile | null) => void;
  setState: (state: AuthState) => void;
}

export const AuthContext = createContext<AuthContextValue | null>(null);

interface AuthProviderProps {
  children: React.ReactNode;
  initialUser?: UserProfile | null;
}

export function AuthProvider({ children, initialUser = null }: AuthProviderProps) {
  const [user, setUser] = useState<UserProfile | null>(initialUser);
  const [state, setState] = useState<AuthState>(
    initialUser ? "authenticated" : "loading",
  );

  const fetchUser = useCallback(async () => {
    const token = getAccessToken();
    if (!token) {
      setState("unauthenticated");
      setUser(null);
      return;
    }

    try {
      const profile = await getMe();
      setUser(profile);
      setState("authenticated");
    } catch {
      clearAccessToken();
      setUser(null);
      setState("unauthenticated");
    }
  }, []);

  useEffect(() => {
    fetchUser();
  }, [fetchUser]);

  const value = useMemo(
    () => ({ user, state, setUser, setState }),
    [user, state, setUser, setState],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}