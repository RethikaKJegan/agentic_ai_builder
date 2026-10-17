import { test, expect } from "@playwright/test";
import fs from "node:fs";
import path from "node:path";

for (const mobile of [false, true]) {
  test(`prompt-selected spreadsheet access is reviewable on ${mobile ? "mobile" : "desktop"}`, async ({ page }) => {
    if (mobile) await page.setViewportSize({ width: 390, height: 844 });
    const workflow = JSON.parse(fs.readFileSync(path.resolve(import.meta.dirname,
      "../../shared/contracts/examples/workflows/support-triage.json"), "utf8"));
    workflow.workflow_id = "sheet-access-review";
    workflow.metadata.workspace_id = "local-workspace";
    workflow.metadata.sheet_write_targets = [
      { spreadsheet_id: "prompt-selected-sheet", range: "Reviews!A1:F1000", identity_column: "review_id", writable_columns: ["status"], allow_create: false },
      { spreadsheet_id: "prompt-selected-sheet", range: "Followups!A1:F1000", identity_column: "review_id", writable_columns: ["findings", "body"], allow_create: true },
    ];
    await page.route("**/api/backend/**", async (route) => {
      const destination = new URL(route.request().url()).pathname.replace("/api/backend/", "");
      let data: unknown = { items: [], total: 0, has_more: false, next_cursor: null };
      if (destination === "session") data = {
        mode: "local-development", runtime_available: true, planning_available: true,
        approval_service_available: true, auth: { subject: { subject_id: "operator", workspace_id: "local-workspace" },
          roles: ["admin"], permissions: ["workflow.view", "workflow.publish", "runs.view"], scopes: ["workspace:read"], decision: "allow" },
      };
      else if (destination.startsWith("workflow-overview")) data = { items: [], next_sequence: 0, has_more: false };
      else if (destination === "workflows") data = { items: [workflow], total: 1, has_more: false, next_cursor: null };
      else if (destination.startsWith("workflows/")) data = { workflow };
      await route.fulfill({ json: { request_id: "sheet-review", status: 200, data } });
    });
    await page.goto("/app/workflows/sheet-access-review");
    await page.locator('summary[aria-label="Sheet write access"]').click();
    await expect(page.getByText("Reviews!A1:F1000", { exact: true })).toBeVisible();
    await expect(page.getByText("Followups!A1:F1000", { exact: true })).toBeVisible();
    await expect(page.getByText("Writable columns: status", { exact: true })).toBeVisible();
    await expect(page.getByText("Existing records only", { exact: true })).toBeVisible();
    await expect(page.getByText("Can create missing records", { exact: true })).toBeVisible();
    const link = page.getByRole("link", { name: "prompt-selected-sheet" }).first();
    await expect(link).toHaveAttribute("href", "https://docs.google.com/spreadsheets/d/prompt-selected-sheet/edit");
    const panel = page.getByText(/Review these destinations before approving and publishing/).locator("..");
    const box = await panel.boundingBox();
    expect(box).not.toBeNull();
    expect(box!.x).toBeGreaterThanOrEqual(0);
    expect(box!.x + box!.width).toBeLessThanOrEqual(page.viewportSize()!.width);
    await page.screenshot({ path: path.resolve(import.meta.dirname, `../../.local/sheet-access-${mobile ? "mobile" : "desktop"}.png`) });
  });
}
