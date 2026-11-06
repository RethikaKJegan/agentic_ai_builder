import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { NextRequest } from "next/server";
import { GET } from "@/app/api/backend/[...path]/route";
import { createWorkspaceSession, WORKSPACE_COOKIE } from '@/lib/workspace-auth';

function authorizedRequest(input: string) {
  return new NextRequest(input, { headers: { cookie: `${WORKSPACE_COOKIE}=${createWorkspaceSession()}` } });
}
beforeEach(() => vi.stubEnv('BUILDER_LOGIN_SECRET', 'proxy-tests-use-an-explicit-32-character-key'));

afterEach(() => { vi.unstubAllGlobals(); vi.unstubAllEnvs(); });

it("reports an unrelated upstream service with a canonical API error", async () => {
  vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response(JSON.stringify({ detail: "Not Found" }), {
    status: 404, headers: { "content-type": "application/json" },
  })));
  const response = await GET(authorizedRequest("http://127.0.0.1:3001/api/backend/session"), { params: Promise.resolve({ path: ["session"] }) });
  expect(response.status).toBe(503);
  expect(await response.json()).toMatchObject({ status: 503,
    data: { error: { error_code: "API_WRONG_SERVICE", retryable: true } } });
});

it("preserves the Builder envelope and development session cookie", async () => {
  const body = { request_id: "req_session", status: 200, data: { runtime_available: true } };
  vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response(JSON.stringify(body), {
    status: 200, headers: { "content-type": "application/json", "set-cookie": "builder_dev_session=test-only; Path=/api/backend" },
  })));
  const response = await GET(authorizedRequest("http://127.0.0.1:3001/api/backend/session"), { params: Promise.resolve({ path: ["session"] }) });
  expect(await response.json()).toEqual(body);
  expect(response.headers.get("set-cookie")).toContain("builder_dev_session=test-only");
});

it("distinguishes a missing route on an older Builder backend from an unrelated service", async () => {
  const fetch = vi.fn()
    .mockResolvedValueOnce(new Response(JSON.stringify({ detail: "Not Found" }), { status: 404 }))
    .mockResolvedValueOnce(new Response(JSON.stringify({ request_id: "req_session", status: 200, data: { runtime_available: true } }), { status: 200 }));
  vi.stubGlobal("fetch", fetch);
  const response = await GET(authorizedRequest("http://127.0.0.1:3001/api/backend/procurement/projects/project_test"), { params: Promise.resolve({ path: ["procurement", "projects", "project_test"] }) });
  expect(await response.json()).toMatchObject({ data: { error: { error_code: "API_ROUTE_UNAVAILABLE" } } });
});

it('rejects retired ontology routes without contacting the backend',async()=>{
 const fetch=vi.fn();vi.stubGlobal('fetch',fetch);
 const response=await GET(authorizedRequest('http://127.0.0.1:3001/api/backend/ontology/v1'),{params:Promise.resolve({path:['ontology','v1']})});
 expect(response.status).toBe(410);expect(fetch).not.toHaveBeenCalled();
 const other=await GET(authorizedRequest('http://127.0.0.1:3001/api/backend/runs/other%3Aid'),{params:Promise.resolve({path:['runs','other:id']})});expect(other.status).toBe(400);
});
