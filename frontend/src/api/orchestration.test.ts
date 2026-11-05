import { it, expect, vi } from "vitest";
import { webcrypto } from "node:crypto";
import { WorkflowClient, ApiError } from "./client";
import fixture from "@/test/fixtures/orchestration.json";
Object.defineProperty(globalThis, "crypto", { configurable: true, value: webcrypto });
const envelope = (data: unknown, status = 200) =>
  new Response(JSON.stringify({ request_id: "req_orchestration", status, data }), {
    status,
    headers: { "Content-Type": "application/json" },
  });
it("uses the authenticated same-origin transport for exact Phase 1–3 endpoints", async () => {
  const calls: { url: string; init: RequestInit }[] = [];
  const transport = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    const url = String(input);
    calls.push({ url, init: init ?? {} });
    if (url.includes("/action-plans")) return envelope(fixture.document);
    if (url.includes("/automation?"))
      return envelope({
        items: fixture.records,
        has_more: false,
        next_cursor: null,
        jobs: [],
        health: {},
      });
    if (url.includes("/automation/")) return envelope(fixture.records[0]);
    return envelope(fixture.case);
  });
  const client = new WorkflowClient(transport as typeof fetch);
  await client.createActionPlan({ objective: "Goal", request_key: "request_plan_1" });
  await client.actionPlan("composition_owned");
  await client.adaptiveCommand("case_owned", "enable", {
    request_key: "enable_1",
    expected_revision: 12,
  });
  await client.adaptiveCommand("case_owned", "supply", {
    request_key: "input_1",
    expected_revision: 13,
    wait_id: "wait_1",
    inputs: { recipient: "engineer@example.com" },
  });
  await client.automationRecords();
  await client.createAutomation("schedules", { request_key: "schedule_1" });
  await client.controlAutomation("auto_owned", { request_key: "pause_1", action: "pause" });
  expect(calls.map((c) => c.url)).toEqual([
    "/api/backend/business-ontology/v1/action-plans",
    "/api/backend/business-ontology/v1/action-plans/composition_owned",
    "/api/backend/business-ontology/v1/cases/case_owned/adaptive",
    "/api/backend/business-ontology/v1/cases/case_owned/adaptive/supply",
    "/api/backend/business-ontology/v1/automation?limit=50",
    "/api/backend/business-ontology/v1/automation/schedules",
    "/api/backend/business-ontology/v1/automation/auto_owned/control",
  ]);
  expect(
    calls.every((c) => c.init.credentials === "same-origin" && c.init.cache === "no-store"),
  ).toBe(true);
  expect(JSON.parse(String(calls[3]!.init.body))).toMatchObject({
    expected_revision: 13,
    wait_id: "wait_1",
  });
});
it("does not automatically retry stale or unknown mutations", async () => {
  for (const status of [409, 503]) {
    const transport = vi.fn(async () =>
      envelope(
        {
          error: {
            error_code: status === 409 ? "CASE_CONFLICT" : "SERVICE_UNAVAILABLE",
            message: "Refresh saved state",
            request_id: "request_failed",
            retryable: true,
          },
        },
        status,
      ),
    );
    const client = new WorkflowClient(transport as typeof fetch);
    await expect(
      client.adaptiveCommand("case_owned", "supply", { request_key: "stable_key" }),
    ).rejects.toBeInstanceOf(ApiError);
    expect(transport).toHaveBeenCalledOnce();
  }
});
it("rejects malformed plan and automation responses instead of fabricating results", async () => {
  const transport = vi.fn(async () => envelope({ state: "completed" }));
  const client = new WorkflowClient(transport as typeof fetch);
  await expect(client.actionPlan("invalid")).rejects.toThrow();
  await expect(client.automationRecords()).rejects.toThrow();
});

it("unwraps response metadata without weakening the canonical workflow contract", async () => {
  const fixture = await import("@/test/fixtures/connected-workflow-response.json");
  const client = new WorkflowClient(vi.fn(async () => envelope(fixture.default)) as typeof fetch);
  const workflow = await client.compositionWorkflow("composition_owned");
  expect(workflow.version).toBe(1);
  expect(workflow).not.toHaveProperty("correlation_id");
  expect(workflow.metadata["connected_action_plan"]).toBeDefined();
  const bad = new WorkflowClient(
    vi.fn(async () => envelope({ ...fixture.default, unknown_authority: true })) as typeof fetch,
  );
  await expect(bad.compositionWorkflow("composition_owned")).rejects.toThrow();
});
