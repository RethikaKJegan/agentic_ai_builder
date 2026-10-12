import { test, expect } from "@playwright/test";
import fs from "node:fs";
import path from "node:path";
import type { RunEvent } from "../src/api/contracts.generated";

// Captured from a live model run: two classifier invocations followed by a summarizer.
const evidence = JSON.parse(fs.readFileSync(path.resolve(import.meta.dirname, "fixtures/multitask-delegation.json"), "utf8"));
for (const mobile of [false, true]) {
  test(`three runtime tasks retain all UUIDs and return links on ${mobile ? "mobile" : "desktop"}`, async ({ page }) => {
    if (mobile) await page.setViewportSize({ width: 390, height: 844 });
    const errors: string[] = [];
    page.on("pageerror", (error) => errors.push(error.message));
    page.on("console", (message) => { if (message.type() === "error") errors.push(message.text()); });
    const { workflow } = evidence;
    const { run } = evidence.runs[0];
    const events: RunEvent[] = evidence.runs[0].events;
    const spawned = events.filter((event) => event.event_type === "agent.spawned");
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
      await route.fulfill({ json: { request_id: "req_multitask_browser", status: 200, data } });
    });
    await page.goto(`/app/workflows/${workflow.workflow_id}`);
    await expect(page.getByLabel("Select workflow run")).toHaveValue(run.run_id);
    await page.getByRole("button", { name: "Agent communication", exact: true }).click();
    const dialog = page.getByRole("dialog", { name: "Agent communication", exact: true });
    await expect(dialog.getByLabel("View", { exact: true })).toHaveValue("run");
    await expect(dialog.getByText("Sub-agent", { exact: true })).toHaveCount(3);
    const inspector = dialog.getByLabel("Communication inspector");
    for (const event of spawned) {
      const details = event.details!;
      if (mobile) await dialog.getByLabel("Communication agents").getByRole("button").filter({ hasText: String(details["invocation_id"]) }).click();
      else await dialog.locator(`.react-flow__node[data-id="${details["node_id"]}"]`).click();
      await expect(inspector.getByText(String(details["invocation_id"]), { exact: true })).toBeVisible();
      await expect(inspector.getByText(String(details["agent_id"]), { exact: true })).toBeVisible();
      await expect(inspector.getByText(/^success$/i)).toBeVisible();
      await inspector.getByRole("button", { name: mobile ? "Back to diagram" : "Close details" }).click();
    }
    for (const kind of ["delegated_task", "delegated_result"]) {
      const handoffs = events.filter((event) => event.event_type === "node.handoff" && event.details?.["transfer_kind"] === kind);
      expect(handoffs).toHaveLength(3);
      for (const [index, event] of handoffs.entries()) {
        const label = kind === "delegated_task" ? "Delegated task" : "Returned result";
        if (mobile) await dialog.getByRole("button", { name: new RegExp(`${label} · 1 recorded handoffs`) }).nth(index).click();
        else await dialog.getByText(`${label} handoff · 1`, { exact: true }).nth(index).click();
        await expect(inspector.getByText(new RegExp(String(event.details!["handoff_id"])))).toBeVisible();
        await expect(inspector.getByText(/Receiving step: completed/)).toBeVisible();
        await inspector.getByRole("button", { name: mobile ? "Back to diagram" : "Close details" }).click();
      }
    }
    expect(errors).toEqual([]);
  });
}
