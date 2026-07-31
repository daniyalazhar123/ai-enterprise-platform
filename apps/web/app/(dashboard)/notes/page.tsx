"use client";

import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";

export default function NotesListPage() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Notes</h1>
        <p className="mt-1 text-muted-foreground">
          Your notes organized by chapter
        </p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>No notes yet</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-muted-foreground">
            Take notes while studying to capture important concepts.
          </p>
        </CardContent>
      </Card>
    </div>
  );
}