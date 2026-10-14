import { test, expect } from "@playwright/test";
import fs from "node:fs";
import path from "node:path";

// Actual GraphRunner + bounded CrewAI events, generated with offline model transport.
const evidence = JSON.parse(fs.readFileSync(path.resolve(import.meta.dirname, "fixtures/dynamic-delegation.json"), "utf8"));
for (const mobile of [false, true]) {
  test(`runtime-spawned agents show task and result evidence on ${mobile ? "mobile" : "desktop"}`, async ({ page }) => {
    if (mobile) await page.setViewportSize({ width: 390, height: 844 });
    const errors: string[] = [];
    page.on("pageerror", (error) => errors.push(error.message));
    const { workflow, run, events } = evidence;
    const spawn = events.find((event: { event_type: string }) => event.event_type === "agent.spawned");
    let phase = 0;
    await page.route("**/api/backend/**", async (route) => {
      const destination = new URL(route.request().url()).pathname.replace("/api/backend/", "");
      const collection = { items: [], total: 0, has_more: false, next_cursor: null };
      let data: unknown = collection;
      if (destination === "session") data = { mode: "local-development", planning_available: false, runtime_available: true, approval_service_available: true, auth: { subject: { subject_id: "operator", workspace_id: "local-workspace" }, roles: ["admin"], permissions: ["workflow.view", "runs.view"], scopes: ["workspace:read"], decision: "allow" } };
      else if (destination.startsWith("workflow-overview")) data = { items: [], next_sequence: 0, has_more: false };
      else if (destination === "workflows") data = { ...collection, items: [workflow], total: 1 };
      else if (destination.startsWith("workflows/")) data = { workflow };
      else if (destination === "runs") data = { ...collection, items: [{ ...run, status: phase < 2 ? "running" : "completed" }], total: 1 };
      else if (destination.endsWith("/events")) {
        const resultIndex = events.findIndex((event: { event_type: string; details?: { transfer_kind?: string } }) => event.event_type === "node.handoff" && event.details?.transfer_kind === "delegated_result");
        const visible = phase === 2 ? events : phase === 1 ? events.slice(0, resultIndex - 1) : events.slice(0, events.indexOf(spawn));
        data = { ...collection, items: visible, total: visible.length };
      }
      else if (destination.startsWith("runs/")) data = { run: { ...run, status: phase < 2 ? "running" : "completed" } };
      await route.fulfill({ json: { request_id: "req_dynamic_browser", status: 200, data } });
    });
    await page.goto(`/app/workflows/${workflow.workflow_id}`);
    await expect(page.getByLabel("Select workflow run")).toHaveValue(run.run_id);
    await page.getByRole("button", { name: "Agent communication", exact: true }).click();
    const dialog = page.getByRole("dialog", { name: "Agent communication", exact: true });
    await expect(dialog.getByText(/^Spawned · Task/)).toHaveCount(0);
    phase = 1;
    await expect(dialog.getByText(/^Spawned · Task/)).toHaveCount(1);
    await expect(dialog.getByRole("button", { name: "Task assigned · Live", exact: true })).toBeVisible();
    expect(await dialog.locator(".react-flow__edge.animated").count()).toBeGreaterThan(0);
    await dialog.locator(`.react-flow__node[data-id="${run.run_id}:${spawn.details.node_id}"]`).click();
    const inspector = dialog.getByLabel("Agent details");
    await expect(inspector.getByRole("heading", { name: "Classifier", exact: true })).toBeVisible();
    await expect(inspector.getByText(/Information received/)).toBeVisible();
    phase = 2;
    await expect(inspector.getByText("Helper agent · Completed", { exact: true })).toBeVisible({ timeout: 10000 });
    await expect(inspector.getByText(/research the issue/).first()).toBeVisible();
    await inspector.getByRole("button", { name: "Close details" }).click();
    await expect(dialog.locator(".react-flow__edge.animated")).toHaveCount(0);
    await dialog.getByRole("button", { name: "Result returned", exact: true }).click();
    await expect(inspector.getByText(/The helper sent its recorded result back/)).toBeVisible();
    expect(errors).toEqual([]);
  });
}
