import { test, expect, type Page } from "@playwright/test";
import { readFileSync } from "node:fs";
import type { DatabaseOperation, DatabaseStep } from "../src/api/data-operations";

const fixture = JSON.parse(
  readFileSync(new URL("./fixtures/database-operations.json", import.meta.url), "utf8"),
);

// Presentation fixtures. Python tests separately execute real disposable engines.
async function setup(page: Page, mode: "normal" | "uncertain" | "disabled" = "normal") {
  const operations = new Map<string, DatabaseOperation>();
  const records = new Map<string, DatabaseStep["values"]>();
  const keys = new Map<string, string>();
  let executions = 0;
  const recordKey = (step: { connection_id: string; identity: Record<string, unknown> }) =>
    step.connection_id + JSON.stringify(step.identity);
  function prepare(steps: DatabaseStep[], recoveryOf: string | null = null) {
    const id = "dbop_" + (operations.size + 1).toString(16).padStart(32, "0");
    const now = Date.now() / 1000;
    const operation: DatabaseOperation = {
      operation_id: id,
      state: "prepared",
      created_at: now,
      expires_at: now + 600,
      recovery_until: now + 86400,
      recovery_of: recoveryOf,
      recovery_operation_id: null,
      preview_available: true,
      steps: steps.map((step) => {
        const target = fixture.targets.find(
          (item: { dataset_id: string }) => item.dataset_id === step.dataset_id,
        )!;
        const before = records.get(recordKey(step));
        return {
          ...structuredClone(step),
          label: target.label,
          tool_id: `${target.engine}_${step.action}_record`,
          state: "pending",
          matched_records: 0,
          affected_records: 0,
          error_code: null,
          before: before ? structuredClone(before) : null,
          after: null,
        } as DatabaseOperation["steps"][number];
      }),
    };
    operations.set(id, operation);
    return operation;
  }
  await page.route("**/api/backend/**", async (route) => {
    const path = new URL(route.request().url()).pathname.replace("/api/backend/", "");
    let data: unknown = { items: [], total: 0, has_more: false, next_cursor: null };
    if (path === "session")
      data = {
        mode: "local-development",
        planning_available: false,
        runtime_available: false,
        approval_service_available: false,
        auth: {
          subject: { subject_id: "test", workspace_id: "test" },
          roles: ["admin"],
          permissions: ["workflow.view", "tools.read", "tools.assign", "workflow.approve"],
          scopes: ["workspace:read", "workspace:write"],
          decision: "allow",
        },
      };
    else if (path === "data-sources")
      data = { configured: true, shared_demo_identity: false, items: [] };
    else if (path === "data-operations")
      data = {
        ...fixture,
        configured: mode !== "disabled",
        targets: mode === "disabled" ? [] : fixture.targets,
        items: [...operations.values()]
          .reverse()
          .map((item) => ({ ...item, preview_available: false })),
      };
    else if (path === "data-operations/read") {
      const body = route.request().postDataJSON();
      const record = records.get(recordKey(body));
      data = {
        record: record ?? null,
        matched_records: record ? 1 : 0,
        label: fixture.targets.find(
          (item: { dataset_id: string }) => item.dataset_id === body.dataset_id,
        ).label,
      };
    } else if (path === "data-operations/prepare") {
      const key = route.request().headers()["idempotency-key"]!;
      expect(key).toMatch(/^[a-zA-Z0-9_-]{8,128}$/);
      const prior = keys.get(key);
      data = prior ? operations.get(prior) : prepare(route.request().postDataJSON().steps);
      if (!prior) keys.set(key, (data as DatabaseOperation).operation_id);
    } else if (path.endsWith("/execute")) {
      expect(route.request().postDataJSON()).toEqual({ confirm: true });
      executions++;
      const operation = operations.get(path.split("/")[1]!)!;
      if (operation.state === "prepared") {
        if (mode === "uncertain") {
          operation.state = "uncertain";
          operation.steps[0]!.state = "uncertain";
          operation.steps[0]!.error_code = "DATA_WRITE_UNCERTAIN";
        } else {
          for (const step of operation.steps) {
            const key = recordKey({ connection_id: step.connection_id, identity: step.identity! });
            if (step.action === "delete") records.delete(key);
            else
              records.set(key, { ...(records.get(key) ?? {}), ...step.identity, ...step.values });
            for (const name of step.unset_fields ?? []) delete records.get(key)![name];
            step.state = "succeeded";
            step.matched_records = step.before ? 1 : 0;
            step.affected_records = 1;
            step.after = records.get(key) ?? null;
          }
          operation.state = "succeeded";
        }
      }
      data = operation;
    } else if (path.endsWith("/recover")) {
      expect(route.request().headers()["idempotency-key"]).toBeTruthy();
      const parent = operations.get(path.split("/")[1]!)!;
      const steps = parent.steps
        .filter((step) => step.state === "succeeded")
        .reverse()
        .map(
          (step) =>
            ({
              connection_id: step.connection_id,
              dataset_id: step.dataset_id,
              action:
                step.action === "delete"
                  ? "create"
                  : step.action === "create"
                    ? "delete"
                    : "update",
              identity: step.identity!,
              values:
                step.action === "create"
                  ? {}
                  : Object.fromEntries(
                      Object.entries(step.before ?? {}).filter(
                        ([name]) => !(name in step.identity!),
                      ),
                    ),
              unset_fields: [],
            }) as DatabaseStep,
        );
      const recovery = prepare(steps, parent.operation_id);
      parent.recovery_operation_id = recovery.operation_id;
      data = recovery;
    } else if (path.startsWith("data-operations/")) data = operations.get(path.split("/")[1]!);
    await route.fulfill({
      status: 200,
      json: { request_id: "req_operations_browser", status: 200, data },
    });
  });
  await page.goto("/app/data-intelligence");
  await page.getByRole("tab", { name: "Operations", exact: true }).click();
  return { executions: () => executions };
}

