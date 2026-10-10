import { test, expect } from "@playwright/test";

test("planner drafts load canonical branches and gates, save revisions and survive reload", async ({ page }) => {
  const errors: string[] = [];
  page.on("pageerror", (error) => errors.push(error.message));
  await page.goto("/app");
  await page.getByLabel("Process description").fill("If an invoice arrives classify it and email the owner after approval");
  await page.getByRole("button", { name: "Plan workflow", exact: true }).click();
  await expect(page).toHaveURL(/\/app\/workflows\/planned_/);
  await expect(page.getByText("Server revision v1 · draft")).toBeVisible();
  await expect(page.locator(".react-flow__node")).toHaveCount(6);
  await expect(page.getByText(/Requested tools:.*smtp_send_email/)).toBeVisible();
  await page.locator('.react-flow__node[data-id="plan_objective"]').click();
  await page.getByRole("tab", { name: /^tools$/i }).click();
  await expect(page.getByText(/Requested capabilities:.*send_email/)).toBeVisible();
  await page.getByRole("button", { name: "Close inspector" }).click();
  await page.getByLabel("Workflow name", { exact: true }).fill("Connected invoice review");
  await expect(page.getByRole("button", { name: "Validate", exact: true })).toBeDisabled();
  await page.getByRole("button", { name: "Save revision", exact: true }).click();
  await expect(page.getByText("Server revision v2 · draft")).toBeVisible();
  await page.getByRole("button", { name: "Validate", exact: true }).click();
  await expect(page.getByText("Server revision v2 · validated")).toBeVisible();
  await expect(page.getByRole("button", { name: "Publish", exact: true })).toBeDisabled();
  await expect(page.getByText(/assignments require registry authorization/)).toBeVisible();
  await page.reload();
  await expect(page.getByLabel("Workflow name", { exact: true })).toHaveValue("Connected invoice review");
  await expect(page.getByText("Server revision v2 · validated")).toBeVisible();
  const id = new URL(page.url()).pathname.split("/").at(-1)!;
  const storage = await page.evaluate(() => JSON.parse(localStorage.getItem("mesh-local-drafts-v1")!).state.workflows);
  expect(storage.some((workflow: { id: string }) => workflow.id === id)).toBe(false);
  const response = await page.request.get(`/api/backend/workflows/${id}`);
  const document = (await response.json()).data.workflow;
  expect(document.conditions.length).toBeGreaterThan(0);
  expect(document.approval_gates.length).toBeGreaterThan(0);
  expect(document.agents[0].allowed_tool_ids).toEqual([]);
  expect(errors).toEqual([]);
});

test("trusted registry assignments allow publication and editable revisions drop old grants", async ({ page }) => {
  await page.goto("/app/workflows/registry_ready");
  await expect(page.getByText("Registry requirements authorized for this revision")).toBeVisible();
  await page.locator('.react-flow__node[data-id="read_rows"]').click();
  await page.getByRole("tab", { name: /^tools$/i }).click();
  await expect(page.getByText("read_spreadsheet · sheets_ready", { exact: true })).toBeVisible();
  await page.getByRole("button", { name: "Close inspector" }).click();
  await page.getByRole("button", { name: "Validate", exact: true }).click();
  await expect(page.getByRole("button", { name: "Approve revision", exact: true })).toBeEnabled();
  await page.getByRole("button", { name: "Approve revision", exact: true }).click();
  await expect(page.getByRole("button", { name: "Publish", exact: true })).toBeEnabled();
  await page.getByRole("button", { name: "Publish", exact: true }).click();
  await expect(page.getByText("Server revision v1 · published")).toBeVisible();
  await page.reload();
  await expect(page.getByText("Server revision v1 · published")).toBeVisible();
  await page.goto("/app/workflows");
  const overviewRow = page.locator(".divide-y > div").filter({ hasText: "Registry ready" });
  await expect(overviewRow).toContainText("published v1");
  await expect(overviewRow).toContainText("active");
  await overviewRow.getByLabel("Actions for Registry ready").click();
  await page.getByText("Edit draft", { exact: true }).click();
  await expect(page).toHaveURL(/\/app\/workflows\/registry_ready/);
  const result = await page.request.get("/api/backend/workflows/registry_ready");
  const document = (await result.json()).data.workflow;
  expect(document.agents[0].allowed_tool_ids).toEqual(["sheets_ready"]);
  expect(JSON.stringify(document)).not.toContain("cred_browser_sheets");
  await page.getByLabel("Workflow name", { exact: true }).fill("New editable registry revision");
  await page.getByRole("button", { name: "Save revision", exact: true }).click();
  await expect(page.getByText("Server revision v2 · draft")).toBeVisible();
  const revised = (await (await page.request.get("/api/backend/workflows/registry_ready")).json()).data.workflow;
  expect(revised.agents[0].allowed_tool_ids).toEqual([]);
});

test("pending approvals and risky assignments remain blocked in the actual UI", async ({ page }) => {
  for (const [id, reason] of [["registry_pending", "APPROVAL_REQUIRED"], ["registry_risky", "RISK_NOT_AUTHORIZED"]]) {
    await page.goto(`/app/workflows/${id}`);
    await expect(page.getByLabel("Registry assignment review")).toContainText(reason!);
    await page.getByRole("button", { name: "Validate", exact: true }).click();
    await expect(page.getByText("Server revision v1 · validated")).toBeVisible();
    await expect(page.getByRole("button", { name: "Approve revision", exact: true })).toBeDisabled();
    await expect(page.getByRole("button", { name: "Publish", exact: true })).toBeDisabled();
  }
});

test("local drafts save to canonical backend storage and validation errors stay actionable", async ({ page }) => {
  await page.goto("/app");
  await page.getByLabel("Workflow name", { exact: true }).fill("Persisted plain workflow");
  await page.getByRole("button", { name: "Create draft", exact: true }).click();
  await page.getByRole("button", { name: "Save revision", exact: true }).click();
  await expect(page.getByText("Server revision v1 · draft")).toBeVisible();
  const id = new URL(page.url()).pathname.split("/").at(-1)!;
  const existing = (await (await page.request.get(`/api/backend/workflows/${id}`)).json()).data.workflow;
  existing.version = 2;
  existing.edges[0].target = "missing_node";
  const response = await page.request.put(`/api/backend/workflows/${id}/versions/2`, { data: {
    request_id: "req_browser_invalid_graph", operation: "save_workflow_version", idempotency_key: "browser_invalid_graph_retry", payload: {
      workflow_id: id, workflow_version: 2, workflow: existing, base_version: 1,
    },
  } });
  expect(response.status()).toBe(200);
  await page.reload();
  await expect(page.getByText("Server revision v2 · draft")).toBeVisible();
  await page.getByRole("button", { name: "Validate", exact: true }).click();
  await expect(page.getByLabel("Workflow API controls").getByRole("alert")).toHaveText(/WORKFLOW_VALIDATION_FAILED.*edges\[0\].target/);
  await page.goto("/app/runs");
  await expect(page.getByText(/runtime API is not connected/)).toBeVisible();
  await page.goto("/app/approvals");
  await expect(page.getByText(/runtime API is not connected/)).toBeVisible();
  await expect(page.getByRole("button", { name: "Approve", exact: true })).toHaveCount(0);
});
