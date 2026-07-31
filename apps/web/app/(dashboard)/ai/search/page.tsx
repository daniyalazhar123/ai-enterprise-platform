"use client";

import { motion } from "framer-motion";
import { ExternalLink, FileText, Loader2, Search as SearchIcon, X } from "lucide-react";
import { AiErrorBoundary } from "@/components/ai/error-boundary";
import { EmptyState } from "@/components/ai/empty-state";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { ScrollArea } from "@/components/ui/scroll-area";
import { useSearch } from "@/hooks/use-ai-search";

export default function AISearchPage() {
  const { query, results, isSearching, error, hasSearched, search, reset } = useSearch();

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    const form = e.target as HTMLFormElement;
    const input = form.elements.nativeElement(0) as HTMLInputElement;
    if (input.value.trim()) search(input.value.trim());
  };

  return (
    <AiErrorBoundary>
      <div className="flex h-[calc(100vh-3.5rem)] flex-col">
        <div className="border-b px-6 py-3">
          <div className="flex items-center gap-2">
            <SearchIcon className="h-5 w-5 text-primary" />
            <h1 className="text-lg font-semibold">Semantic Search</h1>
          </div>
        </div>

        <div className="border-b p-4">
          <div className="mx-auto max-w-2xl">
            <form onSubmit={handleSearch} className="relative">
              <SearchIcon className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
              <Input
                defaultValue={query}
                placeholder="Search your documents and textbook content..."
                className="pl-10 pr-10 h-12 text-base"
                disabled={isSearching}
              />
              {query && (
                <button
                  type="button"
                  onClick={reset}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
                >
                  <X className="h-4 w-4" />
                </button>
              )}
            </form>
          </div>
        </div>

        <ScrollArea className="flex-1">
          <div className="mx-auto max-w-3xl py-6 px-6">
            {isSearching ? (
              <div className="flex flex-col items-center justify-center py-24">
                <Loader2 className="h-8 w-8 animate-spin text-primary mb-4" />
                <p className="text-muted-foreground">Searching your documents...</p>
              </div>
            ) : error ? (
              <div className="text-center py-24 text-destructive">
                <p>{error}</p>
              </div>
            ) : !hasSearched ? (
              <EmptyState
                icon="search"
                title="Search your knowledge base"
                description="Enter a query above to semantically search through your uploaded documents and textbook content."
              />
            ) : results.length === 0 ? (
              <EmptyState
                icon="inbox"
                title="No results found"
                description={`No results for "${query}". Try a different query or upload more documents.`}
              />
            ) : (
              <div className="space-y-4">
                <p className="text-sm text-muted-foreground">
                  Found {results.length} result{results.length !== 1 ? "s" : ""} for &ldquo;{query}&rdquo;
                </p>
                {results.map((result, i) => (
                  <motion.div
                    key={result.id}
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: i * 0.05 }}
                  >
                    <div className="rounded-lg border p-4 space-y-2 hover:bg-accent/50 transition-colors">
                      <div className="flex items-center gap-2">
                        <FileText className="h-4 w-4 text-primary" />
                        <span className="font-medium text-sm">{result.title}</span>
                        <Badge variant="secondary" className="ml-auto text-xs">
                          {(result.score * 100).toFixed(0)}% match
                        </Badge>
                      </div>
                      <p className="text-sm text-muted-foreground line-clamp-3">{result.content}</p>
                      <div className="flex items-center gap-2 text-xs text-muted-foreground">
                        {result.section && <span>Section: {result.section}</span>}
                        <span>Source: {result.source}</span>
                      </div>
                    </div>
                  </motion.div>
                ))}
              </div>
            )}
          </div>
        </ScrollArea>
      </div>
    </AiErrorBoundary>
  );
}