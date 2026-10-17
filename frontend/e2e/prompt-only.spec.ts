import { test, expect } from "@playwright/test";
import fs from "node:fs";
import path from "node:path";

for (const mobile of [false, true]) {
  for (const mode of ["setup", "manual", "event"] as const) {
    test(`prompt-only ${mode} on ${mobile ? "mobile" : "desktop"}`, async ({ page }) => {
      if (mobile) await page.setViewportSize({ width: 390, height: 844 });
      const evidence = JSON.parse(fs.readFileSync(path.resolve(import.meta.dirname, "fixtures/delegated-tools.json"), "utf8"));
      const published = evidence.workflow;
      published.status = "published";
      published.inputs = [];
      published.metadata.execution_input_mode = "automatic";
      published.metadata.trigger_templates = mode === "event" ? [{ provider_id: "google_sheets", event_type: "row.created", input_mapping: {} }] : [];
      const draft = structuredClone(published);
      draft.version = 2;
      draft.inputs = [{ name: "request_text", type: "string", required: true }];
      delete draft.metadata.execution_input_mode;
      const calls: { operation: string; payload: Record<string, unknown> }[] = [];
      const dialogs: string[] = [];
      const errors: string[] = [];
      let sessionRequests = 0;
      page.on("dialog", async (dialog) => { dialogs.push(dialog.message()); await dialog.dismiss(); });
      page.on("pageerror", (error) => errors.push(error.message));
      await page.route("**/api/backend/**", async (route) => {
        const url = new URL(route.request().url());
        const destination = url.pathname.replace("/api/backend/", "");
        const collection = { items: [], total: 0, has_more: false, next_cursor: null };
        let data: unknown = collection;
        if (destination === "session") {
          sessionRequests += 1;
          const stale = mode === "setup" && sessionRequests === 1;
          data = { mode: "local-development", planning_available: !stale, runtime_available: true, approval_service_available: true, auth: { subject: { subject_id: "operator", workspace_id: "local-workspace" }, roles: ["admin"], permissions: stale ? ["workflow.view"] : ["workflow.view", "workflow.plan", "workflow.save", "workflow.execute", "runs.view"], scopes: ["workspace:read"], decision: "allow" } };
        }
        else if (destination.startsWith("workflow-overview")) data = { items: mode === "setup" ? [] : [{ workflow_id: published.workflow_id, name: published.name, draft_version: 2, published_version: 1, release_id: "release_test", activation_state: "active", active_run_count: 0, latest_run_id: null, latest_run_status: null, pending_approval_count: 0, updated_at: "2026-10-11T12:00:00Z" }], next_sequence: 0, has_more: false };
        else if (destination === "workflows") data = { ...collection, items: mode === "setup" ? [] : [draft], total: mode === "setup" ? 0 : 1 };
        else if (destination === "workflows/plan" || route.request().method() === "PUT") {
          calls.push(route.request().postDataJSON());
          data = { workflow: published };
        } else if (destination.endsWith("/execute")) {
          calls.push(route.request().postDataJSON());
          data = { run: { ...evidence.run, workflow_id: published.workflow_id, workflow_version: 1, status: "queued", approvals: [] } };
        } else if (destination.startsWith("workflows/")) data = { workflow: url.searchParams.get("version") === "1" ? published : draft };
        await route.fulfill({ json: { request_id: "req_prompt_only", status: 200, data } });
      });
      if (mode === "setup") {
        await page.goto("/app");
        const prompt = "Read https://docs.google.com/spreadsheets/d/test_sheet_1234567890/edit range Sheet1!A:D and prepare a report when I start it.";
        await page.getByLabel("Process description").fill(prompt);
        await expect(page.getByLabel("Google Sheets URL or ID")).toHaveCount(0);
        await expect(page.getByRole("combobox", { name: "Workflow input source" })).toHaveCount(0);
        await page.getByRole("button", { name: "Generate workflow" }).click();
        await expect(page.getByRole("region", { name: "Generation result" })).toBeVisible();
        await page.getByRole("button", { name: "Review and edit workflow" }).click();
        await expect(page).toHaveURL(new RegExp(`/app/workflows/${published.workflow_id}$`));
        expect(sessionRequests).toBeGreaterThanOrEqual(2);
        const planning = calls.find((call) => call.operation === "plan_workflow");
        expect(planning?.payload.objective).toBe(prompt);
        expect(planning?.payload.context).toMatchObject({ execution_input_mode: "automatic" });
      } else {
        await page.goto("/app/workflows");
        await page.getByRole("button", { name: `Actions for ${published.name}` }).click();
        await page.getByRole("menuitem", { name: "Run published" }).click();
        if (mode === "manual") {
          await page.getByRole("button", { name: "Start run", exact: true }).click();
          await expect.poll(() => calls.filter((call) => call.operation === "execute_workflow").length).toBe(1);
          expect(calls.find((call) => call.operation === "execute_workflow")?.payload).toMatchObject({ workflow_version: 1, inputs: {} });
        } else {
          await expect(page.getByText(/This workflow waits for its configured event/)).toBeVisible();
          expect(calls.filter((call) => call.operation === "execute_workflow")).toHaveLength(0);
        }
      }
      expect(dialogs).toEqual([]);
      expect(errors).toEqual([]);
    });
  }
}
