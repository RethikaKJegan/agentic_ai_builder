import { test, expect } from "@playwright/test";
import fs from "node:fs";

// Synthetic native database-run evidence; the Google transport was offline.
// These browser tests verify presentation and approval controls, not cloud effects.
const fixture = JSON.parse(fs.readFileSync(new URL("./fixtures/database-workflow.json", import.meta.url), "utf8"));
for (const mobile of [false, true]) {
  for (const stale of [false, true]) {
    test(`database workflow ${stale ? "stale approval blocked" : "plan review and execution"} ${mobile ? "mobile" : "desktop"}`, async ({ page }) => {
      if (mobile) await page.setViewportSize({ width: 390, height: 844 });
      const errors: string[] = [];
      page.on("pageerror", error => errors.push(error.message));
      let decisions = 0;
      let completed = false;
      const { workflow } = fixture;
      const operation = { ...fixture.operation, preview_available: !stale, expires_at: Date.now() / 1000 + 600 };
      await page.route("**/api/backend/**", async route => {
        const destination = new URL(route.request().url()).pathname.replace("/api/backend/", "");
        const collection = { items: [], total: 0, has_more: false, next_cursor: null };
        let data: unknown = collection;
        if (destination === "session") data = { mode: "local-development", planning_available: false, runtime_available: true, approval_service_available: true, auth: { subject: { subject_id: "alice", workspace_id: "one" }, roles: ["admin"], permissions: ["workflow.view", "runs.view", "workflow.approve", "tools.read", "tools.assign"], scopes: ["workspace:read", "workspace:write"], decision: "allow" } };
        else if (destination.startsWith("workflow-overview")) data = { ...collection, next_sequence: 0 };
        else if (destination === "workflows") data = { ...collection, items: [workflow], total: 1 };
        else if (destination.startsWith("workflows/")) data = { workflow };
        else if (destination === "data-sources") data = { configured: true, shared_demo_identity: false, items: [] };
        else if (destination === "data-operations") data = { configured: true, targets: [], items: [operation], tools: [] };
        else if (destination === "runs") data = { ...collection, items: [completed ? fixture.completed_run : fixture.pending_run], total: 1 };
        else if (destination.includes("/events")) {
          const events = completed ? fixture.completed_events : fixture.pending_events;
          data = { ...collection, items: events, total: events.length };
        } else if (destination.startsWith("runs/")) data = { run: completed ? fixture.completed_run : fixture.pending_run };
        else if (destination.startsWith("data-operations/")) data = operation;
        else if (destination.startsWith("approvals/") && destination.endsWith("/decision")) {
          decisions++;
          expect(stale).toBe(false);
          completed = true;
          data = fixture.completed_run.approvals[0];
        }
        await route.fulfill({ json: { request_id: "req_database_workflow_browser", status: 200, data } });
      });
      if (!stale) {
        await page.goto("/app/data-intelligence");
        await page.getByRole("tab", { name: "Operations", exact: true }).click();
        await page.getByRole("region", { name: "Database operation history" }).getByRole("button").click();
        await expect(page.getByRole("button", { name: "Execute reviewed operation", exact: true })).toHaveCount(0);
        await page.getByRole("link", { name: "Open workflow", exact: true }).click();
      } else await page.goto(`/app/workflows/${workflow.workflow_id}`);
      await page.getByRole("button", { name: "Workflow details", exact: true }).click();
      const details = page.getByRole("dialog");
      await expect(details.getByRole("region", { name: "Planned database operations" })).toBeVisible();
      await expect(details.getByText(/These are planned sources/)).toBeVisible();
      await expect(details.getByText(/database_execute_operation/).first()).toBeVisible();
      await details.getByRole("button", { name: "Close", exact: true }).click();
      await page.getByRole("tab", { name: "Execution", exact: true }).click();
      const preview = page.getByRole("region", { name: "Database change awaiting approval" });
      await expect(preview).toBeVisible();
      await expect(page.getByRole("button", { name: "Approve", exact: true })).toBeDisabled();
      if (stale) {
        await expect(preview.getByRole("alert")).toBeVisible();
        await expect(preview.getByRole("checkbox")).toHaveCount(0);
        await expect(page.getByRole("button", { name: "Reject", exact: true })).toBeEnabled();
        expect(decisions).toBe(0);
      } else {
        await expect(preview.getByText(/Workflow updated/)).toBeVisible();
        await preview.getByRole("checkbox").check();
        await page.getByRole("button", { name: "Approve", exact: true }).click();
        await expect(page.getByRole("button", { name: /execute · tool · success/ })).toBeVisible();
        await page.getByRole("button", { name: /execute · tool · success/ }).click();
        const trace = page.getByLabel("Node execution trace");
        await expect(trace.getByText(/affected_records/).first()).toBeVisible();
        expect(decisions).toBe(1);
      }
      expect(errors).toEqual([]);
      expect(await page.evaluate(() => document.documentElement.scrollWidth > innerWidth)).toBe(false);
    });
  }
}
