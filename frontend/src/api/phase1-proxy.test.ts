import { webcrypto } from 'node:crypto';
import { TextEncoder, TextDecoder } from 'node:util';
import { afterEach, beforeEach, expect, it, vi } from 'vitest';
import { NextRequest } from 'next/server';
import { GET, POST, PUT } from '@/app/api/backend/[...path]/route';
import { backendConfig } from '@/lib/backend-config';

const base = 'http://127.0.0.1:3001/api/backend/';
const context = (path: string) => ({ params: Promise.resolve({ path: path.split('/') }) });
const envelope = (status = 200) => ({ request_id: 'req_backend', status, data: status >= 400 ? {
  error: { error_code: status === 401 ? 'AUTHENTICATION_REQUIRED' : 'OPERATION_NOT_AUTHORIZED', message: 'Access denied.', request_id: 'req_backend', retryable: false },
} : { items: [] } });
const response = (status = 200) => new Response(JSON.stringify(envelope(status)), { status, headers: { 'content-type': 'application/json' } });
beforeEach(() => { vi.stubGlobal('crypto', webcrypto); vi.stubGlobal('TextEncoder', TextEncoder); vi.stubGlobal('TextDecoder', TextDecoder); });
afterEach(() => { vi.restoreAllMocks(); vi.unstubAllGlobals(); vi.unstubAllEnvs(); vi.useRealTimers(); });

it('defaults to live port 8000 and supports an explicit test API on 8011', () => {
  vi.stubEnv('BUILDER_API_URL', '');
  expect(backendConfig().upstream.href).toBe('http://127.0.0.1:8000/');
  vi.stubEnv('BUILDER_API_URL', 'http://127.0.0.1:8011');
  expect(backendConfig().upstream.port).toBe('8011');
});

it.each(['https://public.example', 'http://user:password@127.0.0.1:8000', 'http://127.0.0.1:8000/path', 'file:///etc/passwd', 'http://127.0.0.1:8000?destination=evil'])('rejects invalid upstream %s', (value) => {
  vi.stubEnv('BUILDER_API_URL', value);
  expect(() => backendConfig()).toThrow();
});

it.each([401, 403, 409, 422, 500])('preserves upstream HTTP %s and its canonical error', async (status) => {
  const fetch = vi.fn().mockResolvedValue(response(status)); vi.stubGlobal('fetch', fetch);
  const result = await GET(new NextRequest(base + 'workflows'), context('workflows'));
  expect(result.status).toBe(status);
  expect(await result.json()).toEqual(envelope(status));
  expect(result.headers.get('cache-control')).toBe('no-store');
});

it('forwards permitted cookies, correlation IDs and exact mutation bodies once', async () => {
  const fetch = vi.fn().mockResolvedValue(response()); vi.stubGlobal('fetch', fetch);
  const body = JSON.stringify({ request_id: 'req_action', operation: 'save_workflow_version', payload: {} });
  const request = new NextRequest(base + 'workflows/id/versions/1', { method: 'PUT', headers: {
    'content-type': 'application/json', 'host': '127.0.0.1:3001', 'origin': 'http://127.0.0.1:3001', 'x-correlation-id': 'corr_action',
    'cookie': 'builder_dev_session=local-session; unrelated=private', 'authorization': 'Bearer do-not-forward',
  }, body });
  const result = await PUT(request, context('workflows/id/versions/1'));
  expect(await result.json()).toEqual(envelope());
  expect(fetch).toHaveBeenCalledTimes(1);
  const options = fetch.mock.calls[0]![1] as RequestInit;
  const headers = new Headers(options.headers);
  expect(headers.get('cookie')).toBe('builder_dev_session=local-session');
  expect(headers.get('authorization')).toBeNull();
  expect(headers.get('x-request-id')).toBe('req_action');
  expect(headers.get('x-correlation-id')).toBe('corr_action');
  expect(new TextDecoder().decode(options.body as Uint8Array)).toBe(body);
  expect(options.redirect).toBe('manual');
});

it('supports exact public HTTPS origin only in production configuration', async () => {
  vi.stubEnv('BUILDER_ENVIRONMENT', 'production');
  const fetch = vi.fn().mockResolvedValue(response()); vi.stubGlobal('fetch', fetch);
  const publicBase = 'https://praxi.bellcorpstudio.com/api/backend/';
  expect((await GET(new NextRequest(publicBase + 'session'), context('session'))).status).toBe(200);
  for (const origin of ['http://praxi.bellcorpstudio.com', 'https://praxi.bellcorpstudio.com:444', 'https://evil.example']) {
    expect((await POST(new NextRequest(publicBase + 'workflows/plan', { method: 'POST', headers: { origin } }), context('workflows/plan'))).status).toBe(403);
  }
  expect((await POST(new NextRequest(publicBase + 'workflows/plan', { method: 'POST' }), context('workflows/plan'))).status).toBe(403);
  expect(fetch).toHaveBeenCalledTimes(1);
});

