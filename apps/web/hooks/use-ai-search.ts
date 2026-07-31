"use client";

import { useCallback, useState } from "react";
import { searchDocuments } from "@/lib/ai-api";
import type { SearchResult } from "@/lib/ai-types";

export function useSearch() {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<SearchResult[]>([]);
  const [isSearching, setIsSearching] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [hasSearched, setHasSearched] = useState(false);

  const search = useCallback(async (searchQuery: string) => {
    setIsSearching(true);
    setError(null);
    setQuery(searchQuery);

    try {
      const data = await searchDocuments(searchQuery);
      setResults(data);
      setHasSearched(true);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Search failed");
    } finally {
      setIsSearching(false);
    }
  }, []);

  const reset = useCallback(() => {
    setQuery("");
    setResults([]);
    setHasSearched(false);
    setError(null);
  }, []);

  return {
    query,
    results,
    isSearching,
    error,
    hasSearched,
    search,
    reset,
  };
}