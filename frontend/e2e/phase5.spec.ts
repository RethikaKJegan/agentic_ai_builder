import { test, expect, type Page } from "@playwright/test";
async function setup(page: Page) {
  await page.goto("/app");
  await page.request.get("/api/backend/session");
  const template = (await (await page.request.get("/api/backend/workflows/registry_ready")).json())
    .data.workflow;
  const id = "wf_phase5_" + crypto.randomUUID().replaceAll("-", "");
  const d = {
    ...template,
    workflow_id: id,
    version: 1,
    status: "draft",
    name: "Phase 5 baseline",
    description: "Original description",
    agents: [],
    tools: [],
    inputs: [],
    outputs: [],
    conditions: [],
    approval_gates: [],
    metadata: {},
    nodes: [
      { node_id: "start", kind: "trigger", label: "Start", layout: { x: 40, y: 80 } },
      { node_id: "finish", kind: "output", label: "Finish", layout: { x: 420, y: 80 } },
    ],
    edges: [{ edge_id: "start_finish", source: "start", target: "finish" }],
  };
  const save = async (document: typeof d, base: number) => {
    const response = await page.request.put(
      `/api/backend/workflows/${id}/versions/${document.version}`,
      {
        data: {
          request_id: "req_phase5_browser",
          operation: "save_workflow_version",
          idempotency_key: crypto.randomUUID(),
          payload: {
            workflow_id: id,
            workflow_version: document.version,
            base_version: base,
            workflow: document,
          },
        },
      },
    );
    expect(response.status()).toBe(200);
    return (await response.json()).data.workflow;
  };
  const saved = await save(d, 0);
  await page.goto("/app/workflows/" + id);
  await expect(page.getByLabel("Workflow name", { exact: true })).toHaveValue(d.name);
  return { id, d: saved as typeof d, save };
}
for (const mobile of [false, true]) {
  test(`non-overlapping conflict rebase preserves edits ${mobile ? "mobile" : "desktop"}`, async ({
    page,
  }) => {
    if (mobile) await page.setViewportSize({ width: 390, height: 844 });
    const { id, d, save } = await setup(page);
    await page.getByLabel("Workflow name", { exact: true }).fill("Local edited name");
    await save({ ...d, version: 2, description: "Other editor description" }, 1);
    await page.evaluate(() => window.dispatchEvent(new Event("focus")));
    const conflict = page.getByRole("region", { name: "Draft conflict resolution" });
    await expect(conflict).toContainText("Server revision v2");
    await expect(page.getByLabel("Workflow name", { exact: true })).toHaveValue(
      "Local edited name",
    );
    await conflict.getByRole("button", { name: "Rebase non-overlapping edits" }).click();
    await expect(conflict).toHaveCount(0);
    const actions = page.getByRole("region", { name: "Workflow actions" });
    await expect(actions).toContainText("server revision v2");
    const server = (await (await page.request.get(`/api/backend/workflows/${id}`)).json()).data
      .workflow;
    expect(server.version).toBe(2);
    expect(server.name).toBe("Phase 5 baseline");
    await actions.getByRole("button", { name: "Save draft", exact: true }).click();
    await expect(actions).toContainText("Save draft confirmed · v3");
    await page.reload();
    await expect(page.getByLabel("Workflow name", { exact: true })).toHaveValue(
      "Local edited name",
    );
    const confirmed = (await (await page.request.get(`/api/backend/workflows/${id}`)).json()).data
      .workflow;
    expect(confirmed.description).toBe("Other editor description");
    expect(confirmed.nodes[0].layout).toEqual({ x: 40, y: 80 });
  });
  test(`unknown save outcome is checked without replay ${mobile ? "mobile" : "desktop"}`, async ({
    page,
  }) => {
    if (mobile) await page.setViewportSize({ width: 390, height: 844 });
    const { id } = await setup(page);
    let submitted = 0;
    await page.route(`**/api/backend/workflows/${id}/versions/2`, async (route) => {
      submitted++;
      await route.fetch();
      await route.abort("failed");
    });
    await page.getByLabel("Workflow name", { exact: true }).fill("Accepted before response loss");
    await page.getByRole("button", { name: "Save draft", exact: true }).click();
    await expect(
      page.getByRole("region", { name: "Workflow actions" }).getByRole("alert"),
    ).toContainText("Outcome unknown");
    expect(submitted).toBe(1);
    await page.evaluate(() => window.dispatchEvent(new Event("focus")));
    const conflict = page.getByRole("region", { name: "Draft conflict resolution" });
    await expect(conflict).toContainText("Server revision v2");
    await conflict.getByRole("button", { name: "Rebase non-overlapping edits" }).click();
    await expect(conflict).toHaveCount(0);
    await expect(page.getByRole("region", { name: "Workflow actions" })).toContainText(
      "No unsaved changes",
    );
    await expect(
      page.getByRole("region", { name: "Workflow actions" }).getByRole("alert"),
    ).toHaveCount(0);
    expect(submitted).toBe(1);
  });
  test(`two tabs keep independent drafts and refuse overlapping rebase ${mobile ? "mobile" : "desktop"}`, async ({
    page,
    context,
  }) => {
    if (mobile) await page.setViewportSize({ width: 390, height: 844 });
    const { id, d, save } = await setup(page);
    await page.getByLabel("Workflow name", { exact: true }).fill("This tab draft");
    const other = await context.newPage();
    if (mobile) await other.setViewportSize({ width: 390, height: 844 });
    await other.goto("/app/workflows/" + id);
    await expect(other.getByLabel("Workflow name", { exact: true })).toHaveValue("This tab draft");
    await other.getByLabel("Workflow name", { exact: true }).fill("Other tab draft");
    await expect(page.getByRole("region", { name: "Draft conflict resolution" })).toContainText(
      "Another tab",
    );
    page.once("dialog", (dialog) => dialog.accept());
    await page.reload();
    await expect(page.getByLabel("Workflow name", { exact: true })).toHaveValue("This tab draft");
    await save({ ...d, version: 2, name: "Remote saved name" }, 1);
    await page.evaluate(() => window.dispatchEvent(new Event("focus")));
    const conflict = page.getByRole("region", { name: "Draft conflict resolution" });
    await expect(conflict).toContainText("Server revision v2");
    await conflict.getByRole("button", { name: "Rebase non-overlapping edits" }).click();
    await expect(conflict.getByRole("list", { name: "Overlapping changes" })).toContainText("name");
    await conflict.getByRole("button", { name: "Export working draft" }).click();
    await expect(conflict.getByLabel("Working draft export")).toHaveValue(/This tab draft/);
    await expect(other.getByLabel("Workflow name", { exact: true })).toHaveValue("Other tab draft");
  });
}

