import type { NextRequest } from "next/server";
import { backendConfig } from "@/lib/backend-config";

export function sameOriginLoginRequest(request: NextRequest) {
  const origin = request.headers.get("origin");
  if (!origin || request.headers.get("sec-fetch-site") === "cross-site") return false;
  try {
    const target = new URL(origin);
    // Host is retained by the TLS reverse proxy for /api/workspace-auth/.
    const host = request.headers.get("host") || request.nextUrl.host;
    const publicOrigin = process.env["BUILDER_LOGIN_PUBLIC_ORIGIN"] || "https://praxi.bellcorpstudio.com";
    const publicURL = new URL(publicOrigin);
    if (publicURL.origin !== publicOrigin || publicURL.protocol !== "https:" || publicURL.username || publicURL.password) return false;
    const allowed = [...backendConfig().origins, publicOrigin];
    return target.host === host.toLowerCase() && allowed.includes(origin);
  } catch { return false; }
}
export function secureLoginCookie(request: NextRequest) {
  return process.env["BUILDER_ENVIRONMENT"] === "production" || request.headers.get("origin")?.startsWith("https://") === true;
}

export function workspaceLoginURL(request: NextRequest) {
  const publicOrigin = process.env["BUILDER_LOGIN_PUBLIC_ORIGIN"] || "https://praxi.bellcorpstudio.com";
  const publicURL = new URL(publicOrigin);
  if (publicURL.origin !== publicOrigin || publicURL.protocol !== "https:" || publicURL.username || publicURL.password) throw new Error("Configure an exact HTTPS login origin.");
  const host = request.headers.get("host") || request.nextUrl.host;
  const localOrigin = `${request.nextUrl.protocol}//${host.toLowerCase()}`;
  return new URL("/login", backendConfig().origins.includes(localOrigin) ? localOrigin : publicOrigin);
}
