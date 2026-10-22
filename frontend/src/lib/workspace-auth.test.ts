import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { scryptSync } from "node:crypto";
import { NextRequest } from "next/server";
import { createWorkspaceSession, SESSION_SECONDS, validWorkspaceSession, verifyWorkspacePassword, WORKSPACE_COOKIE } from "./workspace-auth";
import { proxy } from "@/proxy";
import { POST as login } from "@/app/api/workspace-auth/login/route";
import { POST as logout } from "@/app/api/workspace-auth/logout/route";
const origin = "http://127.0.0.1:3100";
const email = "engineering@bellcorpstudio.com";
const password = "12345678";
beforeEach(() => {
  vi.useFakeTimers(); vi.setSystemTime(new Date("2026-10-22T10:00:00Z"));
  vi.stubEnv("BUILDER_LOGIN_SECRET", "unit-test-signing-secret-with-more-than-32-characters");
  const salt = "a".repeat(32);
  vi.stubEnv("BUILDER_LOGIN_PASSWORD_HASH", `${salt}:${scryptSync(password, salt, 64).toString("hex")}`);
  vi.stubEnv("BUILDER_ENVIRONMENT", "test");
  vi.stubEnv("BUILDER_UI_ORIGINS", origin);
});
afterEach(() => { vi.unstubAllEnvs(); vi.useRealTimers(); });
const request = (path: string, body: unknown, headers: Record<string, string> = {}) => new NextRequest(origin + path, {
  method: "POST", headers: { "content-type": "application/json", host: "127.0.0.1:3100", origin, ...headers }, body: JSON.stringify(body),
});
it("verifies the configured account and rejects incorrect email/password", async () => {
  expect(await verifyWorkspacePassword(email, password)).toBe(true);
  expect(await verifyWorkspacePassword("other@example.com", password)).toBe(false);
  expect(await verifyWorkspacePassword(email, "87654321")).toBe(false);
});
it("rejects missing configuration", async () => {
  vi.stubEnv("BUILDER_LOGIN_SECRET", "");
  await expect(verifyWorkspacePassword(email, password)).rejects.toThrow();
  expect(validWorkspaceSession(createInvalidToken())).toBe(false);
});
function createInvalidToken() { return "1".repeat(10) + "." + "a".repeat(48) + "." + "b".repeat(64); }
it("rejects tampered and expired sessions, and preserves valid sessions across requests", () => {
  const token = createWorkspaceSession();
  expect(validWorkspaceSession(token)).toBe(true);
  expect(validWorkspaceSession(token.slice(0, -1) + (token.endsWith("a") ? "b" : "a"))).toBe(false);
  expect(validWorkspaceSession(token, Date.now() + SESSION_SECONDS * 1000)).toBe(false);
  vi.stubEnv("BUILDER_LOGIN_SECRET", "rotated-secret-with-more-than-32-characters");
  expect(validWorkspaceSession(token)).toBe(false);
});
it.each(["/app", "/app/workflows/existing", "/app/data-intelligence"])("redirects anonymous %s", path => {
  const response = proxy(new NextRequest(origin + path));
  expect(response.status).toBe(307); expect(response.headers.get("location")).toMatch(/\/login$/);
});
it.each(["session", "workflows", "integrations/google/status", "data-sources"])("blocks anonymous API %s before backend bootstrap", async path => {
  const response = proxy(new NextRequest(origin + "/api/backend/" + path));
  expect(response.status).toBe(401);
  expect((await response.json()).data.error.error_code).toBe("AUTHENTICATION_REQUIRED");
});
it("uses the public HTTPS origin for redirects behind the TLS gateway", () => {
  const response = proxy(new NextRequest("http://127.0.0.1:3001/app", { headers: { host: "praxi.bellcorpstudio.com" } }));
  expect(response.headers.get("location")).toBe("https://praxi.bellcorpstudio.com/login");
});
it("accepts a valid website cookie and leaves backend authority separate", () => {
  const response = proxy(new NextRequest(origin + "/api/backend/session", { headers: { cookie: `${WORKSPACE_COOKIE}=${createWorkspaceSession()}` } }));
  expect(response.headers.get("x-middleware-next")).toBe("1");
  expect(response.headers.get("set-cookie")).toBeNull();
});
it.each(["/api/backend/webhooks/slack", "/api/backend/integrations/google/callback"])("preserves provider verification at %s", path => {
  expect(proxy(new NextRequest(origin + path)).headers.get("x-middleware-next")).toBe("1");
});
it("does not exempt POST requests to the Google callback", () => {
  expect(proxy(new NextRequest(origin + "/api/backend/integrations/google/callback", { method: "POST" })).status).toBe(401);
});
it("sets an HttpOnly cookie on correct login and does not disclose credentials", async () => {
  const response = await login(request("/api/workspace-auth/login", { email, password }));
  expect(response.status).toBe(200);
  expect(response.headers.get("set-cookie")).toContain("HttpOnly");
  expect(response.headers.get("set-cookie")).toContain("SameSite=lax");
  expect(response.headers.get("set-cookie")).toContain("Path=/");
  expect(await response.json()).toEqual({ ok: true });
  expect(validWorkspaceSession(response.cookies.get(WORKSPACE_COOKIE)?.value)).toBe(true);
});
it("uses a Secure cookie on HTTPS", async () => {
  vi.stubEnv("BUILDER_ENVIRONMENT", "production");
  vi.stubEnv("BUILDER_UI_ORIGINS", "https://praxi.bellcorpstudio.com");
  const response = await login(new NextRequest("https://praxi.bellcorpstudio.com/api/workspace-auth/login", {
    method: "POST", headers: { origin: "https://praxi.bellcorpstudio.com", "content-type": "application/json" }, body: JSON.stringify({ email, password }),
  }));
  expect(response.status).toBe(200); expect(response.cookies.get(WORKSPACE_COOKIE)?.secure).toBe(true);
});
it("accepts the existing public TLS login without changing private backend origins", async () => {
  const response = await login(new NextRequest("https://praxi.bellcorpstudio.com/api/workspace-auth/login", {
    method: "POST", headers: { host: "praxi.bellcorpstudio.com", origin: "https://praxi.bellcorpstudio.com", "content-type": "application/json" }, body: JSON.stringify({ email, password }),
  }));
  expect(response.status).toBe(200);
  expect(response.cookies.get(WORKSPACE_COOKIE)?.secure).toBe(true);
});
it("rejects invalid credentials without setting a cookie", async () => {
  const response = await login(request("/api/workspace-auth/login", { email, password: "wrong" }));
  expect(response.status).toBe(401); expect(response.headers.get("set-cookie")).toBeNull();
});
it("rejects cross-origin login/logout and missing Origin", async () => {
  for (const handler of [login, logout]) {
    expect((await handler(request("/api/workspace-auth/login", {}, { origin: "https://evil.example" }))).status).toBe(403);
    expect((await handler(new NextRequest(origin + "/api/workspace-auth/logout", { method: "POST" }))).status).toBe(403);
  }
});
it("bounds request size and validates JSON", async () => {
  expect((await login(request("/api/workspace-auth/login", { email, password: "a".repeat(3000) }))).status).toBe(413);
  expect((await login(request("/api/workspace-auth/login", null))).status).toBe(400);
});
it("bounds login attempts even when callers forge different IPs", async () => {
  vi.setSystemTime(new Date("2026-10-22T11:00:00Z"));
  for (let i = 0; i < 20; i++) expect((await login(request("/api/workspace-auth/login", {}))).status).toBe(400);
  const response = await login(request("/api/workspace-auth/login", { email, password }, { "x-forwarded-for": "192.0.2.10" }));
  expect(response.status).toBe(429); expect(response.headers.get("retry-after")).toBe("60");
});
it("clears gate and backend cookies without touching storage", async () => {
  const response = await logout(request("/api/workspace-auth/logout", {}));
  expect(response.status).toBe(200);
  expect(response.cookies.get(WORKSPACE_COOKIE)?.maxAge).toBe(0);
  expect(response.cookies.get("builder_dev_session")?.maxAge).toBe(0);
});
