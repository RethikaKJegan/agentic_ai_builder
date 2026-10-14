import { NextRequest, NextResponse } from "next/server";

export const dynamic = "force-dynamic";
async function proxy(request: NextRequest, context: { params: Promise<{ path: string[] }> }) {
  if (!["localhost", "127.0.0.1", "[::1]", "praxi.bellcorpstudio.com"].includes(request.nextUrl.hostname)) {
    return NextResponse.json({ request_id: "req_proxy", status: 403, data: { error: { error_code: "DEVELOPMENT_AUTH_LOCAL_ONLY", message: "The local workflow API is restricted to loopback hosts.", request_id: "req_proxy", retryable: false } } }, { status: 403 });
  }
  const { path } = await context.params;
  if (path.some((part) => !/^[a-zA-Z0-9_-]+$/.test(part))) {
    return NextResponse.json({ request_id: "req_proxy", status: 400, data: { error: { error_code: "INVALID_ROUTE", message: "Use a supported API route.", request_id: "req_proxy", retryable: false } } }, { status: 400 });
  }
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 120000);
  try {
    // The repository-local development API started by
    // scripts/serve_ui_test_api.py listens on 8011. Using 8000 here can
    // silently proxy to an unrelated project running on the same machine.
    const url = new URL(path.map(encodeURIComponent).join("/") + request.nextUrl.search, (process.env["BUILDER_API_URL"] || "http://127.0.0.1:8011") + "/");
    const headers: Record<string, string> = {};
    const contentType = request.headers.get("content-type");
    const accept = request.headers.get("accept");
    const lastEventId = request.headers.get("last-event-id");
    const signature = request.headers.get("x-builder-signature");
    const timestamp = request.headers.get("x-builder-timestamp");
    if (contentType) headers["content-type"] = contentType;
    if (accept) headers["accept"] = accept;
    if (lastEventId) headers["last-event-id"] = lastEventId;
    if (signature) headers["x-builder-signature"] = signature;
    if (timestamp) headers["x-builder-timestamp"] = timestamp;
    const cookie = request.headers.get("cookie");
    const origin = request.headers.get("origin");
    if (cookie) headers["cookie"] = cookie;
    if (origin) headers["origin"] = origin;
    const response = await fetch(url, { method: request.method, headers, cache: "no-store", signal: controller.signal,
      ...(request.method === "GET" ? {} : { body: await request.text() }) });
    const responseType = response.headers.get("content-type") || "";
    if (!responseType.includes("text/event-stream")) {
      const body: unknown = await response.json();
      if (!body || typeof body !== "object" || !("request_id" in body) || !("status" in body) || !("data" in body)) {
        // Older Builder instances return FastAPI's raw 404 for newly added routes.
        // Check service identity before claiming the upstream is a different app.
        let builder = false;
        if (response.status === 404 && path.join("/") !== "session") {
          const session = await fetch(new URL("session", url.origin + "/"), { headers, cache: "no-store", signal: controller.signal });
          const identity: unknown = await session.json();
          builder = !!identity && typeof identity === "object" && "request_id" in identity && "status" in identity && "data" in identity;
        }
        return NextResponse.json({ request_id: "req_proxy", status: 503, data: { error: {
          error_code: builder ? "API_ROUTE_UNAVAILABLE" : "API_WRONG_SERVICE", message: builder
            ? "The Builder backend is running without this route. Enable procurement and restart scripts/run_live_backend.py on the configured port."
            : "The configured backend is not the Builder API. Start scripts/run_live_backend.py and set BUILDER_API_URL to its port.",
          request_id: "req_proxy", retryable: true,
        } } }, { status: 503, headers: { "Cache-Control": "no-store" } });
      }
      const result = NextResponse.json(body, { status: response.status, headers: { "Cache-Control": "no-store" } });
      const sessionCookie = response.headers.get("set-cookie");
      if (sessionCookie) result.headers.set("set-cookie", sessionCookie);
      return result;
    }
    const result = new NextResponse(response.body, { status: response.status, headers: { "Cache-Control": "no-store", "Content-Type": "text/event-stream", "X-Accel-Buffering": "no" } });
    const sessionCookie = response.headers.get("set-cookie");
    if (sessionCookie) result.headers.set("set-cookie", sessionCookie);
    return result;
  } catch {
    return NextResponse.json({ request_id: "req_proxy", status: 503, data: { error: { error_code: "API_UNAVAILABLE", message: "The workflow API is unavailable. Start the local API and retry.", request_id: "req_proxy", retryable: true } } }, { status: 503, headers: { "Cache-Control": "no-store" } });
  } finally {
    clearTimeout(timeout);
  }
}
export const GET = proxy;
export const POST = proxy;
export const PUT = proxy;
export const DELETE = proxy;
