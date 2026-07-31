"use client";

import { useCallback, useEffect, useState } from "react";

export type VoiceState = "idle" | "recording" | "processing" | "playing";

interface UseVoiceOptions {
  onTranscript?: (text: string) => void;
  language?: string;
}

export function useVoice({ onTranscript, language = "en" }: UseVoiceOptions = {}) {
  const [state, setState] = useState<VoiceState>("idle");
  const [recordingDuration, setRecordingDuration] = useState(0);
  const [recognition, setRecognition] = useState<SpeechRecognition | null>(null);
  const [synthesis, setSynthesis] = useState<SpeechSynthesis | null>(null);

  useEffect(() => {
    if (typeof window !== "undefined") {
      const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
      if (SpeechRecognition) {
        const recog = new SpeechRecognition();
        recog.continuous = true;
        recog.interimResults = true;
        recog.lang = language;
        setRecognition(recog);
      }
      setSynthesis(window.speechSynthesis);
    }
  }, [language]);

  const startRecording = useCallback(() => {
    if (!recognition) return;
    setState("recording");
    setRecordingDuration(0);

    recognition.onresult = (event: SpeechRecognitionEvent) => {
      const transcript = Array.from(event.results)
        .map((r) => r[0].transcript)
        .join("");
      if (event.results[event.results.length - 1].isFinal) {
        onTranscript?.(transcript);
      }
    };

    recognition.onerror = () => setState("idle");
    recognition.start();

    const interval = setInterval(() => {
      setRecordingDuration((prev) => prev + 1);
    }, 1000);

    const cleanup = () => clearInterval(interval);
    recognition.onend = () => {
      clearInterval(interval);
      setState("idle");
    };

    return cleanup;
  }, [recognition, onTranscript]);

  const stopRecording = useCallback(() => {
    recognition?.stop();
    setState("processing");
    setTimeout(() => setState("idle"), 500);
  }, [recognition]);

  const speak = useCallback(
    (text: string, gender: "male" | "female" = "female", speed = 1) => {
      if (!synthesis) return;
      synthesis.cancel();
      const utterance = new SpeechSynthesisUtterance(text);
      utterance.rate = speed;
      utterance.lang = language;

      const voices = synthesis.getVoices();
      const voice = voices.find(
        (v) =>
          v.lang.startsWith(language.split("-")[0]) &&
          (gender === "female" ? v.name.includes("Female") || v.name.includes("Samantha") : v.name.includes("Male") || v.name.includes("Google US English")),
      );
      if (voice) utterance.voice = voice;

      setState("playing");
      utterance.onend = () => setState("idle");
      utterance.onerror = () => setState("idle");
      synthesis.speak(utterance);
    },
    [synthesis, language],
  );

  const stopSpeaking = useCallback(() => {
    synthesis?.cancel();
    setState("idle");
  }, [synthesis]);

  const isSupported = !!recognition;

  return {
    state,
    recordingDuration,
    isSupported,
    startRecording,
    stopRecording,
    speak,
    stopSpeaking,
  };
}