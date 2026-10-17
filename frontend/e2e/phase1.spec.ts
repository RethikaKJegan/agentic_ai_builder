import { test, expect } from '@playwright/test';

for (const mobile of [false, true]) {
  test(`real local proxy session and durable planning on ${mobile ? 'mobile' : 'desktop'}`, async ({ page }) => {
    if (mobile) await page.setViewportSize({ width: 390, height: 844 });
    const errors: string[] = [];
    const privateBrowserCalls: string[] = [];
    page.on('pageerror', (error) => errors.push(error.message));
    page.on('request', (request) => { if (new URL(request.url()).port === '8011' || new URL(request.url()).port === '8000') privateBrowserCalls.push(request.url()); });
    await page.goto('/app');
    await expect(page.getByLabel('Process description')).toBeVisible();
    const session = await page.evaluate(async () => (await fetch('/api/backend/session')).json());
    expect(session.data.mode).toBe('local-development');
    expect(session.data.planning_jobs_available).toBe(true);
    const submitted = await page.evaluate(async () => {
      const response = await fetch('/api/backend/planning-jobs', { method: 'POST', headers: { 'content-type': 'application/json' },
        body: JSON.stringify({ request_id: 'req_browser_phase1', operation: 'plan_workflow', idempotency_key: crypto.randomUUID(), payload: { objective: 'Summarize synthetic notes' } }) });
      return { status: response.status, body: await response.json() };
    });
    expect(submitted.status).toBe(202);
    const jobId = submitted.body.data.job_id;
    await expect.poll(async () => page.evaluate(async (job) => (await (await fetch('/api/backend/planning-jobs/' + job)).json()).data.state, jobId), { timeout: 15000 }).toBe('succeeded');
    const rejected = await page.request.get('/api/backend/session', { headers: { Origin: 'https://evil.example' } });
    expect(rejected.status()).toBe(403);
    expect((await rejected.json()).data.error.error_code).toBe('ORIGIN_NOT_AUTHORIZED');
    expect(privateBrowserCalls).toEqual([]);
    expect(errors).toEqual([]);
  });
}

for (const mobile of [false, true]) {
  test(`planning progress and cancellation preserve the prompt on ${mobile ? 'mobile' : 'desktop'}`, async ({ page }) => {
    if (mobile) await page.setViewportSize({ width: 390, height: 844 });
    let cancelled = false;
    await page.route('**/api/backend/planning-jobs**', async (route) => {
      if (route.request().method() === 'DELETE') cancelled = true;
      const status = route.request().method() === 'POST' ? 202 : 200;
      await route.fulfill({ status, json: { request_id: 'req_cancel_ui', status,
        data: { job_id: 'plan_cancel_ui', state: cancelled ? 'cancelled' : 'running', result: null } } });
    });
    await page.goto('/app');
    const prompt = 'Summarize synthetic notes without external actions';
    await page.getByLabel('Process description').fill(prompt);
    await page.getByRole('button', { name: 'Generate workflow' }).click();
    await expect(page.getByRole('status').filter({ hasText: 'plan_cancel_ui' })).toBeVisible();
    await page.getByRole('button', { name: 'Cancel generation' }).click();
    await expect(page.getByRole('main').getByRole('alert')).toContainText('PLANNING_CANCELLED');
    await expect(page.getByLabel('Process description')).toHaveValue(prompt);
    await expect(page.getByRole('button', { name: 'Retry generation' })).toBeEnabled();
  });
}
