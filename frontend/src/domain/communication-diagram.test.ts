import { expect, it } from "vitest";
import { fromCanonical } from "@/api/mapping";
import type { CanonicalWorkflow, RunEvent } from "@/api/contracts.generated";
import fixture from "../../e2e/fixtures/multitask-delegation.json";
import { workflowDiagram } from "./communication-diagram";

const workflow = fromCanonical(fixture.workflow as CanonicalWorkflow).workflow;
const events = fixture.runs[0]!.events as RunEvent[];
const runId = fixture.runs[0]!.run.run_id;

it("keeps repeated spawned helpers and their task inputs/results separate", () => {
  const model = workflowDiagram(workflow, events, runId, "completed");
  const helpers = model.cards.filter((c) => c.spawned);
  expect(helpers).toHaveLength(3);
  expect(new Set(helpers.map((c) => c.id)).size).toBe(3);
  expect(helpers[0]?.parent).toBe("Master coordinator");
  expect(helpers[0]?.reason).toBe("Ticket A must be classified independently.");
  expect(helpers[0]?.input).toMatchObject({ task: expect.stringContaining("ticket A") });
  expect(helpers[1]?.input).toMatchObject({ task: expect.stringContaining("ticket B") });
  expect(helpers.every((c) => c.status === "Completed" && c.output !== undefined)).toBe(true);
  expect(model.connections.filter((c) => c.label === "Task assigned")).toHaveLength(3);
  expect(model.connections.filter((c) => c.label === "Result returned")).toHaveLength(3);
  expect(model.connections.every((c) => !c.active)).toBe(true);
});

it("never claims configured or mismatched-run helpers were spawned", () => {
  const preview = workflowDiagram(workflow, events);
  expect(preview.cards.every((c) => !c.spawned && c.status === "Planned")).toBe(true);
  expect(preview.connections.every((c) => !c.recorded && !c.active)).toBe(true);
  const mismatched = events.map((e) => ({ ...e, workflow_version: e.workflow_version + 1 }));
  expect(workflowDiagram(workflow, mismatched, runId).cards.filter((c) => c.spawned)).toEqual([]);
  expect(
    workflowDiagram(workflow, events, "another-run").connections.every((c) => !c.recorded),
  ).toBe(true);
});

it("animates recorded in-progress work and stops at completion, failure or approval", () => {
  const task = events.find((e) => e.details?.["transfer_kind"] === "delegated_task")!;
  const partial = events.slice(0, events.indexOf(task) + 1);
  const active = workflowDiagram(workflow, partial, runId, "running");
  expect(active.connections.find((c) => c.label === "Task assigned")?.active).toBe(true);
  const pending = {
    ...task,
    event_id: "pending",
    event_type: "approval.pending" as const,
    details: { node_id: task.details?.["target_node_id"] },
  };
  const paused = workflowDiagram(workflow, [...partial, pending], runId, "paused");
  expect(paused.cards.find((c) => c.nodeId === task.details?.["target_node_id"])?.status).toBe(
    "Waiting for approval",
  );
  expect(paused.connections.every((c) => !c.active)).toBe(true);
  const failed = {
    ...pending,
    event_id: "failed",
    event_type: "node.failed" as const,
    details: { ...pending.details, error_code: "BUDGET_EXHAUSTED" },
  };
  const stopped = workflowDiagram(workflow, [...partial, failed], runId, "failed");
  expect(stopped.cards.find((c) => c.nodeId === task.details?.["target_node_id"])?.problem).toBe(
    "BUDGET_EXHAUSTED",
  );
  expect(stopped.connections.every((c) => !c.active)).toBe(true);
});
