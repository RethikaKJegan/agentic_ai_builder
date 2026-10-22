import { NextRequest, NextResponse } from "next/server";
import { WORKSPACE_COOKIE } from "@/lib/workspace-auth";
import { sameOriginLoginRequest, secureLoginCookie } from "@/lib/workspace-auth-request";

export async function POST(request: NextRequest) {
  if (!sameOriginLoginRequest(request)) return NextResponse.json({ error: "Use this website to sign out." }, { status: 403 });
  const response = NextResponse.json({ ok: true }, { headers: { "Cache-Control": "no-store" } });
  response.cookies.set(WORKSPACE_COOKIE, "", { httpOnly: true, secure: secureLoginCookie(request), sameSite: "lax", path: "/", maxAge: 0 });
  for (const name of ["builder_dev_session", "__Secure-builder_session", "__Secure-builder_login"]) {
    response.cookies.set(name, "", { httpOnly: true, secure: name.startsWith("__Secure-") || secureLoginCookie(request), sameSite: "strict", path: "/api/backend", maxAge: 0 });
  }
  return response;
}
