import { test, expect } from "@playwright/test";
import fs from "node:fs";
import path from "node:path";
const fixture = JSON.parse(
  fs.readFileSync(path.resolve(import.meta.dirname, "fixtures/multitask-delegation.json"), "utf8"),
);
for (const mobile of [false, true]) {
  test(`whole project uses the clickable agent diagram on ${mobile ? "mobile" : "desktop"}`, async ({
    page,
  }) => {
    if (mobile) await page.setViewportSize({ width: 390, height: 844 });
    const errors: string[] = [];
    page.on("pageerror", (error) => errors.push(error.message));
    const workflow = {
      ...fixture.workflow,
      workflow_id: "project_diagram_test",
      name: "Review customer documents",
      metadata: { ...fixture.workflow.metadata, procurement_plan: { project_id: "diagram_test", name: "Document review", simulation: true, context: {}, requirements: { spreadsheet_url: "https://docs.google.com/spreadsheets/d/fixture_source/edit", range: "Records!A1:B10", columns: {} }, vendors: null } },
    };
    const { run, events } = fixture.runs[0];
    const project = {
      project_id: "diagram_test",
      phase: "ACTIVE",
      root_workflow: workflow,
      root_run: null,
      root_events: [],
      configured_workflow: null,
      truncated: false,
      actions: [{ key: "opaque_action_id", workflow: fixture.workflow, run, events }],
    };
    await page.route("**/api/backend/**", async (route) => {
      const destination = new URL(route.request().url()).pathname.replace("/api/backend/", "");
      const collection = { items: [], total: 0, has_more: false, next_cursor: null };
      let data: unknown = collection;
      if (destination === "session")
        data = {
          mode: "local-development",
          planning_available: false,
          runtime_available: true,
          approval_service_available: true,
          auth: {
            subject: { subject_id: "operator", workspace_id: "local-workspace" },
            roles: ["admin"],
            permissions: ["workflow.view", "runs.view"],
            scopes: ["workspace:read"],
            decision: "allow",
          },
        };
      else if (destination.endsWith("communication-project")) data = project;
      else if (destination.startsWith("workflow-overview"))
        data = { items: [], next_sequence: 0, has_more: false };
      else if (destination === "workflows") data = { ...collection, items: [workflow], total: 1 };
      else if (destination.startsWith("workflows/")) data = { workflow };
      await route.fulfill({ json: { request_id: "req_project_diagram", status: 200, data } });
    });
    await page.goto(`/app/workflows/${workflow.workflow_id}`);
    await page.getByRole("tab", { name: "Execution", exact: true }).click();
    await page.getByRole("button", { name: "Agent communication", exact: true }).click();
    const dialog = page.getByRole("dialog", { name: "Agent communication", exact: true });
    await expect(dialog.getByRole("button", { name: "Step-by-step" })).toHaveCount(0);
    await expect(dialog.getByText(/^Spawned · Task/)).toHaveCount(3);
    const spawn = events.find((e: { event_type: string }) => e.event_type === "agent.spawned");
    await dialog
      .locator(`.react-flow__node[data-id="${run.run_id}:${spawn.details.node_id}"]`)
      .click();
    const panel = dialog.getByLabel("Agent details");
    await expect(
      panel.getByText("This helper was started for a separate task in this run."),
    ).toBeVisible();
    await expect(panel.locator("p").filter({ hasText: /^Classify ticket A:/ })).toBeVisible();
    await panel.getByRole("button", { name: "Close details" }).click();
    await dialog.getByRole("button", { name: "Task assigned", exact: true }).first().click();
    await expect(panel.getByText("Information shared", { exact: true })).toBeVisible();
    expect(errors).toEqual([]);
  });
}
