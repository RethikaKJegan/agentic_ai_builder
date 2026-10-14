import { test, expect } from "@playwright/test";
import fs from "node:fs";
import path from "node:path";

// Actual GraphRunner, CrewAI and Sheets adapter; OAuth, HTTP and model transports are offline.
const evidence = JSON.parse(fs.readFileSync(path.resolve(import.meta.dirname, "fixtures/delegated-tools.json"), "utf8"));
for (const mobile of [false, true]) {
  test(`delegated Sheets read and checked findings are inspectable on ${mobile ? "mobile" : "desktop"}`, async ({ page }) => {
    if (mobile) await page.setViewportSize({ width: 390, height: 844 });
    const errors: string[] = [];
    page.on("pageerror", (error) => errors.push(error.message));
    const { workflow, run, events } = evidence;
    const tool = events.find((event: { event_type: string; details: { kind?: string } }) => event.event_type === "node.observed" && event.details.kind === "tool");
    const child = events.find((event: { event_type: string }) => event.event_type === "agent.spawned");
    await page.route("**/api/backend/**", async (route) => {
      const destination = new URL(route.request().url()).pathname.replace("/api/backend/", "");
      const collection = { items: [], total: 0, has_more: false, next_cursor: null };
      let data: unknown = collection;
      if (destination === "session") data = { mode: "local-development", planning_available: false, runtime_available: true, approval_service_available: true, auth: { subject: { subject_id: "operator", workspace_id: "local-workspace" }, roles: ["admin"], permissions: ["workflow.view", "runs.view"], scopes: ["workspace:read"], decision: "allow" } };
      else if (destination.startsWith("workflow-overview")) data = { items: [], next_sequence: 0, has_more: false };
      else if (destination === "workflows") data = { ...collection, items: [workflow], total: 1 };
      else if (destination.startsWith("workflows/")) data = { workflow };
      else if (destination === "runs") data = { ...collection, items: [run], total: 1 };
      else if (destination.endsWith("/events")) data = { ...collection, items: events, total: events.length };
      else if (destination.startsWith("runs/")) data = { run };
      await route.fulfill({ json: { request_id: "req_delegated_tools", status: 200, data } });
    });
    await page.goto(`/app/workflows/${workflow.workflow_id}`);
    await expect(page.getByLabel("Select workflow run")).toHaveValue(run.run_id);
    await page.getByRole("button", { name: "Agent communication", exact: true }).click();
    const dialog = page.getByRole("dialog", { name: "Agent communication", exact: true });
    await expect(dialog.getByRole("button", { name: "Step-by-step" })).toHaveCount(0);
    await dialog.locator(`.react-flow__node[data-id="${run.run_id}:${tool.details.node_id}"]`).click();
    const inspector = dialog.getByLabel("Agent details");
    await expect(inspector.getByText(/test-sheet/).first()).toBeVisible();
    await expect(inspector.getByText(/pending/).first()).toBeVisible();
    await inspector.getByRole("button", { name: "Close details" }).click();
    await dialog.locator(`.react-flow__node[data-id="${run.run_id}:${child.details.node_id}"]`).click();
    await expect(inspector.getByText(/Claim verified/i).first()).toBeVisible();
    await expect(inspector.getByText(/Actual status/i).first()).toBeVisible();
    await expect(inspector.getByText(/pending/).first()).toBeVisible();
    expect(errors).toEqual([]);
  });
}
