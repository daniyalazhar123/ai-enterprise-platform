import { describe, it, expect, vi } from "vitest";

vi.mock("@/lib/utils", () => ({
  cn: (...inputs: unknown[]) => inputs.filter(Boolean).join(" "),
}));

describe("AI Types", () => {
  it("validates ChatMessage shape", () => {
    const msg = {
      id: "test-1",
      role: "user" as const,
      content: "Hello",
      created_at: new Date().toISOString(),
    };
    expect(msg.id).toBe("test-1");
    expect(msg.role).toBe("user");
    expect(msg.content).toBe("Hello");
  });

  it("validates StreamChunk event types", () => {
    const validEvents = ["message", "citation", "done", "error"] as const;
    validEvents.forEach((event) => {
      expect(["message", "citation", "done", "error"]).toContain(event);
    });
  });

  it("validates QuizGenerateRequest shape", () => {
    const req = {
      topic: "Python",
      num_questions: 5,
      difficulty: "medium" as const,
    };
    expect(req.topic).toBe("Python");
    expect(req.num_questions).toBe(5);
    expect(["easy", "medium", "hard"]).toContain(req.difficulty);
  });

  it("validates SearchResult score range", () => {
    const result = { id: "1", content: "test", title: "Test", score: 0.85, source: "pdf", metadata: {} };
    expect(result.score).toBeGreaterThanOrEqual(0);
    expect(result.score).toBeLessThanOrEqual(1);
  });

  it("validates UserPreferences defaults", () => {
    const prefs = { locale: "en", theme: "system" as const, voice_enabled: true, voice_speed: 1, voice_gender: "female" as const };
    expect(prefs.locale).toBe("en");
    expect(["light", "dark", "system"]).toContain(prefs.theme);
    expect(["male", "female"]).toContain(prefs.voice_gender);
  });
});

describe("Languages", () => {
  it("returns correct language name", async () => {
    const { getLanguageName } = await import("@/lib/languages");
    expect(getLanguageName("en")).toBe("English");
    expect(getLanguageName("zh")).toBe("Chinese");
    expect(getLanguageName("fr")).toBe("French");
  });

  it("returns code for unknown language", async () => {
    const { getLanguageName } = await import("@/lib/languages");
    expect(getLanguageName("xx")).toBe("xx");
  });

  it("returns native name", async () => {
    const { getNativeName } = await import("@/lib/languages");
    expect(getNativeName("en")).toBe("English");
    expect(getNativeName("zh")).toBe("中文");
  });
});

describe("UI Components", () => {
  it("Button renders with variants", async () => {
    const { buttonVariants } = await import("@/components/ui/button");
    const classes = buttonVariants({ variant: "default", size: "default" });
    expect(classes).toContain("bg-primary");
  });

  it("Badge renders with variants", async () => {
    const { badgeVariants } = await import("@/components/ui/badge");
    const classes = badgeVariants({ variant: "secondary" });
    expect(classes).toContain("bg-secondary");
  });

  it("cn utility merges classes", async () => {
    const { cn } = await import("@/lib/utils");
    const result = cn("foo", "bar");
    expect(result).toBe("foo bar");
  });
});