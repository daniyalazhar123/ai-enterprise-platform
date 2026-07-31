"use client";

import { useAuth, useLogout } from "@ai-enterprises/auth";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Separator } from "@/components/ui/separator";

export default function BookmarkListPage() {
  const { user } = useAuth();
  const { logout } = useLogout();

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Bookmarks</h1>
        <p className="mt-1 text-muted-foreground">
          Your saved sections for quick access
        </p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>No bookmarks yet</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-muted-foreground">
            Bookmark sections while reading to find them quickly here.
          </p>
        </CardContent>
      </Card>
    </div>
  );
}