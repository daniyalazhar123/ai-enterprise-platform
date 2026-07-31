"use client";

import { useTheme } from "next-themes";
import { useCallback, useState } from "react";
import { AiErrorBoundary } from "@/components/ai/error-boundary";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Separator } from "@/components/ui/separator";
import { Switch } from "@/components/ui/switch";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { VoiceSettings } from "@/components/voice/voice-components";
import { usePreferences } from "@/hooks/use-ai-preferences";
import { LANGUAGES } from "@/lib/languages";

export default function SettingsPage() {
  const { theme, setTheme } = useTheme();
  const { preferences, setLocale, setVoiceEnabled, setVoiceSpeed, setVoiceGender } = usePreferences();
  const [saving, setSaving] = useState(false);

  return (
    <AiErrorBoundary>
      <div className="flex h-[calc(100vh-3.5rem)] flex-col">
        <div className="border-b px-6 py-3">
          <h1 className="text-lg font-semibold">Settings</h1>
        </div>

        <ScrollArea className="flex-1">
          <div className="mx-auto max-w-2xl py-6 px-6">
            <Tabs defaultValue="appearance" className="space-y-6">
              <TabsList>
                <TabsTrigger value="appearance">Appearance</TabsTrigger>
                <TabsTrigger value="language">Language</TabsTrigger>
                <TabsTrigger value="voice">Voice</TabsTrigger>
                <TabsTrigger value="account">Account</TabsTrigger>
              </TabsList>

              <TabsContent value="appearance" className="space-y-6">
                <Card className="p-6 space-y-4">
                  <div>
                    <h3 className="font-semibold mb-1">Theme</h3>
                    <p className="text-sm text-muted-foreground mb-4">Choose your preferred color scheme.</p>
                    <div className="grid grid-cols-3 gap-3">
                      {[
                        { value: "light", label: "Light", icon: "☀️" },
                        { value: "dark", label: "Dark", icon: "🌙" },
                        { value: "system", label: "System", icon: "💻" },
                      ].map((t) => (
                        <button
                          key={t.value}
                          onClick={() => setTheme(t.value)}
                          className={`flex flex-col items-center gap-2 rounded-lg border p-4 transition-colors ${
                            theme === t.value
                              ? "border-primary bg-primary/10"
                              : "hover:bg-accent"
                          }`}
                        >
                          <span className="text-2xl">{t.icon}</span>
                          <span className="text-sm font-medium">{t.label}</span>
                        </button>
                      ))}
                    </div>
                  </div>
                </Card>
              </TabsContent>

              <TabsContent value="language" className="space-y-6">
                <Card className="p-6 space-y-4">
                  <div>
                    <h3 className="font-semibold mb-1">Language</h3>
                    <p className="text-sm text-muted-foreground mb-4">Select your preferred language.</p>
                    <Select value={preferences.locale} onValueChange={setLocale}>
                      <SelectTrigger className="w-full">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        {LANGUAGES.map((lang) => (
                          <SelectItem key={lang.code} value={lang.code}>
                            <span className="flex items-center gap-2">
                              <span>{lang.native_name}</span>
                              <span className="text-muted-foreground">({lang.name})</span>
                            </span>
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>
                </Card>
              </TabsContent>

              <TabsContent value="voice" className="space-y-6">
                <Card className="p-6">
                  <VoiceSettings />
                </Card>
              </TabsContent>

              <TabsContent value="account" className="space-y-6">
                <Card className="p-6 space-y-4">
                  <h3 className="font-semibold">Account Settings</h3>
                  <p className="text-sm text-muted-foreground">
                    Manage your account settings and preferences from your profile page.
                  </p>
                  <Button variant="outline" onClick={() => window.location.href = "/dashboard/profile"}>
                    Go to Profile
                  </Button>
                </Card>
              </TabsContent>
            </Tabs>
          </div>
        </ScrollArea>
      </div>
    </AiErrorBoundary>
  );
}