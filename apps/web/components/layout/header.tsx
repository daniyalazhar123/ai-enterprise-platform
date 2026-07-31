"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { BookOpen, LogOut, User } from "lucide-react";
import { useAuth, useLogout } from "@ai-enterprises/auth";
import { Button } from "@/components/ui/button";
import { Avatar } from "@/components/ui/avatar";

export function Header() {
  const { user } = useAuth();
  const { logout, loading } = useLogout();
  const pathname = usePathname();

  const isAuthPage = pathname.startsWith("/login") || pathname.startsWith("/register");

  if (isAuthPage) {
    return (
      <header className="fixed top-0 z-50 w-full border-b bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60">
        <div className="container flex h-14 items-center">
          <Link href="/" className="flex items-center gap-2 font-semibold">
            <BookOpen className="h-5 w-5 text-primary" />
            <span>AI Enterprises</span>
          </Link>
        </div>
      </header>
    );
  }

  return (
    <header className="fixed top-0 z-50 w-full border-b bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60">
      <div className="container flex h-14 items-center justify-between">
        <div className="flex items-center gap-6">
          <Link href="/dashboard" className="flex items-center gap-2 font-semibold">
            <BookOpen className="h-5 w-5 text-primary" />
            <span className="hidden sm:inline">AI Enterprises</span>
          </Link>
        </div>

        <div className="flex items-center gap-4">
          {user && (
            <>
              <Link href="/dashboard/profile">
                <Button variant="ghost" size="sm" className="gap-2">
                  <Avatar
                    src={user.avatar_url}
                    alt={user.display_name}
                    fallback={user.display_name}
                    className="h-6 w-6"
                  />
                  <span className="hidden sm:inline text-sm">{user.display_name}</span>
                </Button>
              </Link>
              <Button
                variant="ghost"
                size="icon"
                onClick={() => logout()}
                disabled={loading}
                title="Logout"
              >
                <LogOut className="h-4 w-4" />
              </Button>
            </>
          )}
        </div>
      </div>
    </header>
  );
}