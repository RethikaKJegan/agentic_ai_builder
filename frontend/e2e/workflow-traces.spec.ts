import { test, expect } from "@playwright/test";
import fs from "node:fs";
import path from "node:path";

for (const mobile of [false, true]) {
  test(`node traces and run selection work on ${mobile ? "mobile" : "desktop"}`, async ({ page }) => {
    if (mobile) await page.setViewportSize({ width: 390, height: 844 });
    const workflow = JSON.parse(fs.readFileSync(path.resolve(import.meta.dirname, "../../shared/contracts/examples/workflows/support-triage.json"), "utf8"));
    workflow.metadata.workspace_id = "local-workspace";
    workflow.nodes = [{ node_id: "start", kind: "trigger", label: "New ticket", layout: { x: 80, y: 120 } }, { node_id: "choose", kind: "condition", label: "Open refund ticket?", condition_id: "choice", layout: { x: 400, y: 120 } }, { node_id: "finish", kind: "output", label: "Finished", layout: { x: 720, y: 120 } }];
    workflow.conditions = [{ condition_id: "choice", expression: "input.request_text == 'refund'", outcomes: ["yes", "no"] }];
    workflow.edges = [{ edge_id: "a", source: "start", target: "choose" }, { edge_id: "b", source: "choose", target: "finish", outcome: "yes" }, { edge_id: "c", source: "choose", target: "finish", outcome: "no" }];
    const runs = ["latest", "older"].map((name) => ({ run_id: `run_${name}`, workflow_id: workflow.workflow_id, workflow_version: 1, status: "completed", approvals: [] }));
    const timeline = (id: string) => [{ event_type: "node.observed", details: { node_id: "choose", kind: "condition", observation: { ticket_id: id === "run_latest" ? "T002" : "T001" } } }, { event_type: "node.completed", details: { node_id: "choose", expression: "input.request_text == 'refund'", evaluated_value: id === "run_latest", outcome: id === "run_latest" ? "yes" : "no", explanation: "The recorded expression produced the declared outcome.", selected_edges: [id === "run_latest" ? "b" : "c"], next_nodes: ["finish"] } }].map((event, index) => ({ ...event, event_id: `${id}_${index}`, run_id: id, workflow_id: workflow.workflow_id, workflow_version: 1, timestamp: "2026-10-11T09:00:00Z", source: "runtime" }));
    await page.route("**/api/backend/**", async (route) => {
      const destination = new URL(route.request().url()).pathname.replace("/api/backend/", "");
      const collection = { items: [], total: 0, has_more: false, next_cursor: null };
      let data: unknown = collection;
      if (destination === "session") data = { mode: "local-development", planning_available: false, runtime_available: true, approval_service_available: true, auth: { subject: { subject_id: "operator", workspace_id: "local-workspace" }, roles: ["admin"], permissions: ["workflow.view", "runs.view"], scopes: ["workspace:read"], decision: "allow" } };
      else if (destination.startsWith("workflow-overview")) data = { items: [], next_sequence: 0, has_more: false };
      else if (destination === "workflows") data = { ...collection, items: [workflow], total: 1 };
      else if (destination.startsWith("workflows/")) data = { workflow };
      else if (destination === "runs") data = { ...collection, items: runs, total: runs.length };
      else if (destination.endsWith("/events")) { const id = destination.split("/")[1]!; data = { ...collection, items: timeline(id), total: 2 }; }
      else if (destination.startsWith("runs/")) data = { run: runs.find((run) => destination === `runs/${run.run_id}`) };
      await route.fulfill({ json: { request_id: "req_trace_test", status: 200, data } });
    });
    await page.goto(`/app/workflows/${workflow.workflow_id}`);
    await expect(page.getByLabel("Select workflow run")).toHaveValue("run_latest");
    if (mobile) await page.getByRole("button", { name: /Open refund ticket/ }).click();
    else await page.locator('.react-flow__node[data-id="choose"]').click();
    await expect(page.getByLabel("Node execution trace").getByText(/T002/).first()).toBeVisible();
    await expect(page.getByLabel("Node execution trace").getByText("yes", { exact: true })).toBeVisible();
    await page.getByRole("tab", { name: "Configuration", exact: true }).click();
    await expect(page.getByLabel("Condition expression")).toBeVisible();
    await page.getByRole("tab", { name: "Trace", exact: true }).click();
    await page.getByRole("button", { name: "Close inspector" }).click();
    await page.getByLabel("Select workflow run").selectOption("run_older");
    if (mobile) await page.getByRole("button", { name: /Open refund ticket/ }).click();
    else await page.locator('.react-flow__node[data-id="choose"]').click();
    await expect(page.getByLabel("Node execution trace").getByText(/T001/).first()).toBeVisible();
    await expect(page.getByLabel("Node execution trace").getByText("no", { exact: true })).toBeVisible();
    await expect(page.getByLabel("Node execution trace").getByText(/T002/)).toHaveCount(0);
  });
}
