import { webcrypto } from "node:crypto";
import { TextEncoder } from "node:util";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { api, ApiError, WorkflowClient } from "./client";
import { useBackend } from "./state";

const envelope = (data: unknown, status = 200) => new Response(JSON.stringify({ request_id: "req_session", status, data }), { status });
const rejected = (status = 401) => envelope({ error: { error_code: status === 401 ? "AUTHENTICATION_REQUIRED" : "OPERATION_NOT_AUTHORIZED", message: "Session unavailable.", request_id: "req_session", retryable: false } }, status);
const session = (mode = "local-development") => envelope({ mode, planning_available: true, runtime_available: true, approval_service_available: true,
  auth: { subject: { subject_id: "operator", workspace_id: "local-workspace" }, roles: ["admin"], permissions: ["workflow.view"], scopes: [], decision: "allow" } });
const collection = () => envelope({ items: [], total: 0, has_more: false, next_cursor: null });

beforeEach(() => { vi.stubGlobal("crypto", webcrypto); vi.stubGlobal("TextEncoder", TextEncoder); });
afterEach(() => { vi.restoreAllMocks(); vi.unstubAllGlobals(); });

it("renews an expired local session and preserves the rejected mutation exactly", async () => {
  let renewed = false;
  const bodies: string[] = [];
  const transport = vi.fn<typeof fetch>(async (url, options) => {
    if (String(url).endsWith("/session")) { renewed = true; return session(); }
    bodies.push(String(options?.body));
    return renewed ? envelope({ run: { run_id: "run_session", workflow_id: "workflow_session", workflow_version: 1, status: "queued", approvals: [] } }) : rejected();
  });
  const result = await new WorkflowClient(transport).request("execute_workflow", { workflow_id: "workflow_session", workflow_version: 1, inputs: {} }, "stable_retry_session");
  expect(result.run.status).toBe("queued");
  expect(transport).toHaveBeenCalledTimes(3);
  expect(bodies).toHaveLength(2);
  expect(bodies[1]).toBe(bodies[0]);
  expect(JSON.parse(bodies[1]!).idempotency_key).toBe("stable_retry_session");
});

it("shares renewal with concurrent requests, including a delayed stale response", async () => {
  let renewed = false;
  let release!: (response: Response) => void;
  const delayed = new Promise<Response>((resolve) => { release = resolve; });
  const transport = vi.fn<typeof fetch>(async (url) => {
    if (String(url).endsWith("/session")) { renewed = true; return session(); }
    if (renewed) return collection();
    return String(url).includes("/workflows?") ? delayed : rejected();
  });
  const client = new WorkflowClient(transport);
  const first = client.request("list_tools", {});
  const second = client.request("list_workflows", {});
  await first;
  release(rejected());
  await second;
  expect(transport.mock.calls.filter(([url]) => String(url).endsWith("/session"))).toHaveLength(1);
  expect(transport).toHaveBeenCalledTimes(5);
});

it("stops after one retry when authentication is still rejected", async () => {
  const transport = vi.fn<typeof fetch>(async (url) => String(url).endsWith("/session") ? session() : rejected());
  await expect(new WorkflowClient(transport).request("list_tools", {})).rejects.toMatchObject({ error: { error_code: "AUTHENTICATION_REQUIRED" } });
  expect(transport).toHaveBeenCalledTimes(3);
});

it("shares a session renewal that is still in flight", async () => {
  let renewed = false;
  let release!: (response: Response) => void;
  const pending = new Promise<Response>((resolve) => { release = resolve; });
  const transport = vi.fn<typeof fetch>(async (url) => String(url).endsWith("/session") ? pending : renewed ? collection() : rejected());
  const client = new WorkflowClient(transport);
  const requests = [client.request("list_tools", {}), client.request("list_workflows", {})];
  await vi.waitFor(() => expect(transport).toHaveBeenCalledTimes(3));
  renewed = true;
  release(session());
  await Promise.all(requests);
  expect(transport.mock.calls.filter(([url]) => String(url).endsWith("/session"))).toHaveLength(1);
});

it("does not recursively renew a rejected session endpoint", async () => {
  const transport = vi.fn<typeof fetch>(async () => rejected());
  await expect(new WorkflowClient(transport).request("list_tools", {})).rejects.toMatchObject({ error: { error_code: "AUTHENTICATION_REQUIRED" } });
  expect(transport).toHaveBeenCalledTimes(2);
});

it("does not retry authorization denials or non-local sessions", async () => {
  const denied = vi.fn<typeof fetch>(async () => rejected(403));
  await expect(new WorkflowClient(denied).request("list_tools", {})).rejects.toMatchObject({ error: { error_code: "OPERATION_NOT_AUTHORIZED" } });
  expect(denied).toHaveBeenCalledTimes(1);
  const remote = vi.fn<typeof fetch>(async (url) => String(url).endsWith("/session") ? session("authenticated") : rejected());
  await expect(new WorkflowClient(remote).request("list_tools", {})).rejects.toMatchObject({ error: { error_code: "AUTHENTICATION_REQUIRED" } });
  expect(remote).toHaveBeenCalledTimes(2);
});

it("clears the old authentication banner after overview recovery and preserves other errors", async () => {
  vi.spyOn(api, "overview").mockResolvedValue({ items: [], next_sequence: 5, has_more: false });
  const error = new ApiError({ error_code: "AUTHENTICATION_REQUIRED", message: "Expired session", request_id: "req_session", retryable: false });
  useBackend.setState({ error, liveStatus: "stale" });
  await useBackend.getState().refreshOverview();
  expect(useBackend.getState().error).toBeNull();
  expect(useBackend.getState().liveStatus).toBe("live");
  const unrelated = new ApiError({ ...error.error, error_code: "PROVIDER_FAILED" });
  useBackend.setState({ error: unrelated });
  await useBackend.getState().refreshOverview();
  expect(useBackend.getState().error).toBe(unrelated);
});
