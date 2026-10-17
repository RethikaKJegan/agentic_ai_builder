import { render, screen, cleanup } from "@testing-library/react";
import { afterEach, expect, test } from "vitest";
import { NodeTrace } from "./NodeTrace";
import type { WorkflowTrace } from "./useWorkflowTrace";
afterEach(cleanup);
const node = { id: "choose", type: "mesh" as const, position: { x: 0, y: 0 }, data: { kind: "condition" as const, label: "Choose" } };
const run = { run_id: "run_one", workflow_id: "workflow", workflow_version: 1, status: "completed" as const, approvals: [] };
const trace = { available: true,hasMoreRuns:false,loadMoreRuns:()=>{},hasMoreEvents:false,loadMoreEvents:()=>{}, runs: [run], runId: run.run_id, run, events: [], runState: {}, activeEdges: new Set<string>(), error: null, loading: false, revision: null, retry: () => {}, selectRun: () => {} } satisfies WorkflowTrace;
test("historical missing evidence is explicit and unrelated nodes are excluded", () => {
  render(<NodeTrace node={node} trace={{ ...trace, events: [{ event_id: "evt", run_id: run.run_id, workflow_id: "workflow", workflow_version: 1, timestamp: "2026-10-11T09:00:00Z", source: "runtime", event_type: "node.completed", details: { node_id: "other", output: "unrelated private data" } }] }} />);
  expect(screen.getAllByText("Not captured for this run.").length).toBeGreaterThan(0);
  expect(screen.queryByText(/unrelated private data/)).toBeNull();
});
test("branch evidence shows actual observation, rule and outcome", () => {
  const events = [
    { event_type: "node.observed", details: { node_id: "choose", observation: { ticket: "T002" } } },
    { event_type: "node.completed", details: { node_id: "choose", expression: "input.status == 'open'", evaluated_value: true, outcome: "yes", explanation: "Both required conditions matched.", next_nodes: ["analyze"] } },
  ].map((event, i) => ({ ...event, event_id: `evt_${i}`, run_id: run.run_id, workflow_id: "workflow", workflow_version: 1, timestamp: "2026-10-11T09:00:00Z", source: "runtime" }));
  render(<NodeTrace node={node} trace={{ ...trace, events, runState: { choose: "success" } }} />);
  expect(screen.getAllByText(/T002/)[0]).toBeInTheDocument();
  expect(screen.getByText("yes")).toBeInTheDocument();
  expect(screen.getAllByText(/input.status/)[0]).toBeInTheDocument();
  expect(screen.getAllByText("Both required conditions matched.")[0]).toBeInTheDocument();
});
