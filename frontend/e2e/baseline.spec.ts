import { test, expect } from "@playwright/test";
import { localDraft } from "./helpers";

test("landing and workspace navigation preserve routes without demo controls", async ({ page }) => {
  const errors: string[] = [];
  page.on("pageerror", (error) => errors.push(error.message));
  await page.goto("/");
  await expect(page.getByRole("heading", { name: "An entire AI workforce. One coordinated system." })).toBeVisible();
  await expect(page.getByRole("link", { name: /interactive demo/i })).toHaveCount(0);
  await page.getByRole("link", { name: "Launch Workspace", exact: true }).first().click();
  await expect(page.getByRole("button", { name: "Generate workflow", exact: true })).toBeVisible();
  await expect(page.getByText("Investor demo")).toHaveCount(0);
  await page.getByRole("button", { name: "Search or jump to…" }).click();
  await page.getByPlaceholder("Search workflows, agents, or actions…").fill("Integrations");
  await page.getByRole("option", { name: "Integrations" }).click();
  await expect(page).toHaveURL(/\/app\/integrations$/);
  await expect(page.getByRole("heading", { name: "Integrations", exact: true })).toBeVisible();
  await expect(page.getByRole("button", { name: /^(connect|configure|reconnect|disconnect)$/i })).toHaveCount(0);
  expect(errors).toEqual([]);
});

test("local draft canvas editing, undo and reload persistence work", async ({ page }) => {
  const errors: string[] = [];
  page.on("pageerror", (error) => errors.push(error.message));
  await localDraft(page,"Review procurement");
  await expect(page).toHaveURL(/\/app\/workflows\/wf_/);
  await expect(page.getByLabel("Workflow name", { exact: true })).toHaveValue("Review procurement");
  await expect(page.locator(".react-flow__node")).toHaveCount(2);
  await expect(page.getByRole("button", { name: "Test", exact: true })).toHaveCount(0);
  // This suite uses a server-configured admin to cover publication; local drafts cannot publish.
  await expect(page.getByRole("button", { name: "Publish", exact: true })).toBeDisabled();
  await page.getByRole("button", { name: "Add step" }).click();
  await page.getByRole("menuitem", { name: "New AI agent", exact: true }).click();
  await expect(page.locator(".react-flow__node")).toHaveCount(3);
  await page.getByRole("button", { name: "Close inspector" }).click();
  await page.getByRole("button", { name: "Undo", exact: true }).click();
  await expect(page.locator(".react-flow__node")).toHaveCount(2);
  await page.getByRole("button", { name: "Redo", exact: true }).click();
  await expect(page.locator(".react-flow__node")).toHaveCount(3);
  await page.getByLabel("Workflow name", { exact: true }).fill("Procurement review draft");
  await page.reload();
  await expect(page.getByLabel("Workflow name", { exact: true })).toHaveValue("Procurement review draft");
  await expect(page.locator(".react-flow__node")).toHaveCount(3);
  await page.keyboard.press("Control+Enter");
  await expect(page.getByRole("button", { name: "Run simulation", exact: true })).toHaveCount(0);
  expect(await page.evaluate(() => JSON.parse(localStorage.getItem("mesh-local-drafts-v1")!).state.runs)).toEqual([]);
  expect(errors).toEqual([]);
});

test("all workspace routes load without demo role controls", async ({ page }) => {
  const errors: string[] = [];
  page.on("pageerror", (error) => errors.push(error.message));
  for (const name of ["workflows", "agents", "marketplace", "integrations", "knowledge", "approvals", "runs", "monitoring", "governance", "settings"]) {
    await page.goto(`/app/${name}`);
    await expect(page.getByRole("heading", { name: new RegExp(`^${name}$`, "i"), exact: true })).toBeVisible();
  }
  await expect(page.getByRole("button", { name: /switch role|reset demo/i })).toHaveCount(0);
  await page.goto("/app/marketplace?asset=mk_tl_slack");
  await expect(page.getByRole("button", { name: /connect/i })).toHaveCount(0);
  await page.goto("/app/workflows/missing");
  await expect(page.getByText("Workflow not found")).toBeVisible();
  await page.goto("/does-not-exist");
  await expect(page.getByRole("heading", { name: "Page not found" })).toBeVisible();
  expect(errors).toEqual([]);
});

test("mobile navigation and local draft editor remain usable", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/app");
  await page.getByRole("button", { name: "More", exact: true }).click();
  await page.getByRole("dialog").getByRole("link", { name: "Integrations", exact: true }).click();
  await expect(page).toHaveURL(/\/app\/integrations$/);
  await localDraft(page,"Mobile draft");
  await expect(page.getByLabel("Workflow name", { exact: true })).toHaveValue("Mobile draft");
  await expect(page.getByRole("button", { name: "Add step" })).toBeVisible();
});
