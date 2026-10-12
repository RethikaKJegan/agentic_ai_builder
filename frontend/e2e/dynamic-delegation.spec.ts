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
    let includeSpawn = false;
    await page.route("**/api/backend/**", async (route) => {
      const destination = new URL(route.request().url()).pathname.replace("/api/backend/", "");
      const collection = { items: [], total: 0, has_more: false, next_cursor: null };
      let data: unknown = collection;
      if (destination === "session") data = { mode: "local-development", planning_available: false, runtime_available: true, approval_service_available: true, auth: { subject: { subject_id: "operator", workspace_id: "local-workspace" }, roles: ["admin"], permissions: ["workflow.view", "runs.view"], scopes: ["workspace:read"], decision: "allow" } };
      else if (destination.startsWith("workflow-overview")) data = { items: [], next_sequence: 0, has_more: false };
      else if (destination === "workflows") data = { ...collection, items: [workflow], total: 1 };
      else if (destination.startsWith("workflows/")) data = { workflow };
      else if (destination === "runs") data = { ...collection, items: [run], total: 1 };
      else if (destination.endsWith("/events")) {
        const visible = includeSpawn ? events : events.slice(0, events.indexOf(spawn));
        data = { ...collection, items: visible, total: visible.length };
      }
      else if (destination.startsWith("runs/")) data = { run };
      await route.fulfill({ json: { request_id: "req_dynamic_browser", status: 200, data } });
    });
    await page.goto(`/app/workflows/${workflow.workflow_id}`);
    await expect(page.getByLabel("Select workflow run")).toHaveValue(run.run_id);
    await page.getByRole("button", { name: "Agent communication", exact: true }).click();
    const dialog = page.getByRole("dialog", { name: "Agent communication", exact: true });
    await expect(dialog.getByText("Sub-agent", { exact: true })).toHaveCount(0);
    includeSpawn = true;
    await expect(dialog.getByText("Sub-agent", { exact: true }).first()).toBeVisible();
    if (mobile) await dialog.getByRole("button", { name: /Sub-agent Classifier/ }).click();
    else await dialog.locator(`.react-flow__node[data-id="${spawn.details.node_id}"]`).click();
    const inspector = dialog.getByLabel("Communication inspector");
    await expect(inspector.getByText(spawn.details.invocation_id, { exact: true })).toBeVisible();
    await expect(inspector.getByText("research_agent", { exact: true })).toBeVisible();
    await expect(inspector.getByText(/research the issue/).first()).toBeVisible();
    await inspector.getByRole("button", { name: mobile ? "Back to diagram" : "Close details" }).click();
    if (mobile) await dialog.getByRole("button", { name: /Delegated task · 1 recorded handoffs/ }).click();
    else await dialog.getByText("Delegated task handoff · 1", { exact: true }).click();
    await expect(inspector.getByText("Delegated task", { exact: true }).last()).toBeVisible();
    await expect(inspector.getByText(/This specialist handles the requested task/)).toBeVisible();
    await inspector.getByRole("button", { name: mobile ? "Back to diagram" : "Close details" }).click();
    if (mobile) await dialog.getByRole("button", { name: /Returned result · 1 recorded handoffs/ }).click();
    else await dialog.getByText("Returned result handoff · 1", { exact: true }).click();
    await expect(inspector.getByText("Returned specialist result", { exact: true })).toBeVisible();
    await expect(inspector.getByText(/research the issue/).first()).toBeVisible();
    await page.screenshot({ path: path.resolve(import.meta.dirname, `../../.local/dynamic-delegation-${mobile ? "mobile" : "desktop"}.png`), fullPage: true });
    expect(errors).toEqual([]);
  });
}
