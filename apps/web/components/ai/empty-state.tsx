"use client";

import { motion } from "framer-motion";
import { Bot, FileText, Inbox, MessageSquare, Search } from "lucide-react";

interface EmptyStateProps {
  icon?: "chat" | "search" | "documents" | "quiz" | "inbox";
  title: string;
  description?: string;
  action?: React.ReactNode;
}

const iconMap = {
  chat: MessageSquare,
  search: Search,
  documents: FileText,
  quiz: Bot,
  inbox: Inbox,
};

export function EmptyState({ icon = "inbox", title, description, action }: EmptyStateProps) {
  const Icon = iconMap[icon];

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3 }}
      className="flex flex-col items-center justify-center py-16 px-4 text-center"
    >
      <div className="rounded-full bg-muted p-4 mb-4">
        <Icon className="h-8 w-8 text-muted-foreground" />
      </div>
      <h3 className="text-lg font-semibold mb-1">{title}</h3>
      {description && (
        <p className="text-sm text-muted-foreground max-w-sm mb-4">{description}</p>
      )}
      {action}
    </motion.div>
  );
}