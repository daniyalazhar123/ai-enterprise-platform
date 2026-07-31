"use client";

import { useCallback, useEffect, useState } from "react";
import { deleteDocument, listDocuments, uploadDocument } from "@/lib/ai-api";
import type { DocumentInfo } from "@/lib/ai-types";

export function useDocuments() {
  const [documents, setDocuments] = useState<DocumentInfo[]>([]);
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchDocuments = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await listDocuments();
      setDocuments(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load documents");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchDocuments();
  }, [fetchDocuments]);

  const upload = useCallback(async (file: File, chapterId?: string, section?: string) => {
    setUploading(true);
    setError(null);
    try {
      const result = await uploadDocument(file, chapterId, section);
      setDocuments((prev) => [
        {
          id: result.id,
          filename: result.filename,
          content_type: result.content_type,
          chunk_count: result.chunks,
          file_size: file.size,
        },
        ...prev,
      ]);
      return result;
    } catch (err) {
      const message = err instanceof Error ? err.message : "Upload failed";
      setError(message);
      throw err;
    } finally {
      setUploading(false);
    }
  }, []);

  const remove = useCallback(async (id: string) => {
    try {
      await deleteDocument(id);
      setDocuments((prev) => prev.filter((d) => d.id !== id));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to delete document");
    }
  }, []);

  return {
    documents,
    loading,
    uploading,
    error,
    refetch: fetchDocuments,
    upload,
    remove,
  };
}