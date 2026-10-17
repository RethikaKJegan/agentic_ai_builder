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
    await page.getByRole("tab", { name: "Execution", exact: true }).click();
    await expect(page.getByLabel("Select workflow run")).toHaveValue(run.run_id);
    await page.getByRole("button", { name: "Agent communication", exact: true }).click();
    const dialog = page.getByRole("dialog", { name: "Agent communication", exact: true });
    await expect(dialog.getByRole("button", { name: "Step-by-step" })).toHaveCount(0);
    await expect(dialog.getByText(/^Spawned · Task/)).toHaveCount(3);
    await expect(dialog.getByRole("button", { name: "Task assigned", exact: true })).toHaveCount(3);
    await expect(dialog.getByRole("button", { name: "Result returned", exact: true })).toHaveCount(3);
    await expect(dialog.locator(".react-flow__edge.animated")).toHaveCount(0);
    const inspector = dialog.getByLabel("Agent details");
    for (const event of spawned) {
      const details = event.details!;
      await dialog.locator(`.react-flow__node[data-id="${run.run_id}:${details["node_id"]}"]`).click();
      await expect(inspector.getByText(/This helper was started for a separate task/)).toBeVisible();
      await expect(inspector.getByText("Information received", { exact: true })).toBeVisible();
      await expect(inspector.getByText("Result", { exact: true })).toBeVisible();
      await expect(inspector.getByText("Technical details", { exact: true }).locator("..")).not.toHaveAttribute("open", "");
      await inspector.getByText("Technical details", { exact: true }).click();
      await expect(inspector.getByText(String(details["invocation_id"]), { exact: true })).toBeVisible();
      await inspector.getByRole("button", { name: "Close details" }).click();
    }
    for (const label of ["Task assigned", "Result returned"]) {
      for (let index = 0; index < 3; index++) {
        await dialog.getByRole("button", { name: label, exact: true }).nth(index).click();
        await expect(inspector.getByText(label === "Task assigned" ? "Information shared" : "Result returned", { exact: true }).last()).toBeVisible();
        await inspector.getByRole("button", { name: "Close details" }).click();
      }
    }
    await page.screenshot({ path: path.resolve(import.meta.dirname, `../../.local/communication-diagram-${mobile ? "mobile" : "desktop"}.png`), fullPage: true });
    expect(errors).toEqual([]);
  });
}
