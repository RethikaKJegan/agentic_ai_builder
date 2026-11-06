import { createHmac, scryptSync, webcrypto } from 'node:crypto';
import { NextRequest } from 'next/server';
import { afterEach, beforeEach, expect, it, vi } from 'vitest';
import { authenticateWorkspace, createClientSession, workspaceAccount, WORKSPACE_COOKIE } from './workspace-auth';
import { GET } from '@/app/api/backend/[...path]/route';
import { POST as login } from '@/app/api/workspace-auth/login/route';
import { backendConfig } from './backend-config';

const origin = 'http://127.0.0.1:3100';
const hash = (password: string) => `${'b'.repeat(32)}:${scryptSync(password, 'b'.repeat(32), 64).toString('hex')}`;
beforeEach(() => {
  vi.stubGlobal('crypto', webcrypto);
  vi.stubEnv('BUILDER_LOGIN_SECRET', 'shared-website-signing-key-over-32-characters');
  vi.stubEnv('BUILDER_LOGIN_PASSWORD_HASH', hash('operator-test-password'));
  vi.stubEnv('BUILDER_ENVIRONMENT', 'test');
  vi.stubEnv('BUILDER_UI_ORIGINS', origin);
  for (const [client, port] of [['simpsons', '8020'], ['subway', '8021']]) {
    const prefix = 'BUILDER_' + client!.toUpperCase();
    vi.stubEnv(prefix + '_LOGIN_EMAIL', client === 'subway' ? 'subway.admin@example.com' : 'alex.simpsons@example.test');
    vi.stubEnv(prefix + '_LOGIN_PASSWORD_HASH', hash(client === 'subway' ? 'Subway@123' : 'simpsons-test-password'));
    vi.stubEnv(prefix + '_PROXY_SECRET', client + '-independent-secret-over-32-characters');
    vi.stubEnv(prefix + '_API_URL', 'http://127.0.0.1:' + port);
  }
});
afterEach(() => { vi.unstubAllEnvs(); vi.unstubAllGlobals(); vi.restoreAllMocks(); });

it('authenticates independent accounts and rejects cross-account passwords', async () => {
  expect(await authenticateWorkspace('subway.admin@example.com', 'Subway@123')).toBe('subway');
  expect(await authenticateWorkspace('alex.simpsons@example.test', 'simpsons-test-password')).toBe('simpsons');
  expect(await authenticateWorkspace('subway.admin@example.com', 'simpsons-test-password')).toBeNull();
  expect(await authenticateWorkspace('alex.simpsons@example.test', 'Subway@123')).toBeNull();
  expect(workspaceAccount(createClientSession('subway'))).toBe('subway');
  expect(workspaceAccount(createClientSession('simpsons').replace('simpsons', 'subway'))).toBeNull();
});

it('issues the Subway account cookie from the existing public login endpoint', async () => {
  const response = await login(new NextRequest(origin + '/api/workspace-auth/login', {
    method: 'POST', headers: { origin, host: '127.0.0.1:3100', 'content-type': 'application/json' },
    body: JSON.stringify({ email: 'subway.admin@example.com', password: 'Subway@123', tenant: 'simpsons' }),
  }));
  expect(response.status).toBe(200);
  expect(workspaceAccount(response.cookies.get(WORKSPACE_COOKIE)?.value)).toBe('subway');
});

it('selects only Subway upstream and signs only Subway authority', async () => {
  const fetch = vi.fn().mockResolvedValue(new Response(JSON.stringify({ request_id: 'req_subway', status: 200, data: {} }),
    { headers: { 'x-builder-client': 'subway' } }));
  vi.stubGlobal('fetch', fetch);
  const response = await GET(new NextRequest(origin + '/api/backend/session', { headers: {
    host: '127.0.0.1:3100',
    cookie: `${WORKSPACE_COOKIE}=${createClientSession('subway')}; builder_dev_session=old`,
    'x-builder-client-assertion': 'forged-simpsons',
  } }), { params: Promise.resolve({ path: ['session'] }) });
  expect(response.status).toBe(200);
  expect(String(fetch.mock.calls[0]![0])).toBe('http://127.0.0.1:8021/session');
  const headers = new Headers(fetch.mock.calls[0]![1].headers);
  expect(headers.get('cookie')).toBeNull();
  const parts = headers.get('x-builder-client-assertion')!.split('.');
  expect(parts[0]).toBe('subway');
  expect(parts[3]).toBe(createHmac('sha256', process.env['BUILDER_SUBWAY_PROXY_SECRET']!).update(parts.slice(0, 3).join('.')).digest('hex'));
});

it('refuses shared client endpoints and missing Subway configuration', () => {
  vi.stubEnv('BUILDER_SUBWAY_API_URL', 'http://127.0.0.1:8020');
  expect(() => backendConfig('subway')).toThrow();
  expect(() => backendConfig('simpsons')).toThrow();
  vi.stubEnv('BUILDER_SUBWAY_API_URL', '');
  expect(() => backendConfig('subway')).toThrow();
  expect(backendConfig('simpsons').upstream.port).toBe('8020');
});
