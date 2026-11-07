import { test, expect } from "@playwright/test";
import { mutation } from "./helpers";
import { createHmac, randomBytes } from "node:crypto";

for (const mobile of [false, true]) {
  test(`current editor activation and persisted run ${mobile ? "mobile" : "desktop"}`, async ({ page }) => {
    test.setTimeout(90000);
    if (mobile) await page.setViewportSize({ width: 390, height: 844 });
    const secret = process.env["BUILDER_LOGIN_SECRET"];
    if (!secret || secret.length < 32) throw new Error("Provide an isolated browser-test signing key.");
    const payload = `${Math.floor(Date.now() / 1000) + 3600}.${randomBytes(24).toString("hex")}`;
    await page.context().addCookies([{ name: "builder_workspace_access",
      value: `${payload}.${createHmac("sha256", secret).update(payload).digest("hex")}`,
      domain: "127.0.0.1", path: "/" }]);
    await page.goto("/app");
    const session = await page.request.get("/api/backend/session");
    expect(session.status(), await session.text()).toBe(200);
    const template = await page.request.get("/api/backend/workflows/registry_ready");
    expect(template.status(), await template.text()).toBe(200);
    const canonical = (await template.json()).data.workflow;
    const id = "wf_current_release_" + crypto.randomUUID().replaceAll("-", "");
    const document = {
      ...canonical, workflow_id: id, version: 1, status: "draft", name: "Current release acceptance",
      agents: [], tools: [], inputs: [], outputs: [], conditions: [], approval_gates: [], metadata: {},
      nodes: [
        { node_id: "start", kind: "trigger", label: "Start", layout: { x: 40, y: 80 } },
        { node_id: "finish", kind: "output", label: "Finish", layout: { x: 420, y: 80 } },
      ],
      edges: [{ edge_id: "start_finish", source: "start", target: "finish" }],
    };
    const saved = await mutation(page, "save_workflow_version", `workflows/${id}/versions/1`,
      { workflow_id: id, workflow_version: 1, base_version: 0, workflow: document }, "PUT");
    expect(saved.status(), await saved.text()).toBe(200);
    await page.goto(`/app/workflows/${id}`);
    const actions = page.getByRole("region", { name: "Workflow launch actions" });
    await expect(actions.getByRole("button", { name: "Run", exact: true })).toBeDisabled();
    await actions.getByRole("button", { name: "Prepare & Activate", exact: true }).click();
    await expect(actions.getByText("Active · v1", { exact: true })).toBeVisible({ timeout: 30000 });
    const release = (await (await page.request.get(`/api/backend/workflows/${id}/release-state`)).json()).data.release;
    expect(release.state).toBe("active");
    expect(release.workflow_version).toBe(1);
    const published = (await (await page.request.get(`/api/backend/workflows/${id}`)).json()).data.workflow;
    expect(published.status).toBe("published");
    await actions.getByRole("button", { name: "Run", exact: true }).click();
    const runs = async () => (await (await page.request.get(`/api/backend/runs?workflow_id=${id}`)).json()).data;
    await expect.poll(async () => (await runs()).items?.[0]?.status, { timeout: 30000 }).toBe("completed");
    const completed = await runs();
    expect(completed.total).toBe(1);
    expect(completed.items[0].workflow_version).toBe(1);
    const runId = completed.items[0].run_id;
    await expect(page.getByLabel("Select workflow run")).toHaveValue(runId);
    await page.reload();
    await expect(page.getByLabel("Workflow name", { exact: true })).toHaveValue(document.name);
    await page.getByRole("tab", { name: "Execution", exact: true }).click();
    await expect(page.getByLabel("Select workflow run")).toHaveValue(runId);
    expect((await runs()).total).toBe(1);
    const refreshed = (await (await page.request.get(`/api/backend/workflows/${id}/release-state`)).json()).data.release;
    expect(refreshed.release_id).toBe(release.release_id);
    expect((await (await page.request.get(`/api/backend/runs/${runId}`)).json()).data.run.status).toBe("completed");
  });
}
