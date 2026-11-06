import { createHmac, scryptSync, webcrypto } from 'node:crypto';
import { NextRequest } from 'next/server';
import { afterEach, beforeEach, expect, it, vi } from 'vitest';
import { authenticateWorkspace, createClientSession, workspaceAccount, WORKSPACE_COOKIE } from './workspace-auth';
import { POST as login } from '@/app/api/workspace-auth/login/route';
import { GET } from '@/app/api/backend/[...path]/route';

const origin = 'http://127.0.0.1:3100';
const email = 'simpsons-user@example.test';
const secret = 'simpsons-private-proxy-key-with-over-32-characters';
const hash = (password: string) => `${'a'.repeat(32)}:${scryptSync(password, 'a'.repeat(32), 64).toString('hex')}`;
const context = { params: Promise.resolve({ path: ['session'] }) };
beforeEach(() => {
  vi.stubGlobal('crypto', webcrypto);
  vi.stubEnv('BUILDER_LOGIN_SECRET', 'website-cookie-key-with-over-32-characters');
  vi.stubEnv('BUILDER_LOGIN_PASSWORD_HASH', hash('operator-password'));
  vi.stubEnv('BUILDER_SIMPSONS_LOGIN_EMAIL', email);
  vi.stubEnv('BUILDER_SIMPSONS_LOGIN_PASSWORD_HASH', hash('client-password'));
  vi.stubEnv('BUILDER_SIMPSONS_PROXY_SECRET', secret);
  vi.stubEnv('BUILDER_SIMPSONS_API_URL', 'http://127.0.0.1:8020');
  vi.stubEnv('BUILDER_API_URL', 'http://127.0.0.1:8000');
  vi.stubEnv('BUILDER_ENVIRONMENT', 'test');
  vi.stubEnv('BUILDER_UI_ORIGINS', origin);
});
afterEach(() => { vi.unstubAllEnvs(); vi.unstubAllGlobals(); vi.restoreAllMocks(); });
const request = (cookie = createClientSession('simpsons')) => new NextRequest(origin + '/api/backend/session', {
  headers: { host: '127.0.0.1:3100', cookie: `${WORKSPACE_COOKIE}=${cookie}; builder_dev_session=old-shared-session`,
    'x-builder-client-assertion': 'browser-forgery', 'x-workspace-id': 'foreign-company' },
});
const upstream = (client = 'simpsons') => new Response(JSON.stringify({ request_id: 'req_simpsons', status: 200, data: {
  auth: { subject: { workspace_id: 'client-simpsons', subject_id: 'simpsons-client' } },
} }), { headers: { 'content-type': 'application/json', 'x-builder-client': client } });

it('maps credentials to a signed Simpsons account and rejects password/account substitution', async () => {
  expect(await authenticateWorkspace(email, 'client-password')).toBe('simpsons');
  expect(await authenticateWorkspace(email, 'operator-password')).toBeNull();
  expect(await authenticateWorkspace('engineering@bellcorpstudio.com', 'client-password')).toBeNull();
  const token = createClientSession('simpsons');
  expect(workspaceAccount(token)).toBe('simpsons');
  expect(workspaceAccount(token.replace('simpsons', 'operator'))).toBeNull();
  expect(workspaceAccount(token, Date.now() + 8 * 60 * 60 * 1000)).toBeNull();
});

it('logs Simpsons in through the existing login form endpoint', async () => {
  const response = await login(new NextRequest(origin + '/api/workspace-auth/login', { method: 'POST',
    headers: { origin, host: '127.0.0.1:3100', 'content-type': 'application/json' }, body: JSON.stringify({ email, password: 'client-password' }),
  }));
  expect(response.status).toBe(200);
  expect(workspaceAccount(response.cookies.get(WORKSPACE_COOKIE)?.value)).toBe('simpsons');
});

it('routes to Simpsons only, signs server authority and strips shared/backend/browser authority', async () => {
  const fetch = vi.fn().mockResolvedValue(upstream()); vi.stubGlobal('fetch', fetch);
  expect((await GET(request(), context)).status).toBe(200);
  expect(String(fetch.mock.calls[0]![0])).toBe('http://127.0.0.1:8020/session');
  const headers = new Headers(fetch.mock.calls[0]![1].headers);
  expect(headers.get('cookie')).toBeNull();
  expect(headers.get('x-workspace-id')).toBeNull();
  const assertion = headers.get('x-builder-client-assertion')!;
  const parts = assertion.split('.');
  expect(parts[0]).toBe('simpsons');
  expect(Number(parts[1]) - Math.floor(Date.now() / 1000)).toBeLessThanOrEqual(60);
  expect(parts[3]).toBe(createHmac('sha256', secret).update(parts.slice(0, 3).join('.')).digest('hex'));
});

it('never bootstraps the shared backend when the client config is missing or points at the shared instance', async () => {
  const fetch = vi.fn(); vi.stubGlobal('fetch', fetch);
  for (const url of ['', 'http://127.0.0.1:8000']) {
    vi.stubEnv('BUILDER_SIMPSONS_API_URL', url);
    expect((await GET(request(), context)).status).toBe(503);
  }
  expect(fetch).not.toHaveBeenCalled();
});

it('rejects anonymous and tampered cookies inside the route handler', async () => {
  const fetch = vi.fn(); vi.stubGlobal('fetch', fetch);
  expect((await GET(request(''), context)).status).toBe(401);
  expect((await GET(request(createClientSession('simpsons') + 'tampered'), context)).status).toBe(401);
  expect(fetch).not.toHaveBeenCalled();
});

it('rejects an upstream that is not the Simpsons backend without falling back', async () => {
  const fetch = vi.fn().mockResolvedValue(upstream('operator')); vi.stubGlobal('fetch', fetch);
  const response = await GET(request(), context);
  expect(response.status).toBe(503);
  expect((await response.json()).data.error.error_code).toBe('CLIENT_BACKEND_MISMATCH');
  expect(fetch).toHaveBeenCalledTimes(1);
});
