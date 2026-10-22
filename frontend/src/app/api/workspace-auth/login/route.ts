import { NextRequest, NextResponse } from "next/server";
import { createWorkspaceSession, SESSION_SECONDS, verifyWorkspacePassword, WORKSPACE_COOKIE } from "@/lib/workspace-auth";
import { sameOriginLoginRequest, secureLoginCookie } from "@/lib/workspace-auth-request";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";
// Bounded across all callers, so forged IP headers cannot bypass the attempt budget.
let windowStart = 0;
let attempts = 0;
const result = (error: string, status: number) => NextResponse.json({ error }, { status, headers: { "Cache-Control": "no-store" } });
export async function POST(request: NextRequest) {
  if (!sameOriginLoginRequest(request)) return result("Use the login form on this website.", 403);
  const now = Date.now();
  if (now - windowStart >= 60_000) { windowStart = now; attempts = 0; }
  if (++attempts > 20) {
    const response = result("Too many attempts. Please try again in a minute.", 429);
    response.headers.set("Retry-After", "60");
    return response;
  }
  if (!request.headers.get("content-type")?.includes("application/json")) return result("Enter your email and password.", 400);
  // Read a bounded body even when Content-Length is omitted or untrusted.
  let text = "";
  const reader = request.body?.getReader();
  if (!reader) return result("Enter your email and password.", 400);
  try {
    const decoder = new TextDecoder();
    let bytes = 0;
    while (true) {
      const chunk = await reader.read();
      if (chunk.done) break;
      bytes += chunk.value.byteLength;
      if (bytes > 2048) { await reader.cancel(); return result("The login request is too large.", 413); }
      text += decoder.decode(chunk.value, { stream: true });
    }
    text += decoder.decode();
  } catch { return result("Enter your email and password.", 400); }
  let body: unknown;
  try { body = JSON.parse(text); } catch { return result("Enter your email and password.", 400); }
  if (!body || typeof body !== "object" || !("email" in body) || !("password" in body)) return result("Enter your email and password.", 400);
  try {
    if (!await verifyWorkspacePassword(body.email, body.password)) return result("The email or password is incorrect.", 401);
    const response = NextResponse.json({ ok: true }, { headers: { "Cache-Control": "no-store" } });
    response.cookies.set(WORKSPACE_COOKIE, createWorkspaceSession(), {
      httpOnly: true, secure: secureLoginCookie(request), sameSite: "lax", path: "/", maxAge: SESSION_SECONDS,
    });
    return response;
  } catch { return result("Workspace sign-in is not configured. Contact the administrator.", 503); }
}
