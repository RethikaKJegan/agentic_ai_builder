import { test, expect } from "@playwright/test";

for (const decision of ["approved", "rejected"] as const) {
  test(`Slack DM approval ${decision} uses the exact run and exposes both pending messages`, async ({ page }) => {
    const approvals = [1, 2].map((id) => ({ approval_id: `approval_dm_${id}`, workflow_id: "slack-dm-gmail", workflow_version: 1,
      status: "pending", allowed_decisions: ["approved", "rejected"] }));
    const runs = approvals.map((approval, index) => ({ run_id: `run_dm_${index + 1}`, workflow_id: "slack-dm-gmail", workflow_version: 1,
      status: "paused_for_approval", approvals: [approval] }));
    let submitted: Record<string, unknown> | undefined;
    await page.route("**/api/backend/**", async (route) => {
      const path = new URL(route.request().url()).pathname.replace("/api/backend/", "");
      const collection = { items: [], total: 0, has_more: false, next_cursor: null };
      let data: unknown = collection;
      if (path === "session") data = { mode: "local-development", planning_available: false, runtime_available: true, approval_service_available: true,
        auth: { subject: { subject_id: "local-builder", workspace_id: "local-workspace" }, roles: ["admin", "approver"],
          permissions: ["workflow.view", "workflow.approve", "runs.view"], scopes: ["workspace:read", "workspace:write"], decision: "allow" } };
      else if (path.startsWith("workflow-overview")) data = { items: [], next_sequence: 0, has_more: false };
      else if (path === "runs") data = { ...collection, items: runs, total: runs.length };
      else if (path === "runs/run_dm_1") data = { run: runs[0] };
      else if (path === "approvals/approval_dm_1/decision") {
        submitted = route.request().postDataJSON().payload;
        approvals[0]!.status = decision;
        approvals[0]!.allowed_decisions = [];
        runs[0]!.status = decision === "approved" ? "running" : "rejected";
        data = approvals[0];
      }
      await route.fulfill({ json: { request_id: "req_browser_slack", status: 200, data } });
    });
    await page.goto("/app/approvals");
    await expect(page.getByRole("button", { name: /run_dm_1/ })).toBeVisible();
    await expect(page.getByRole("button", { name: /run_dm_2/ })).toBeVisible();
    await page.getByRole("button", { name: /run_dm_1/ }).click();
    await page.getByRole("button", { name: decision === "approved" ? "Approve" : "Reject", exact: true }).click();
    await expect(page.getByText(`Approval approval_dm_1 · ${decision} · v1`)).toBeVisible();
    expect(submitted).toEqual({ approval_id: "approval_dm_1", workflow_id: "slack-dm-gmail", workflow_version: 1, decision });
  });
}