it('rejects requests above the body limit before calling the backend', async () => {
  const fetch = vi.fn(); vi.stubGlobal('fetch', fetch);
  const result = await POST(new NextRequest(base + 'workflows/plan', { method: 'POST', body: 'x'.repeat(2 * 1024 * 1024 + 1) }), context('workflows/plan'));
  expect(result.status).toBe(413);
  expect(fetch).not.toHaveBeenCalled();
});

it('reports malformed JSON separately from invalid contracts', async () => {
  const fetch = vi.fn().mockResolvedValueOnce(new Response('not-json')).mockResolvedValueOnce(new Response(JSON.stringify({ result: 'unknown' })));
  vi.stubGlobal('fetch', fetch);
  expect(await (await GET(new NextRequest(base + 'session'), context('session'))).json()).toMatchObject({ data: { error: { error_code: 'API_MALFORMED_JSON' } } });
  expect(await (await GET(new NextRequest(base + 'session'), context('session'))).json()).toMatchObject({ data: { error: { error_code: 'API_INVALID_CONTRACT' } } });
});

it('does not retry a mutation after network failure', async () => {
  const fetch = vi.fn().mockRejectedValue(new TypeError('offline')); vi.stubGlobal('fetch', fetch);
  const result = await POST(new NextRequest(base + 'workflows/plan', { method: 'POST', body: '{}' }), context('workflows/plan'));
  expect(await result.json()).toMatchObject({ data: { error: { error_code: 'API_UNAVAILABLE', retryable: false } } });
  expect(fetch).toHaveBeenCalledTimes(1);
});

it('times out normal APIs separately from long synchronous planning', async () => {
  vi.useFakeTimers();
  vi.stubGlobal('fetch', vi.fn((_url: unknown, options: RequestInit) => new Promise((_resolve, reject) => options.signal?.addEventListener('abort', () => reject(new Error('aborted'))))));
  const pending = GET(new NextRequest(base + 'workflows'), context('workflows'));
  await vi.advanceTimersByTimeAsync(30_001);
  expect((await pending).status).toBe(504);
  expect(backendConfig().plannerTimeout).toBeGreaterThan(180_000);
});

it('preserves all allowed session cookies and rejects unrelated upstream cookies', async () => {
  const headers = new Headers({ 'content-type': 'application/json' });
  headers.append('set-cookie', 'builder_dev_session=one; HttpOnly; Path=/api/backend');
  headers.append('set-cookie', '__Secure-builder_session=two; Secure; HttpOnly; Path=/api/backend');
  headers.append('set-cookie', 'unrelated=three');
  vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response(JSON.stringify(envelope()), { headers })));
  const result = await GET(new NextRequest(base + 'session'), context('session'));
  expect(result.headers.getSetCookie()).toHaveLength(2);
});

it('streams SSE bytes and forwards the reconnect cursor', async () => {
  const fetch = vi.fn().mockResolvedValue(new Response('id: 12\ndata: {"state":"running"}\n\n', { headers: { 'content-type': 'text/event-stream' } }));
  vi.stubGlobal('fetch', fetch);
  const result = await GET(new NextRequest(base + 'workflow-overview/events', { headers: { accept: 'text/event-stream', 'last-event-id': '11' } }), context('workflow-overview/events'));
  expect(result.headers.get('content-type')).toBe('text/event-stream');
  expect(result.headers.get('x-accel-buffering')).toBe('no');
  expect(await result.text()).toContain('id: 12');
  expect(new Headers((fetch.mock.calls[0]![1] as RequestInit).headers).get('last-event-id')).toBe('11');
});

it('forwards signed Slack webhook bytes unchanged and preserves verification challenges', async () => {
  const fetch = vi.fn().mockResolvedValue(new Response(JSON.stringify({ challenge: 'verified-challenge' })));
  vi.stubGlobal('fetch', fetch);
  const raw = '{ "type": "url_verification" }';
  const result = await POST(new NextRequest(base + 'webhooks/slack_events/binding', { method: 'POST', headers: { 'x-slack-signature': 'v0=signed', 'x-slack-request-timestamp': '123', 'content-type': 'application/json' }, body: raw }), context('webhooks/slack_events/binding'));
  expect(await result.json()).toEqual({ challenge: 'verified-challenge' });
  const options = fetch.mock.calls[0]![1] as RequestInit;
  expect(new TextDecoder().decode(options.body as Uint8Array)).toBe(raw);
  expect(new Headers(options.headers).get('x-slack-signature')).toBe('v0=signed');
});
