"use client";

import Link from "next/link";
import {
  BookOpen,
  Trophy,
  Flame,
  Brain,
  MessageSquare,
  GraduationCap,
  ArrowRight,
} from "lucide-react";
import { useAuth } from "@ai-enterprises/auth";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";

export default function DashboardPage() {
  const { user } = useAuth();

  const quickActions = [
    {
      title: "Continue Reading",
      description: "Pick up where you left off",
      icon: BookOpen,
      href: "/textbook/en/docs/introduction",
      color: "text-blue-500",
    },
    {
      title: "AI Chat",
      description: "Ask questions about any topic",
      icon: MessageSquare,
      href: "/ai/chat",
      color: "text-green-500",
    },
    {
      title: "Take a Quiz",
      description: "Test your knowledge",
      icon: GraduationCap,
      href: "/ai/quiz",
      color: "text-purple-500",
    },
    {
      title: "AI Tutor",
      description: "Learn with Socratic method",
      icon: Brain,
      href: "/ai/tutor",
      color: "text-orange-500",
    },
  ];

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">
          Welcome back{user ? `, ${user.display_name}` : ""}!
        </h1>
        <p className="mt-1 text-muted-foreground">
          Continue your learning journey
        </p>
      </div>

      <div className="grid gap-4 md:grid-cols-3">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Chapters Completed</CardTitle>
            <BookOpen className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">0</div>
            <p className="text-xs text-muted-foreground">of 40 chapters</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Quiz Average</CardTitle>
            <Trophy className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">--</div>
            <p className="text-xs text-muted-foreground">Complete a quiz to see your score</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Day Streak</CardTitle>
            <Flame className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">0</div>
            <p className="text-xs text-muted-foreground">days active</p>
          </CardContent>
        </Card>
      </div>

      <div>
        <h2 className="mb-4 text-xl font-semibold tracking-tight">Quick Actions</h2>
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
          {quickActions.map((action) => {
            const Icon = action.icon;
            return (
              <Link key={action.href} href={action.href}>
                <Card className="transition-colors hover:bg-accent/50 cursor-pointer h-full">
                  <CardHeader>
                    <Icon className={`h-8 w-8 ${action.color}`} />
                    <CardTitle className="text-base mt-2">{action.title}</CardTitle>
                    <CardDescription>{action.description}</CardDescription>
                  </CardHeader>
                  <CardContent>
                    <div className="flex items-center text-sm text-primary">
                      Get started <ArrowRight className="ml-1 h-3 w-3" />
                    </div>
                  </CardContent>
                </Card>
              </Link>
            );
          })}
        </div>
      </div>
    </div>
  );
}