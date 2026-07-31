import type { NextRequest } from "next/server";

const API_URL = process.env.API_URL || "http://localhost:8000";

export async function POST(request: NextRequest) {
  const body = await request.json();
  const authHeader = request.headers.get("Authorization");

  const headers: Record<string, string> = { "Content-Type": "application/json" };
  if (authHeader) {
    headers["Authorization"] = authHeader;
  }

  const response = await fetch(`${API_URL}/api/v1/auth/logout`, {
    method: "POST",
    headers,
    body: JSON.stringify(body),
  });

  const respHeaders = new Headers();
  respHeaders.append(
    "Set-Cookie",
    "access_token=; Path=/; HttpOnly; Secure; SameSite=Strict; Max-Age=0",
  );

  return new Response(null, {
    status: response.ok ? 204 : response.status,
    headers: respHeaders,
  });
}