"use client";

import { ExternalLink, FileText } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";
import type { SourceCitation } from "@/lib/ai-types";

interface CitationCardProps {
  citation: SourceCitation;
  index: number;
}

export function CitationCard({ citation, index }: CitationCardProps) {
  return (
    <div
      className={cn(
        "flex gap-3 rounded-lg border p-3 text-sm transition-colors hover:bg-muted/50",
        citation.relevance === "high" && "border-l-2 border-l-emerald-500",
        citation.relevance === "medium" && "border-l-2 border-l-amber-500",
        citation.relevance === "low" && "border-l-2 border-l-slate-300 dark:border-l-slate-600",
      )}
    >
      <div className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-primary/10 text-xs font-medium text-primary">
        {index + 1}
      </div>
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2 mb-1">
          <FileText className="h-3 w-3 text-muted-foreground" />
          <span className="font-medium truncate">{citation.title}</span>
          <Badge variant="secondary" className="text-[10px] px-1.5 py-0">
            {(citation.score * 100).toFixed(0)}%
          </Badge>
        </div>
        <p className="text-muted-foreground line-clamp-2 text-xs">{citation.content}</p>
        {citation.section && (
          <p className="text-[10px] text-muted-foreground mt-1">
            Section: {citation.section}
          </p>
        )}
      </div>
      <ExternalLink className="h-3 w-3 text-muted-foreground shrink-0 mt-1" />
    </div>
  );
}