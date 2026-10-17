import { readFileSync } from 'node:fs';
import path from 'node:path';
import { webcrypto } from 'node:crypto';
import { TextEncoder } from 'node:util';
import { afterEach, beforeEach, expect, it, vi } from 'vitest';
import { api, WorkflowClient } from './client';
import { useBackend } from './state';

const workflow = JSON.parse(readFileSync(path.resolve(process.cwd(), '../shared/contracts/examples/workflows/invoice-review.json'), 'utf8'));
const wrap = (data: unknown, status = 200) => ({ request_id: 'req_planning', status, data });
const response = (data: unknown, status = 200) => new Response(JSON.stringify(wrap(data, status)), { status });
const auth = { subject: { subject_id: 'builder', workspace_id: 'local-workspace' }, roles: ['builder'] as const, permissions: ['workflow.plan'], scopes: [], decision: 'allow' as const };
const session = (mode = 'local-development') => ({ mode, auth: { ...auth, roles: [...auth.roles] }, planning_available: true, runtime_available: false, approval_service_available: false, planning_jobs_available: true });
beforeEach(() => { vi.stubGlobal('crypto', webcrypto); vi.stubGlobal('TextEncoder', TextEncoder); localStorage.clear(); });
afterEach(() => { vi.restoreAllMocks(); vi.unstubAllGlobals(); vi.useRealTimers(); });

it('uses a durable job only when advertised and retrieves its confirmed result', async () => {
  vi.useFakeTimers();
  let polls = 0;
  const transport = vi.fn<typeof fetch>(async (url) => {
    if (String(url).endsWith('/session')) return response(session());
    if (String(url).endsWith('/planning-jobs')) return response({ job_id: 'plan_one', state: 'queued', result: null }, 202);
    polls++;
    return response({ job_id: 'plan_one', state: polls === 1 ? 'running' : 'succeeded', result: polls === 1 ? null : wrap({ workflow }) });
  });
  const client = new WorkflowClient(transport);
  await client.session();
  const promise = client.request('plan_workflow', { objective: 'Review invoice approval' });
  await vi.waitFor(() => expect(transport.mock.calls.some(([url]) => String(url).endsWith('/planning-jobs'))).toBe(true));
  await vi.advanceTimersByTimeAsync(3100);
  expect((await promise).workflow.workflow_id).toBe(workflow.workflow_id);
  expect(transport.mock.calls.filter(([url]) => String(url).includes('/planning-jobs/'))).toHaveLength(2);
  expect(transport.mock.calls.some(([url]) => String(url).endsWith('/workflows/plan'))).toBe(false);
});

it('keeps a retry key after an unknown submission outcome', async () => {
  const keys: string[] = [];
  const transport = vi.fn<typeof fetch>(async (url, options) => {
    if (String(url).endsWith('/session')) return response(session());
    keys.push(JSON.parse(String(options?.body)).idempotency_key);
    throw new TypeError('lost connection');
  });
  const client = new WorkflowClient(transport);
  await client.session();
  for (let i = 0; i < 2; i++) await expect(client.request('plan_workflow', { objective: 'Review invoice approval' })).rejects.toMatchObject({ error: { error_code: 'API_UNAVAILABLE' } });
  expect(keys).toHaveLength(2);
  expect(keys[0]).toBe(keys[1]);
});

it('allows a new explicit user retry after a confirmed failed job', async () => {
  const keys: string[] = [];
  const transport = vi.fn<typeof fetch>(async (url, options) => {
    if (String(url).endsWith('/session')) return response(session());
    keys.push(JSON.parse(String(options?.body)).idempotency_key);
    return response({ job_id: 'plan_failed', state: 'failed', result: wrap({ error: { error_code: 'PLANNER_PROVIDER_TIMEOUT', message: 'Generation timed out.', request_id: 'req_planning', retryable: true } }, 504) }, 202);
  });
  const client = new WorkflowClient(transport);
  await client.session();
  for (let i = 0; i < 2; i++) await expect(client.request('plan_workflow', { objective: 'Review invoice approval' })).rejects.toMatchObject({ error: { error_code: 'PLANNER_PROVIDER_TIMEOUT' } });
  expect(keys).toHaveLength(2);
  expect(keys[0]).not.toBe(keys[1]);
});

it('does not renew or replay actions for a known production session', async () => {
  const transport = vi.fn<typeof fetch>(async (url) => String(url).endsWith('/session') ? response(session('google-workspace')) : response({ error: { error_code: 'AUTHENTICATION_REQUIRED', message: 'Sign in again.', request_id: 'req_planning', retryable: false } }, 401));
  const client = new WorkflowClient(transport);
  await client.session();
  await expect(client.request('list_tools', {})).rejects.toMatchObject({ error: { error_code: 'AUTHENTICATION_REQUIRED' } });
  expect(transport).toHaveBeenCalledTimes(2);
});

it('rejects absolute browser API destinations', () => {
  expect(() => new WorkflowClient(fetch, 'http://127.0.0.1:8000/')).toThrow('relative');
});

it('removes stale authority when a session cannot be recovered', async () => {
  const { ApiError } = await import('./client');
  useBackend.setState({ status: 'connected', session: session(), tools: [], reviews: {} });
  vi.spyOn(api, 'overview').mockRejectedValue(new ApiError({ error_code: 'AUTHENTICATION_REQUIRED', message: 'Expired', request_id: 'req_expired', retryable: false }));
  await useBackend.getState().refreshOverview();
  expect(useBackend.getState().session).toBeNull();
  expect(useBackend.getState().can('workflow.plan')).toBe(false);
});

it('restores current session permissions after overview recovery', async () => {
  const { ApiError } = await import('./client');
  useBackend.setState({ status: 'unavailable', session: null, error: new ApiError({ error_code: 'AUTHENTICATION_REQUIRED', message: 'Expired', request_id: 'req_recovery', retryable: false }) });
  vi.spyOn(api, 'overview').mockResolvedValue({ items: [], next_sequence: 1, has_more: false });
  vi.spyOn(api, 'session').mockResolvedValue(session());
  await useBackend.getState().refreshOverview();
  expect(useBackend.getState().status).toBe('connected');
  expect(useBackend.getState().can('workflow.plan')).toBe(true);
  expect(useBackend.getState().error).toBeNull();
});
