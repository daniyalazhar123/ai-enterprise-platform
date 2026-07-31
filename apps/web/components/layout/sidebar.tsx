"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  BookOpen,
  Bookmark,
  FileText,
  LayoutDashboard,
  MessageSquare,
  Bot,
  GraduationCap,
  Briefcase,
  Search,
  Settings,
  TrendingUp,
  Mic,
} from "lucide-react";

import { cn } from "@/lib/utils";

const sidebarLinks = [
  { href: "/dashboard", label: "Dashboard", icon: LayoutDashboard },
  { href: "/textbook/en/docs/introduction", label: "Textbook", icon: BookOpen },
  { href: "/ai/chat", label: "AI Chat", icon: MessageSquare },
  { href: "/ai/tutor", label: "AI Tutor", icon: Bot },
  { href: "/ai/quiz", label: "Quiz", icon: GraduationCap },
  { href: "/ai/interview", label: "Interview", icon: Briefcase },
  { href: "/ai/search", label: "Search", icon: Search },
  { href: "/ai/documents", label: "Documents", icon: FileText },
  { href: "/dashboard/bookmarks", label: "Bookmarks", icon: Bookmark },
  { href: "/dashboard/notes", label: "Notes", icon: FileText },
  { href: "/progress", label: "Progress", icon: TrendingUp },
  { href: "/settings", label: "Settings", icon: Settings },
];

export function Sidebar() {
  const pathname = usePathname();

  return (
    <aside className="fixed left-0 top-14 z-40 h-[calc(100vh-3.5rem)] w-56 border-r bg-background">
      <nav className="flex flex-col gap-1 p-4">
        {sidebarLinks.map((link) => {
          const Icon = link.icon;
          const isActive = pathname === link.href || pathname.startsWith(link.href + "/");
          return (
            <Link
              key={link.href}
              href={link.href}
              className={cn(
                "flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-colors",
                isActive
                  ? "bg-primary/10 text-primary"
                  : "text-muted-foreground hover:bg-accent hover:text-accent-foreground",
              )}
            >
              <Icon className="h-4 w-4" />
              {link.label}
            </Link>
          );
        })}
      </nav>
    </aside>
  );
}