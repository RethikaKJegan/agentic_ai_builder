import { test, expect } from "../../../frontend/node_modules/@playwright/test/index.mjs";
for (const mobile of [false, true]) {
  test(`extension discovery and approved connector execution on ${mobile ? "mobile" : "desktop"}`, async ({ page }) => {
    if (mobile) await page.setViewportSize({ width: 390, height: 844 });
    const errors: string[] = [];
    page.on("pageerror", error => errors.push(error.message));

    await page.goto("/app/integrations");
    await expect(page.getByRole("button", { name: "Test server connection" })).toHaveCount(19);
    await expect(page.getByText("extension_mail_attachment · v1", { exact: true })).toBeVisible();
    await expect(page.getByText("extension_calendar_create · v1", { exact: true })).toBeVisible();
    await page.getByRole("button", { name: "Test server connection" }).first().click();
    await expect(page.getByText("Extension configuration is available; no live connection test was performed.").first()).toBeVisible();
    await page.goto("/app/workflows");
    await page.getByRole("button", { name: "Actions for Extension Calendar smoke" }).click();
    await page.getByRole("menuitem", { name: "Run published" }).click();
    await expect(page.getByText(/Run run_.* is paused_for_approval/)).toBeVisible();
    await page.goto("/app/approvals");
    const run = page.getByRole("button", { name: /extension_calendar_browser/ }).first();
    await expect(run).toBeVisible();
    await run.click();
    await page.getByRole("button", { name: "Approve", exact: true }).click();
    await expect(page.getByText(/Approval approval_.* · approved · v1/)).toBeVisible();
    await page.goto("/app/runs");
    await expect(page.getByRole("button", { name: /completed.*extension_calendar_browser/ }).first()).toBeVisible();
    await page.goto("/app");
    const link = "https://docs.google.com/spreadsheets/d/new_project_book/edit";
    await page.getByLabel("Process description").fill(`Read ${link}, discover tabs and headers, and summarize the requirements.`);
    await page.getByRole("button", { name: "Generate workflow", exact: true }).click();
    await expect(page).toHaveURL(/\/app\/workflows\/planned_/);
    await page.getByRole("button", { name: "Publish", exact: true }).click();
    await expect.poll(async () => {
      const overview = await page.request.get("/api/backend/workflow-overview");
      const item = (await overview.json()).data.items.find((row: { name: string }) => row.name === "New spreadsheet check");
      return item?.activation_state;
    }).toBe("active");
    await page.goto("/app/workflows");
    await page.getByRole("button", { name: "Actions for New spreadsheet check" }).click();
    await page.getByRole("menuitem", { name: "Run published" }).click();
    await expect(page.getByText(/Run run_.* is completed/)).toBeVisible();
    const response = await page.request.get("/api/backend/workflows");
    const document = (await response.json()).data.items.find((workflow: { name: string }) => workflow.name === "New spreadsheet check");
    expect(document.nodes.find((node: { kind: string }) => node.kind === "tool").configuration.input.spreadsheet_url).toBe(link);
    await page.getByRole("button", { name: "Actions for Extension Mail smoke" }).click();
    await page.getByRole("menuitem", { name: "Run published" }).click();
    await expect(page.getByText(/Run run_.* is paused_for_approval/)).toBeVisible();
    await page.goto("/app/approvals");
    await page.getByRole("button", { name: /extension_mail_browser/ }).first().click();
    await page.getByRole("button", { name: "Approve", exact: true }).click();
    await expect(page.getByText(/Approval approval_.* · approved · v1/)).toBeVisible();
    await page.goto("/app/runs");
    await expect(page.getByRole("button", { name: /completed.*extension_mail_browser/ }).first()).toBeVisible();
    expect(errors).toEqual([]);
  });
}
