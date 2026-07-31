"use client";

import { useCallback, useEffect, useState } from "react";

interface UserPreferences {
  locale: string;
  theme: "light" | "dark" | "system";
  voice_enabled: boolean;
  voice_speed: number;
  voice_gender: "male" | "female";
}

const DEFAULT_PREFERENCES: UserPreferences = {
  locale: "en",
  theme: "system",
  voice_enabled: true,
  voice_speed: 1,
  voice_gender: "female",
};

export function usePreferences() {
  const [preferences, setPreferences] = useState<UserPreferences>(() => {
    if (typeof window === "undefined") return DEFAULT_PREFERENCES;
    try {
      const stored = localStorage.getItem("ai-preferences");
      return stored ? { ...DEFAULT_PREFERENCES, ...JSON.parse(stored) } : DEFAULT_PREFERENCES;
    } catch {
      return DEFAULT_PREFERENCES;
    }
  });

  useEffect(() => {
    localStorage.setItem("ai-preferences", JSON.stringify(preferences));
  }, [preferences]);

  const updatePreferences = useCallback((updates: Partial<UserPreferences>) => {
    setPreferences((prev) => ({ ...prev, ...updates }));
  }, []);

  const setLocale = useCallback((locale: string) => updatePreferences({ locale }), [updatePreferences]);
  const setTheme = useCallback((theme: "light" | "dark" | "system") => updatePreferences({ theme }), [updatePreferences]);
  const setVoiceEnabled = useCallback((enabled: boolean) => updatePreferences({ voice_enabled: enabled }), [updatePreferences]);
  const setVoiceSpeed = useCallback((speed: number) => updatePreferences({ voice_speed: speed }), [updatePreferences]);
  const setVoiceGender = useCallback((gender: "male" | "female") => updatePreferences({ voice_gender: gender }), [updatePreferences]);

  return {
    preferences,
    updatePreferences,
    setLocale,
    setTheme,
    setVoiceEnabled,
    setVoiceSpeed,
    setVoiceGender,
  };
}