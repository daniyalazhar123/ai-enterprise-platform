import type { NextRequest } from "next/server";

const API_URL = process.env.API_URL || "http://localhost:8000";

export async function POST(request: NextRequest) {
  const body = await request.json();
  const cookie = request.cookies.get("__Host-refresh_token");

  const headers: Record<string, string> = { "Content-Type": "application/json" };
  if (cookie) {
    headers["Cookie"] = `__Host-refresh_token=${cookie.value}`;
  }

  const response = await fetch(`${API_URL}/api/v1/auth/refresh`, {
    method: "POST",
    headers,
    body: JSON.stringify(body),
  });

  const data = await response.json();

  if (!response.ok) {
    return Response.json(data, { status: response.status });
  }

  const respHeaders = new Headers();
  respHeaders.append(
    "Set-Cookie",
    `access_token=${data.access_token}; Path=/; HttpOnly; Secure; SameSite=Strict; Max-Age=900`,
  );

  return Response.json(data, {
    status: 200,
    headers: respHeaders,
  });
}