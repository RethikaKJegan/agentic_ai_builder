import { NextRequest, NextResponse } from "next/server";
import { workspaceLoginURL } from "@/lib/workspace-auth-request";
import { validWorkspaceSession, WORKSPACE_COOKIE } from "@/lib/workspace-auth";

export function proxy(request: NextRequest) {
  const path = request.nextUrl.pathname;
  // These retain their existing signature/state validation in the backend.
  if (path.startsWith("/api/backend/webhooks/") ||
      (path === "/api/backend/integrations/google/callback" && request.method === "GET")) return NextResponse.next();
  if (validWorkspaceSession(request.cookies.get(WORKSPACE_COOKIE)?.value)) {
    const response = NextResponse.next();
    response.headers.set("Cache-Control", "private, no-store");
    return response;
  }
  if (path.startsWith("/api/")) {
    const reference = `req_${crypto.randomUUID()}`;
    return NextResponse.json({ request_id: reference, status: 401, data: { error: {
      error_code: "AUTHENTICATION_REQUIRED", message: "Sign in to open the workspace.", request_id: reference, retryable: false,
    } } }, { status: 401, headers: { "Cache-Control": "no-store" } });
  }
  return NextResponse.redirect(workspaceLoginURL(request), { status: 307, headers: { "Cache-Control": "no-store" } });
}
export const config = { matcher: ["/app/:path*", "/api/backend/:path*"] };
