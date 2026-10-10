import { afterEach, expect, it, vi } from "vitest";
import { cleanup, render, screen } from "@testing-library/react";
import { LiveRuntimePanel } from "./app.monitoring";

afterEach(() => { cleanup(); vi.unstubAllGlobals(); });

it("shows pre-run source failures and server guardrails in the shared live panel", async () => {
  vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response(JSON.stringify({ data: {
    runs: { total: 0, active: 0, completed: 0, failed: 0 }, events: 0,
    usage: { llm_calls: 0, tool_calls: 0, tokens: 0, retries: 0, estimated_cost_usd: 0 }, latest: [],
    sources: [{ binding_id: "bind_test", workflow_id: "wf_test", provider_id: "google_sheets", health: "error", error_code: "EVENT_MAPPING_FAILED", baseline_ready: true }],
    policies: [{ workflow_id: "wf_test", version: 1, action_approval_required: false, agents: [{ agent_id: "analysis", guardrails: { injection_detection: true }, limits: { max_llm_calls: 1, max_tool_calls: 0, max_retries: 0 } }] }],
    audit: [{ event_id: "evt_test", event_type: "run.completed", run_id: "run_test", timestamp: "2026-10-10" }],
  } }))));
  render(<LiveRuntimePanel />);
  expect(await screen.findByText(/EVENT_MAPPING_FAILED: polling failed/)).toBeInTheDocument();
  expect(screen.getByText(/Baseline established/)).toBeInTheDocument();
  expect(screen.getByText(/injection_detection: on/)).toBeInTheDocument();
  expect(screen.getByText(/run.completed/)).toBeInTheDocument();
});
