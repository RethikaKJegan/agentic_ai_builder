import { test, expect } from "@playwright/test";
for (const mobile of [false, true]) {
  test(`exact historical revision and preserved design ${mobile ? "mobile" : "desktop"}`, async ({
    page,
  }) => {
    if (mobile) await page.setViewportSize({ width: 390, height: 844 });
    const errors: string[] = [];
    page.on("pageerror", (e) => errors.push(e.message));
    await page.goto("/app");
    await page.request.get("/api/backend/session");
    const template = (
      await (await page.request.get("/api/backend/workflows/registry_ready")).json()
    ).data.workflow;
    const id = "wf_phase4_" + crypto.randomUUID().replaceAll("-", "");
    const revision = {
      ...template,
      workflow_id: id,
      version: 1,
      status: "draft",
      name: "Phase 4 exact revision",
      description: "A deterministic process for historical visualization",
      agents: [],
      tools: [],
      inputs: [],
      outputs: [],
      conditions: [],
      approval_gates: [],
      metadata: {},
      nodes: [
        { node_id: "start", kind: "trigger", label: "Historical start", layout: { x: 80, y: 100 } },
        {
          node_id: "finish",
          kind: "output",
          label: "Historical finish",
          layout: { x: 450, y: 100 },
        },
      ],
      edges: [{ edge_id: "start_finish", source: "start", target: "finish" }],
    };
    const mutation = async (operation: string, path: string, payload: unknown, method = "POST") => {
      const response = await page.request.fetch("/api/backend/" + path, {
        method,
        data: {
          request_id: "req_phase4_browser",
          operation,
          idempotency_key: crypto.randomUUID(),
          payload,
        },
      });
      expect(response.status()).toBe(200);
      return (await response.json()).data;
    };
    await mutation(
      "save_workflow_version",
      `workflows/${id}/versions/1`,
      { workflow_id: id, workflow_version: 1, base_version: 0, workflow: revision },
      "PUT",
    );
    await mutation("validate_workflow", `workflows/${id}/validate`, {
      workflow_id: id,
      workflow_version: 1,
    });
    await mutation("approve_workflow", `workflows/${id}/approve`, {
      workflow_id: id,
      workflow_version: 1,
      action: "approve",
    });
    await mutation("approve_workflow", `workflows/${id}/approve`, {
      workflow_id: id,
      workflow_version: 1,
      action: "publish",
    });
    const executed = await mutation("execute_workflow", `workflows/${id}/execute`, {
      workflow_id: id,
      workflow_version: 1,
      inputs: {},
    });
    const updated = {
      ...revision,
      version: 2,
      name: "Current revision two",
      nodes: [
        ...revision.nodes,
        {
          node_id: "draft_only",
          kind: "output",
          label: "Draft-only step",
          layout: { x: 800, y: 100 },
        },
      ],
    };
    await mutation(
      "save_workflow_version",
      `workflows/${id}/versions/2`,
      { workflow_id: id, workflow_version: 2, base_version: 1, workflow: updated },
      "PUT",
    );
    await page.goto("/app/workflows/" + id);
    await expect(page.getByLabel("Workflow name", { exact: true })).toHaveValue(
      "Current revision two",
    );
    await page.getByLabel("Workflow name", { exact: true }).fill("Unsaved working draft");
    await page.getByRole("tab", { name: "Execution", exact: true }).click();
    const execution = page.getByRole("region", { name: "Recorded execution" });
    await expect(execution.getByText(new RegExp("Read-only historical revision v1"))).toBeVisible();
    await expect(
      execution.locator("p").filter({ hasText: executed.run.run_id }).first(),
    ).toBeVisible();
    const outline = execution.getByRole("list", { name: "Recorded workflow steps" });
    await expect(outline.getByText(/Historical finish/)).toBeVisible();
    await expect(outline.getByText(/Draft-only step/)).toHaveCount(0);
    await expect(page.getByRole("button", { name: "Save draft", exact: true })).toHaveCount(0);
    await outline.getByRole("button", { name: /Historical finish/ }).click();
    await expect(execution.getByLabel("Node execution trace")).toBeVisible();
    await execution.getByRole("button", { name: "Return to editable draft" }).click();
    await expect(page.getByLabel("Workflow name", { exact: true })).toHaveValue(
      "Unsaved working draft",
    );
    await page.getByRole("tab", { name: "Agent hierarchy", exact: true }).click();
    await expect(page.getByText(/No agents are defined/)).toBeVisible();
    await page.getByRole("tab", { name: "Design", exact: true }).click();
    await page.getByText(/Workflow outline and connections/).click();
    const accessible = page.getByRole("list", { name: "Accessible workflow outline" });
    await expect(accessible.getByRole("button").first()).toContainText("Historical start");
    await page.getByLabel("Connection source").selectOption("start");
    await page.getByLabel("Connection target").selectOption("draft_only");
    await page.getByRole("button", { name: "Connect steps" }).focus();
    await page.keyboard.press("Enter");
    await expect(page.getByRole("button", { name: /Remove connection/ })).toHaveCount(2);
    await page.getByRole("button", { name: "Undo", exact: true }).click();
    await expect(page.getByRole("button", { name: /Remove connection/ })).toHaveCount(1);
    await page.getByRole("button", { name: "Redo", exact: true }).click();
    await expect(page.getByRole("button", { name: /Remove connection/ })).toHaveCount(2);
    await page.getByRole("button", { name: "Save draft", exact: true }).click();
    await expect(page.getByText(/Save draft confirmed · v3/)).toBeVisible();
    await page.reload();
    await expect(page.getByLabel("Workflow name", { exact: true })).toHaveValue(
      "Unsaved working draft",
    );
    expect(errors).toEqual([]);
  });
  test(`structured generation review ${mobile ? "mobile" : "desktop"}`, async ({ page }) => {
    if (mobile) await page.setViewportSize({ width: 390, height: 844 });
    await page.goto("/app");
    await page
      .getByLabel("Process description")
      .fill("Review invoice amounts and require manager approval before reporting the result.");
    await page.getByRole("button", { name: "Generate workflow", exact: true }).click();
    const result = page.getByRole("region", { name: "Generation result" });
    await expect(result).toBeVisible({ timeout: 30000 });
    await expect(page).toHaveURL(/\/app$/);
    await expect(result.getByText("Goal", { exact: true })).toBeVisible();
    await expect(result.getByText("Approval points", { exact: true })).toBeVisible();
    await result.getByRole("button", { name: "Review and edit workflow" }).click();
    await expect(page).toHaveURL(/\/app\/workflows\//);
    await expect(page.getByRole("tab", { name: "Design", exact: true })).toHaveAttribute(
      "aria-selected",
      "true",
    );
    await page.getByRole("tab",{name:"Agent hierarchy",exact:true}).click();
    await expect(page.getByText(/Master · Master orchestrator/)).toBeVisible();
    await expect(page.getByText(/Delegated ·/).first()).toBeVisible();
    await page.getByRole("tab",{name:"Design",exact:true}).click();
  });
}
