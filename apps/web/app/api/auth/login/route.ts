import type { NextRequest } from "next/server";

const API_URL = process.env.API_URL || "http://localhost:8000";

export async function POST(request: NextRequest) {
  const body = await request.json();
  const response = await fetch(`${API_URL}/api/v1/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });

  const data = await response.json();

  if (!response.ok) {
    return Response.json(data, { status: response.status });
  }

  const headers = new Headers();
  headers.append("Set-Cookie", `access_token=${data.access_token}; Path=/; HttpOnly; Secure; SameSite=Strict; Max-Age=900`);

  return Response.json(data, {
    status: 200,
    headers,
  });
}