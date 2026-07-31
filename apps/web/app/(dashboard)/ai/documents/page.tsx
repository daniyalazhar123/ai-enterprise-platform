"use client";

import { motion } from "framer-motion";
import {
  FileText,
  Loader2,
  Plus,
  Trash2,
  Upload,
  File,
  FileType,
  ChevronRight,
} from "lucide-react";
import { useCallback, useRef, useState } from "react";
import { AiErrorBoundary } from "@/components/ai/error-boundary";
import { EmptyState } from "@/components/ai/empty-state";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { ScrollArea } from "@/components/ui/scroll-area";
import { SkeletonCard } from "@/components/ui/skeleton";
import { useDocuments } from "@/hooks/use-ai-documents";

export default function AIDocumentsPage() {
  const { documents, loading, uploading, error, refetch, upload, remove } = useDocuments();
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [deleting, setDeleting] = useState<string | null>(null);

  const handleUploadClick = () => fileInputRef.current?.click();

  const handleFileChange = useCallback(async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    try {
      await upload(file);
    } catch {
      /* error handled by hook */
    }
    e.target.value = "";
  }, [upload]);

  const handleDelete = useCallback(async (id: string) => {
    setDeleting(id);
    await remove(id);
    setDeleting(null);
  }, [remove]);

  const formatSize = (bytes: number) => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };

  const getFileIcon = (type: string) => {
    if (type.includes("pdf")) return <FileText className="h-5 w-5 text-red-500" />;
    if (type.includes("markdown") || type.includes("md")) return <FileType className="h-5 w-5 text-blue-500" />;
    return <File className="h-5 w-5 text-muted-foreground" />;
  };

  return (
    <AiErrorBoundary>
      <div className="flex h-[calc(100vh-3.5rem)] flex-col">
        <div className="border-b px-6 py-3">
          <div className="flex items-center gap-2">
            <FileText className="h-5 w-5 text-primary" />
            <h1 className="text-lg font-semibold">Documents</h1>
          </div>
        </div>

        <div className="border-b p-4">
          <div className="flex items-center gap-2">
            <Button onClick={handleUploadClick} disabled={uploading} className="gap-2">
              {uploading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Upload className="h-4 w-4" />}
              {uploading ? "Uploading..." : "Upload Document"}
            </Button>
            <input
              ref={fileInputRef}
              type="file"
              accept=".pdf,.md,.mdx,.txt"
              className="hidden"
              onChange={handleFileChange}
            />
            <Button variant="outline" size="icon" onClick={refetch} disabled={loading}>
              <Loader2 className={`h-4 w-4 ${loading ? "animate-spin" : ""}`} />
            </Button>
          </div>
          {error && <p className="text-sm text-destructive mt-2">{error}</p>}
        </div>

        <ScrollArea className="flex-1">
          <div className="mx-auto max-w-3xl py-6 px-6">
            {loading ? (
              <div className="space-y-3">
                {[1, 2, 3].map((i) => <SkeletonCard key={i} />)}
              </div>
            ) : documents.length === 0 ? (
              <EmptyState
                icon="documents"
                title="No documents uploaded"
                description="Upload PDF, Markdown, or text files to search through them using AI."
                action={
                  <Button onClick={handleUploadClick} variant="outline" className="gap-2">
                    <Plus className="h-4 w-4" />
                    Upload your first document
                  </Button>
                }
              />
            ) : (
              <div className="space-y-2">
                {documents.map((doc, i) => (
                  <motion.div
                    key={doc.id}
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: i * 0.03 }}
                  >
                    <Card className="p-4 flex items-center gap-3 hover:bg-accent/50 transition-colors group">
                      {getFileIcon(doc.content_type)}
                      <div className="flex-1 min-w-0">
                        <p className="text-sm font-medium truncate">{doc.filename}</p>
                        <div className="flex items-center gap-3 text-xs text-muted-foreground">
                          <span>{formatSize(doc.file_size)}</span>
                          <span>{doc.chunk_count} chunks</span>
                          <Badge variant="outline" className="text-[10px]">{doc.content_type}</Badge>
                        </div>
                      </div>
                      <Button
                        variant="ghost"
                        size="icon"
                        className="h-8 w-8 opacity-0 group-hover:opacity-100 transition-opacity shrink-0"
                        onClick={() => handleDelete(doc.id)}
                        disabled={deleting === doc.id}
                        aria-label={`Delete ${doc.filename}`}
                      >
                        {deleting === doc.id ? <Loader2 className="h-4 w-4 animate-spin" /> : <Trash2 className="h-4 w-4 text-destructive" />}
                      </Button>
                    </Card>
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