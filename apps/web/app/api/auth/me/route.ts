import type { NextRequest } from "next/server";

const API_URL = process.env.API_URL || "http://localhost:8000";

export async function GET(request: NextRequest) {
  const authHeader = request.headers.get("Authorization");

  const headers: Record<string, string> = {};
  if (authHeader) {
    headers["Authorization"] = authHeader;
  }

  const response = await fetch(`${API_URL}/api/v1/auth/me`, { headers });
  const data = await response.json();

  return Response.json(data, { status: response.status });
}