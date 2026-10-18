import { test, expect } from "@playwright/test";
import { readFileSync } from "node:fs";

const fixture = JSON.parse(
  readFileSync(new URL("./fixtures/source-selection.json", import.meta.url), "utf8"),
);

// API fixtures exercise presentation, not model routing or live database reads.
for (const mobile of [false, true]) {
  for (const engine of ["postgresql", "mongodb", "both"] as const) {
    test(`selected source preview ${engine} on ${mobile ? "mobile" : "desktop"}`, async ({
      page,
    }) => {
      if (mobile) await page.setViewportSize({ width: 390, height: 844 });
      const errors: string[] = [];
      page.on("pageerror", (error) => errors.push(error.message));
      const preview = structuredClone(fixture);
      if (engine !== "both") {
        preview.sources = preview.sources.filter(
          (source: { engine: string }) => source.engine === engine,
        );
        preview.relationships = [];
        preview.business_mappings = [];
        preview.sources[0].fields = [{ ...preview.sources[0].fields[0], purposes: ["row_count"] }];
        preview.sources[0].reasons = [
          "Base dataset in the validated plan.",
          "Supplies rows for counting; an enumeration field is required.",
        ];
      } else {
        preview.sources[0].fields = preview.sources[0].fields.filter(
          (field: { field_id: string }) => field.field_id !== "order_amount",
        );
        preview.sources[0].reasons = [
          "Base dataset in the validated plan.",
          "Provides keys required to link selected datasets.",
        ];
      }
      const base = preview.sources[0].dataset_id;
      let reads = 0;
      let reviewedPlan: unknown;
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
              permissions: ["workflow.view", "tools.read", "tools.assign"],
              scopes: [],
              decision: "allow",
            },
          };
        if (path === "data-sources")
          data = { configured: true, shared_demo_identity: false, items: [] };
        if (path === "data-queries")
          data = {
            configured: true,
            max_rows_per_dataset: 5000,
            max_bytes: 2000000,
            max_datasets: 4,
            max_result_rows: 500,
            plan_ttl_seconds: 600,
          };
        if (path === "data-queries/plan") {
          const question = route.request().postDataJSON().question;
          data = {
            plan_id: "dq_selection",
            question,
            graph_revision: 1,
            created_at: "2026-10-18T00:00:00Z",
            expires_at: 2000000000,
            selection_preview: preview,
            field_labels: Object.fromEntries(
              preview.sources.flatMap((source: { fields: { field_id: string; label: string }[] }) =>
                source.fields.map((field) => [field.field_id, field.label]),
              ),
            ),
            dataset_labels: Object.fromEntries(
              preview.sources.map((source: { dataset_id: string; label: string }) => [
                source.dataset_id,
                source.label,
              ]),
            ),
            plan: {
              base_dataset_id: base,
              joins:
                engine === "both"
                  ? [{ relationship_id: "orders_customers", target_dataset_id: "customers" }]
                  : [],
              fields: [],
              filters: [],
              group_by: engine === "both" ? ["customer_name"] : [],
              metrics: [{ label: "count", op: "count", expression: "" }],
              order_by: [],
              limit: 100,
              explanation: "Count complete matching rows in the selected sources.",
              clarification: question === "Unclear measure" ? "Which measure and time range?" : "",
            },
          };
        }
        if (path === "data-queries/plan") reviewedPlan = (data as {plan: unknown}).plan;
        if (path === "data-queries/execute") {
          expect(route.request().postDataJSON()).toEqual({ plan_id: "dq_selection" });
          reads++;
          data = {
            plan_id: "dq_selection",
            executed_plan: reviewedPlan,
            columns: [{ key: "count", label: "count" }],
            rows: [{ count: 2 }],
            total_result_rows: 1,
            matched_rows: 2,
            limited: false,
            executed_at: "2026-10-18T00:00:01Z",
            explanation: "Count complete matching rows.",
            warnings: [],
            join_checks: [],
            sources: preview.sources.map((source: { dataset_id: string; label: string }) => ({
              dataset_id: source.dataset_id,
              label: source.label,
              metadata_revision: 1,
              rows_read: 2,
              started_at: "2026-10-18T00:00:00Z",
              finished_at: "2026-10-18T00:00:01Z",
            })),
          };
        }
        await route.fulfill({
          status: 200,
          json: { request_id: "req_selection", status: 200, data },
        });
      });
      await page.goto("/app/data-intelligence");
      await page.getByRole("tab", { name: "Questions", exact: true }).click();
      await page.getByLabel("Your data question").fill("Count selected records");
      await page.getByRole("button", { name: "Create query plan" }).click();
      const selection = page.getByRole("region", { name: "Selected sources", exact: true });
      await expect(
        selection.getByText(`Selected sources (${preview.sources.length})`, { exact: true }),
      ).toBeVisible();
      await expect(selection.getByLabel("Selected graph subset")).toBeVisible();
      for (const source of preview.sources) {
        await selection.getByLabel("Inspect selected dataset").selectOption(source.dataset_id);
        await expect(
          selection.getByRole("region", { name: "Selected source details" }),
        ).toContainText(source.label);
      }
      expect(reads).toBe(0);
      if (engine === "both")
        await expect(
          selection.getByRole("region", { name: "Selected linking fields" }),
        ).toContainText("accepted");
      await page.getByRole("button", { name: "Run read-only query" }).click();
      await expect(page.getByRole("cell", { name: "2", exact: true })).toBeVisible();
      await page.getByText("Executed logical read plan", {exact: true}).click();
      await expect(page.getByLabel("Executed logical query")).toContainText(base);
      expect(reads).toBe(1);
      await page.getByLabel("Your data question").fill("Unclear measure");
      await page.getByRole("button", { name: "Create query plan" }).click();
      await expect(page.getByText("Which measure and time range?")).toBeVisible();
      await expect(selection).toHaveCount(0);
      await expect(page.getByRole("button", { name: "Run read-only query" })).toHaveCount(0);
      expect(reads).toBe(1);
      expect(errors).toEqual([]);
      expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(
        true,
      );
    });
  }
}
