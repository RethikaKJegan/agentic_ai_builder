import { NextRequest, NextResponse } from "next/server";
import { backendConfig } from "@/lib/backend-config";
import { ApiResponseSchema, SafeErrorSchema } from "@/api/contracts.generated";
import { containsSecret } from "@/api/client";

export const dynamic = "force-dynamic";
const safeId = (value: string | null) => value && /^[a-zA-Z0-9_-]{1,128}$/.test(value) ? value : null;
const cookieNames = new Set(["builder_dev_session", "__Secure-builder_session", "__Secure-builder_login"]);
async function proxy(request: NextRequest, context: { params: Promise<{ path: string[] }> }) {
  let reference = safeId(request.headers.get("x-request-id")) || safeId(request.nextUrl.searchParams.get("request_id")) || `req_${crypto.randomUUID()}`;
  const correlation = safeId(request.headers.get("x-correlation-id")) || reference;
  const error = (code: string, message: string, status: number, retryable = false) => NextResponse.json({ request_id: reference, status,
    data: { correlation_id: correlation, error: { error_code: code, message, request_id: reference, retryable } } },
    { status, headers: { "Cache-Control": "no-store", "X-Request-ID": reference, "X-Correlation-ID": correlation } });
  let config: ReturnType<typeof backendConfig>;
  try { config = backendConfig(); } catch { return error("API_CONFIGURATION_INVALID", "The server API configuration is invalid. Contact the administrator.", 503); }
  const { path } = await context.params;
  if (!path.length || path.some((part) => !/^[a-zA-Z0-9_-]+$/.test(part))) return error("INVALID_ROUTE", "Use a supported API route.", 400);
  const route = path.join("/");
  const webhook = route.startsWith("webhooks/");
  const origin = request.headers.get("origin");
  // NextURL rewrites loopback IPs to localhost; Host retains the actual browser origin.
  const requestOrigin = request.headers.get('host') ? `${request.nextUrl.protocol}//${request.headers.get('host')!.toLowerCase()}` : request.nextUrl.origin;
  if (!config.origins.includes(requestOrigin) || (origin && (!config.origins.includes(origin) || origin !== requestOrigin)) ||
      (!webhook && request.headers.get("sec-fetch-site") === "cross-site")) return error("ORIGIN_NOT_AUTHORIZED", "This request origin is not authorized.", 403);
  if (process.env['BUILDER_ENVIRONMENT'] === 'production' && !webhook && !['GET', 'HEAD', 'OPTIONS'].includes(request.method) && !origin)
    return error("ORIGIN_NOT_AUTHORIZED", "An authorized same-origin request is required.", 403);
  const declared = request.headers.get("content-length");
  if (declared && (!/^\d+$/.test(declared) || Number(declared) > config.maxBody)) return error("REQUEST_TOO_LARGE", "The request exceeds the 2 MiB limit.", 413);
  let body: Uint8Array | undefined;
  if (request.body && !['GET', 'HEAD'].includes(request.method)) {
    const reader = request.body.getReader();
    const chunks: Uint8Array[] = [];
    let size = 0;
    try {
      while (true) {
        const chunk = await reader.read();
        if (chunk.done) break;
        size += chunk.value.byteLength;
        if (size > config.maxBody) { await reader.cancel(); return error("REQUEST_TOO_LARGE", "The request exceeds the 2 MiB limit.", 413); }
        chunks.push(chunk.value);
      }
    } catch { return error("INVALID_REQUEST", "The request body could not be read.", 400); }
    body = new Uint8Array(size);
    let offset = 0;
    for (const chunk of chunks) { body.set(chunk, offset); offset += chunk.byteLength; }
    // Webhook signatures cover exact bytes; never parse or rewrite them.
    if (!webhook && request.headers.get('content-type')?.includes('application/json')) {
      try {
        const parsed = JSON.parse(new TextDecoder().decode(body)) as { request_id?: unknown };
        if (parsed && typeof parsed.request_id === 'string') reference = safeId(parsed.request_id) || reference;
      } catch { return error("INVALID_REQUEST", "The request must contain valid JSON.", 400); }
    }
  }
  const controller = new AbortController();
  const abort = () => controller.abort();
  request.signal.addEventListener('abort', abort, { once: true });
  const timeout = setTimeout(abort, route === 'workflows/plan' ? config.plannerTimeout : config.normalTimeout);
  let streaming = false;
  const cleanup = () => { clearTimeout(timeout); request.signal.removeEventListener('abort', abort); };
  try {
    const url = new URL(path.map(encodeURIComponent).join('/') + request.nextUrl.search, config.upstream);
    const headers = new Headers({ 'x-request-id': reference, 'x-correlation-id': correlation });
    for (const key of ['content-type', 'accept', 'last-event-id', 'origin', 'sec-fetch-site', 'x-builder-signature', 'x-builder-timestamp',
      'x-hub-signature-256', 'x-slack-signature', 'x-slack-request-timestamp']) {
      const value = request.headers.get(key);
      if (value) headers.set(key, value);
    }
    const cookies = request.cookies.getAll().filter((cookie) => cookieNames.has(cookie.name));
    if (cookies.length) headers.set('cookie', cookies.map((c) => `${c.name}=${c.value}`).join('; '));
    const response = await fetch(url, { method: request.method, headers, cache: 'no-store', redirect: 'manual', signal: controller.signal,
      ...(body ? { body: body as BodyInit } : {}) });
    const resultHeaders = new Headers({ 'Cache-Control': 'no-store', 'X-Request-ID': reference, 'X-Correlation-ID': correlation });
    for (const cookie of response.headers.getSetCookie()) {
      const name = cookie.split('=', 1)[0];
      if (name && cookieNames.has(name)) resultHeaders.append('set-cookie', cookie);
    }
    if ([302, 303].includes(response.status) && ['auth/login', 'auth/callback'].includes(route)) {
      const location = response.headers.get('location');
      if (!location) return error('API_INVALID_CONTRACT', 'The login response is invalid.', 502);
      const target = new URL(location);
      if (!(route === 'auth/login' && target.origin === 'https://accounts.google.com' && target.pathname === '/o/oauth2/v2/auth') &&
          !(route === 'auth/callback' && config.origins.includes(target.origin) && target.pathname === '/app')) return error('API_INVALID_CONTRACT', 'The login destination is invalid.', 502);
      resultHeaders.set('location', location);
      return new NextResponse(null, { status: response.status, headers: resultHeaders });
    }
    if (response.headers.get('content-type')?.includes('text/event-stream')) {
      if (!response.ok || !response.body) return error('API_INVALID_CONTRACT', 'The event stream response is invalid.', 502);
      streaming = true;
      resultHeaders.set('Content-Type', 'text/event-stream');
      resultHeaders.set('X-Accel-Buffering', 'no');
      const reader = response.body.getReader();
      // Deadline bounds establishing the stream; disconnect/cancel ends the live body.
      clearTimeout(timeout);
      return new NextResponse(new ReadableStream({
        async pull(stream) {
          try { const chunk = await reader.read(); if (chunk.done) { cleanup(); stream.close(); } else stream.enqueue(chunk.value); }
          catch (failure) { cleanup(); stream.error(failure); }
        },
        async cancel() { controller.abort(); cleanup(); await reader.cancel(); },
      }), { status: response.status, headers: resultHeaders });
    }
    let raw: unknown;
    try { raw = await response.json(); } catch {
      if (controller.signal.aborted) throw new Error('aborted');
      return error('API_MALFORMED_JSON', 'The backend returned malformed JSON.', 502);
    }
    // Google's signed webhook verification challenge is intentionally not a Builder envelope.
    if (webhook && response.ok && raw && typeof raw === 'object' && Object.keys(raw).length === 1 && 'challenge' in raw && typeof raw.challenge === 'string')
      return NextResponse.json(raw, { status: response.status, headers: resultHeaders });
    const parsed = ApiResponseSchema.safeParse(raw);
    if (!parsed.success || parsed.data.status !== response.status || containsSecret(raw)) {
      if (response.status === 404 && response.headers.get('x-builder-service') !== 'workflow-api') {
        let builder = false;
        if (route !== 'session') {
          const identity = await fetch(new URL('session', config.upstream), { headers, cache: 'no-store', redirect: 'manual', signal: controller.signal });
          builder = identity.headers.get('x-builder-service') === 'workflow-api';
          if (!builder) { try { builder = ApiResponseSchema.safeParse(await identity.json()).success; } catch { /* Not a Builder envelope. */ } }
        }
        return error(builder ? 'API_ROUTE_UNAVAILABLE' : 'API_WRONG_SERVICE', builder ? 'This route is unavailable on the configured Builder backend.' : 'The configured upstream is not the Builder API. Check its service and port.', 503, true);
      }
      return error('API_INVALID_CONTRACT', 'The backend response does not match the API contract.', 502);
    }
    if (!response.ok) {
      const data = parsed.data.data;
      if (!SafeErrorSchema.safeParse(data && !Array.isArray(data) ? data['error'] : null).success) return error('API_INVALID_CONTRACT', 'The backend returned an invalid error contract.', 502);
    }
    resultHeaders.set('X-Request-ID', parsed.data.request_id);
    return NextResponse.json(raw, { status: response.status, headers: resultHeaders });
  } catch {
    if (controller.signal.aborted) return error('API_TIMEOUT', 'The API request timed out. Check the current state before retrying an action.', 504, request.method === 'GET');
    return error('API_UNAVAILABLE', 'The workflow backend cannot be reached. Check its service and configured port.', 503, request.method === 'GET');
  } finally { if (!streaming) cleanup(); }
}
export const GET = proxy;
export const POST = proxy;
export const PUT = proxy;
export const DELETE = proxy;