for (const mobile of [false, true]) {
  test(`uncertain first save recovery ${mobile ? "mobile" : "desktop"}`, async ({ page }) => {
    if (mobile) await page.setViewportSize({ width: 390, height: 844 });
    const id = "wf_firstsave_" + crypto.randomUUID().replaceAll("-", "");
    await page.addInitScript(
      ({ id }) => {
        if (sessionStorage.getItem("phase5-first-seeded")) return;
        const at = new Date().toISOString();
        localStorage.setItem(
          "mesh-local-drafts-v1",
          JSON.stringify({
            version: 1,
            state: {
              workflows: [
                {
                  id,
                  workspaceId: "local",
                  name: "First save draft",
                  description: "Deterministic first save",
                  prompt: "",
                  scenario: "custom",
                  status: "draft",
                  versions: [],
                  createdAt: at,
                  updatedAt: at,
                  nodes: [
                    {
                      id: "start",
                      type: "mesh",
                      position: { x: 40, y: 80 },
                      data: { kind: "trigger", label: "Start" },
                    },
                    {
                      id: "finish",
                      type: "mesh",
                      position: { x: 420, y: 80 },
                      data: { kind: "output", label: "Finish" },
                    },
                  ],
                  edges: [{ id: "start_finish", source: "start", target: "finish" }],
                },
              ],
              agents: [],
            },
          }),
        );
        sessionStorage.setItem("phase5-first-seeded", "1");
      },
      { id },
    );
    await page.goto("/app/workflows/" + id);
    let submitted = 0;
    await page.route(`**/api/backend/workflows/${id}/versions/1`, async (route) => {
      submitted++;
      await route.fetch();
      await route.abort("failed");
    });
    await page.getByRole("button", { name: "Save draft", exact: true }).click();
    await expect(
      page.getByRole("region", { name: "Workflow actions" }).getByRole("alert"),
    ).toContainText("Outcome unknown");
    await page.evaluate(() => window.dispatchEvent(new Event("focus")));
    const conflict = page.getByRole("region", { name: "Draft conflict resolution" });
    await expect(conflict).toContainText("Server revision v1");
    await expect(page.getByLabel("Workflow name", { exact: true })).toHaveValue("First save draft");
    page.once("dialog", (dialog) => dialog.accept());
    await conflict.getByRole("button", { name: "Discard and reload latest" }).click();
    await expect(conflict).toHaveCount(0);
    await expect(page.getByRole("region", { name: "Workflow actions" })).toContainText(
      "server revision v1",
    );
    expect(submitted).toBe(1);
  });
}
