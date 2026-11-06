import { afterEach, beforeEach, expect, it, vi } from 'vitest';

beforeEach(() => { vi.resetModules(); localStorage.clear(); sessionStorage.clear(); });
afterEach(() => { vi.unstubAllGlobals(); });

it('discards the old tab recovery copy when a different account logs in', async () => {
  localStorage.setItem('mesh-browser-session-v1', 'simpsons-login');
  sessionStorage.setItem('mesh-tab-session-v1', 'operator-login');
  sessionStorage.setItem('mesh-tab-drafts-v1', JSON.stringify({ state: { workflows: [{ name: 'Other company' }] } }));
  const { draftStorage } = await import('@/domain/draft-storage');
  expect(draftStorage.getItem('mesh-local-drafts-v1')).toBeNull();
  expect(sessionStorage.getItem('mesh-tab-drafts-v1')).toBeNull();
});

it('prevents a stale tab from writing company drafts or sending requests under the new cookie', async () => {
  const { browserSessionCurrent, BROWSER_SESSION } = await import('./browser-session');
  const { draftStorage } = await import('@/domain/draft-storage');
  const { WorkflowClient } = await import('@/api/client');
  expect(browserSessionCurrent()).toBe(true);
  localStorage.setItem(BROWSER_SESSION, 'new-simpsons-login');
  draftStorage.setItem('mesh-local-drafts-v1', 'old company');
  expect(localStorage.getItem('mesh-local-drafts-v1')).toBeNull();
  const transport = vi.fn();
  await expect(new WorkflowClient(transport).session()).rejects.toMatchObject({ error: { error_code: 'AUTHENTICATION_REQUIRED' } });
  expect(transport).not.toHaveBeenCalled();
});

it('discards an in-flight response when the browser account changes', async () => {
  const { BROWSER_SESSION } = await import('./browser-session');
  const { WorkflowClient } = await import('@/api/client');
  let finish!: (response: Response) => void;
  const transport = vi.fn(() => new Promise<Response>(resolve => { finish = resolve; }));
  const request = new WorkflowClient(transport).session();
  localStorage.setItem(BROWSER_SESSION, 'new-simpsons-login');
  finish(new Response(JSON.stringify({ company: 'old company' })));
  await expect(request).rejects.toMatchObject({ error: { error_code: 'AUTHENTICATION_REQUIRED' } });
});

it('discards a response when the account changes while its body is being read', async () => {
  const { BROWSER_SESSION } = await import('./browser-session');
  const { WorkflowClient } = await import('@/api/client');
  let finish!: (value: unknown) => void;
  let reading!: () => void;
  const started = new Promise<void>(resolve => { reading = resolve; });
  const response = new Response('{}');
  vi.spyOn(response, 'json').mockImplementation(() => { reading(); return new Promise(resolve => { finish = resolve; }); });
  const request = new WorkflowClient(vi.fn().mockResolvedValue(response)).session();
  await started;
  localStorage.setItem(BROWSER_SESSION, 'new-simpsons-login');
  finish({ old_company_data: true });
  await expect(request).rejects.toMatchObject({ error: { error_code: 'AUTHENTICATION_REQUIRED' } });
});
