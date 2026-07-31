"use client";

import { Mic, MicOff, Play, Square, Volume2 } from "lucide-react";
import { useCallback, useState } from "react";
import { Button } from "@/components/ui/button";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Slider } from "@/components/ui/slider";
import { Switch } from "@/components/ui/switch";
import { cn } from "@/lib/utils";
import { useVoice } from "@/hooks/use-ai-voice";

export function VoiceRecorder({ onTranscript }: { onTranscript?: (text: string) => void }) {
  const { state, recordingDuration, isSupported, startRecording, stopRecording } = useVoice({ onTranscript });

  if (!isSupported) return null;

  return (
    <Button
      variant="outline"
      size="icon"
      className={cn(
        "rounded-full transition-all",
        state === "recording" && "bg-destructive text-destructive-foreground hover:bg-destructive/90 animate-pulse",
        state === "processing" && "bg-amber-500/10 text-amber-500",
      )}
      onClick={state === "recording" ? stopRecording : startRecording}
      aria-label={state === "recording" ? "Stop recording" : "Start recording"}
    >
      {state === "recording" ? (
        <Square className="h-4 w-4" />
      ) : state === "processing" ? (
        <div className="h-4 w-4 animate-spin rounded-full border-2 border-amber-500 border-t-transparent" />
      ) : (
        <Mic className="h-4 w-4" />
      )}
    </Button>
  );
}

interface VoicePlaybackProps {
  text: string;
  gender?: "male" | "female";
  speed?: number;
}

export function VoicePlayback({ text, gender = "female", speed = 1 }: VoicePlaybackProps) {
  const { state, speak, stopSpeaking } = useVoice();

  const handleToggle = useCallback(() => {
    if (state === "playing") {
      stopSpeaking();
    } else {
      speak(text, gender, speed);
    }
  }, [state, text, gender, speed, speak, stopSpeaking]);

  return (
    <Button
      variant="ghost"
      size="icon"
      className={cn("h-8 w-8", state === "playing" && "text-primary")}
      onClick={handleToggle}
      aria-label={state === "playing" ? "Stop playback" : "Read aloud"}
    >
      {state === "playing" ? <Square className="h-4 w-4" /> : <Volume2 className="h-4 w-4" />}
    </Button>
  );
}

export function VoiceSettings() {
  const [gender, setGender] = useState<"male" | "female">("female");
  const [speed, setSpeed] = useState(1);
  const [enabled, setEnabled] = useState(true);

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <p className="text-sm font-medium">Voice Readback</p>
          <p className="text-xs text-muted-foreground">Enable text-to-speech for AI responses</p>
        </div>
        <Switch checked={enabled} onCheckedChange={setEnabled} />
      </div>

      {enabled && (
        <>
          <div className="space-y-2">
            <label className="text-sm font-medium">Voice Gender</label>
            <Select value={gender} onValueChange={(v) => setGender(v as "male" | "female")}>
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="female">Female</SelectItem>
                <SelectItem value="male">Male</SelectItem>
              </SelectContent>
            </Select>
          </div>

          <div className="space-y-2">
            <label className="text-sm font-medium">Speech Speed: {speed}x</label>
            <Slider value={[speed]} onValueChange={([v]) => setSpeed(v)} min={0.5} max={2} step={0.25} />
          </div>

          <div className="flex items-center gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={() => speak("Hello, this is a preview of the voice settings.", gender, speed)}
              className="gap-2"
            >
              <Play className="h-4 w-4" />
              Preview
            </Button>
          </div>
        </>
      )}
    </div>
  );
}

function speak(text: string, gender: string, rate: number) {
  if (typeof window === "undefined") return;
  window.speechSynthesis.cancel();
  const utterance = new SpeechSynthesisUtterance(text);
  utterance.rate = rate;
  utterance.lang = "en";
  window.speechSynthesis.speak(utterance);
}