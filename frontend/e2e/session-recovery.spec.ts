import { test, expect } from "@playwright/test";

// Recovery may span two documented 15-second polling cycles.
test.setTimeout(60000);

for (const mobile of [false, true]) {
  test(`open workflows recover a stale session on ${mobile ? "mobile" : "desktop"}`, async ({ page }) => {
    if (mobile) await page.setViewportSize({ width: 390, height: 844 });
    let expired = false;
    let renewalBlocked = true;
    let renewals = 0;
    const errors: string[] = [];
    page.on("pageerror", (error) => errors.push(error.message));
    await page.route("**/api/backend/**", async (route) => {
      const path = new URL(route.request().url()).pathname.replace("/api/backend/", "");
      const denied = expired && (path !== "session" || renewalBlocked);
      let data: unknown = { items: [], total: 0, has_more: false, next_cursor: null };
      if (denied) data = { error: { error_code: "AUTHENTICATION_REQUIRED", message: "Expired local session", request_id: "req_expired", retryable: false } };
      else if (path === "session") {
        if (expired) { renewals += 1; expired = false; }
        data = { mode: "local-development", planning_available: false, runtime_available: true, approval_service_available: true,
          auth: { subject: { subject_id: "operator", workspace_id: "local-workspace" }, roles: ["admin"], permissions: ["workflow.view"], scopes: [], decision: "allow" } };
      } else if (path.startsWith("workflow-overview")) data = { items: [], next_sequence: 0, has_more: false };
      await route.fulfill({ status: denied ? 401 : 200, json: { request_id: "req_recovery", status: denied ? 401 : 200, data } });
    });
    await page.goto("/app/workflows");
    await expect(page.getByText("Live overview", { exact: false })).toBeVisible({ timeout: 25000 });
    expired = true;
    const authenticationError = page.getByRole("alert").filter({ hasText: "AUTHENTICATION_REQUIRED" });
    await expect(authenticationError).toContainText("Expired local session", { timeout: 25000 });
    renewalBlocked = false;
    await expect(authenticationError).toHaveCount(0, { timeout: 25000 });
    await expect(page.getByText("Live overview", { exact: false })).toBeVisible({ timeout: 25000 });
    expect(renewals).toBe(1);
    expect(errors).toEqual([]);
  });
}