for (const mobile of [false, true]) {
  for (const engine of ["pg", "mongo"]) {
    test(`reviewed CRUD and guarded recovery ${engine} on ${mobile ? "mobile" : "desktop"}`, async ({
      page,
    }) => {
      if (mobile) await page.setViewportSize({ width: 390, height: 844 });
      const errors: string[] = [];
      page.on("pageerror", (error) => errors.push(error.message));
      const context = await setup(page);
      const target = fixture.targets.find(
        (item: { connection_id: string }) => item.connection_id === engine,
      )!;
      const identity = JSON.stringify({ [engine === "pg" ? "id" : "_id"]: "DEMO-001" });
      async function draft(action: string, name?: string) {
        await page.getByLabel("Operation dataset").selectOption(`${engine}:${target.dataset_id}`);
        await page.getByLabel("Record identity (JSON)").fill(identity);
        await page.getByLabel("Database action").selectOption(action);
        if (action !== "delete")
          await page
            .getByLabel("Field values (JSON)", { exact: true })
            .fill(JSON.stringify({ name }));
        await page.getByRole("button", { name: "Add operation step", exact: true }).click();
        await page.getByRole("button", { name: "Prepare operation", exact: true }).click();
        await expect(page.getByText("State: prepared", { exact: true })).toBeVisible();
        await expect(
          page.getByRole("button", { name: "Execute reviewed operation", exact: true }),
        ).toBeDisabled();
      }
      async function execute() {
        await page.getByRole("checkbox").check();
        await page.getByRole("button", { name: "Execute reviewed operation", exact: true }).click();
        await expect(page.getByText("State: succeeded", { exact: true })).toBeVisible();
      }
      await draft("create", "Created");
      expect(context.executions()).toBe(0);
      await execute();
      await page.getByRole("button", { name: "Read record", exact: true }).click();
      await expect(page.getByRole("region", { name: "Record read result" })).toContainText(
        "Created",
      );
      await page.getByRole("button", { name: "New operation", exact: true }).click();
      await draft("update", "Updated");
      await execute();
      await page.getByRole("button", { name: "New operation", exact: true }).click();
      await draft("delete");
      await execute();
      await page.getByRole("button", { name: "Read record", exact: true }).click();
      await expect(page.getByRole("region", { name: "Record read result" })).toContainText(
        "0 record matched",
      );
      await page.getByRole("button", { name: "Prepare guarded recovery", exact: true }).click();
      await expect(page.getByText(/Compensating operation for/)).toBeVisible();
      expect(context.executions()).toBe(3);
      await expect(
        page.getByRole("button", { name: "Execute reviewed operation", exact: true }),
      ).toBeDisabled();
      await execute();
      await page.getByRole("button", { name: "Read record", exact: true }).click();
      await expect(page.getByRole("region", { name: "Record read result" })).toContainText(
        "Updated",
      );
      expect(context.executions()).toBe(4);
      expect(errors).toEqual([]);
      expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(
        true,
      );
    });
  }
  test(`disabled operation policy on ${mobile ? "mobile" : "desktop"}`, async ({ page }) => {
    if (mobile) await page.setViewportSize({ width: 390, height: 844 });
    const context = await setup(page, "disabled");
    await expect(page.getByText(/No database operation targets are enabled/)).toBeVisible();
    await expect(page.getByRole("button", { name: "Add operation step" })).toHaveCount(0);
    expect(context.executions()).toBe(0);
  });
  test(`uncertain operation is not replayed on ${mobile ? "mobile" : "desktop"}`, async ({
    page,
  }) => {
    if (mobile) await page.setViewportSize({ width: 390, height: 844 });
    const context = await setup(page, "uncertain");
    await page.getByLabel("Record identity (JSON)").fill('{"id":"DEMO-001"}');
    await page.getByLabel("Field values (JSON)", { exact: true }).fill('{"name":"Demo"}');
    await page.getByRole("button", { name: "Add operation step", exact: true }).click();
    await page.getByRole("button", { name: "Prepare operation", exact: true }).click();
    await page.getByRole("checkbox").check();
    await page.getByRole("button", { name: "Execute reviewed operation", exact: true }).click();
    await expect(page.getByText(/The commit outcome is uncertain/)).toBeVisible();
    await expect(
      page.getByRole("button", { name: "Execute reviewed operation", exact: true }),
    ).toHaveCount(0);
    await expect(
      page.getByRole("button", { name: "Prepare guarded recovery", exact: true }),
    ).toHaveCount(0);
    await page.getByRole("button", { name: "Refresh operation status", exact: true }).click();
    expect(context.executions()).toBe(1);
  });
}
