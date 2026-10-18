import { test, expect } from "@playwright/test";
import { readFileSync } from "node:fs";
const fixture = JSON.parse(
  readFileSync(new URL("./fixtures/detailed-graph.json", import.meta.url), "utf8"),
);

// Browser API fixtures; Python tests separately verify real inference/storage/auth.
for (const mobile of [false, true]) {
  test(`detailed graph containment, business review and reload on ${mobile ? "mobile" : "desktop"}`, async ({
    page,
  }) => {
    if (mobile) await page.setViewportSize({ width: 390, height: 844 });
    const errors: string[] = [];
    page.on("pageerror", (e) => errors.push(e.message));
    const view = structuredClone(fixture);
    const customer = view.graph.mappings.find((mapping) => mapping.node_id === "mongo_customers")!;
    const field = view.graph.nodes.find((node) => node.node_id === "mongo_customers_customerID")!;
    for (let index = 0; index < 101; index++) {
      const id = `customer_attribute_${index}`;
      view.graph.nodes.push({ ...field, node_id: id, label: `attribute_${index}` });
      view.graph.mappings.push({ ...customer, node_id: id, role: "attribute" });
    }
    const entitySourceCount = view.graph.mappings.filter((mapping) => mapping.entity_id === customer.entity_id).length;
    let buildReads = 0;
    let building = false;
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
      else if (path === "data-sources")
        data = { configured: true, shared_demo_identity: false, items: [] };
      else if (path === "data-relationships/build") {
        building = true;
        buildReads = 0;
        view.build_status = "queued";
        data = {
          ...view,
          graph: {
            ...view.graph,
            nodes: view.graph.nodes.filter((n) =>
              ["connection", "dataset", "field"].includes(n.kind),
            ),
          },
        };
      } else if (path.startsWith("data-relationships/v2")) {
        if (building && ++buildReads >= 2) {
          view.build_status = "ready";
          view.graph.revision++;
          building = false;
        }
        if (route.request().method() === "POST") {
          const body = route.request().postDataJSON();
          expect(body.revision).toBe(view.graph.revision);
          const id = path.split("/").at(-1)!;
          const mapping = view.graph.mappings.find((m) => m.node_id === id)!;
          mapping.entity_name =
            body.status === "suggested" ? mapping.proposed_name : body.entity_name;
          mapping.role = body.role;
          mapping.status = body.status;
          view.graph.revision++;
        }
        data = view;
      } else if (path.startsWith("data-relationships/review/")) {
        const body = route.request().postDataJSON();
        expect(body.revision).toBe(view.graph.revision);
        view.graph.relationships.find((e) => e.relationship_id === path.split("/").at(-1))!.status =
          body.status;
        view.graph.revision++;
        data = {
          ...view,
          graph: {
            ...view.graph,
            nodes: view.graph.nodes.filter((n) =>
              ["connection", "dataset", "field"].includes(n.kind),
            ),
          },
        };
      } else if (path === "data-relationships")
        data = {
          ...view,
          version: undefined,
          graph: {
            ...view.graph,
            nodes: view.graph.nodes.filter((n) =>
              ["connection", "dataset", "field"].includes(n.kind),
            ),
          },
        };
      await route.fulfill({
        status: 200,
        json: { request_id: "req_detailed_graph_browser", status: 200, data },
      });
    });
    await page.goto("/app/data-intelligence");
    await page.getByRole("tab", { name: "Relationships", exact: true }).click();
    await page.getByRole("button", { name: "Detailed knowledge graph", exact: true }).click();
    await expect(page.getByText(/Detailed graph v2 · revision 1/)).toBeVisible();
    await page.getByRole("button", { name: "Expand Postgres", exact: true }).click();
    await page.getByRole("button", { name: "Expand demo", exact: true }).click();
    await page.getByRole("button", { name: "Expand northwind", exact: true }).click();
    await page.getByRole("button", { name: "Expand northwind.orders", exact: true }).click();
    await page.getByRole("button", { name: "customerID (field)", exact: true }).click();
    await expect(page.getByLabel("Mapping role")).toHaveValue("reference");
    await page.getByText("Discovered metadata and constraints", { exact: true }).click();
    await expect(page.getByText("Stable ID: pg_orders_customerID", { exact: true })).toBeVisible();
    const relationships = page.getByRole("region", { name: "Qualified relationships" });
    await relationships.locator("summary").filter({ hasText: /declared$/ }).first().click();
    await relationships.getByRole("button", { name: "Postgres / demo / northwind / customers / customerID", exact: true }).first().click();
    await expect(page.getByText("Stable ID: pg_customers_customerID", { exact: true })).toBeVisible();
    await page.getByRole("button", { name: "Business entities", exact: true }).click();
    await page.getByTestId("mapping-mongo_customers").click();
    await page.getByRole("button", { name: "Confirm mapping", exact: true }).click();
    await expect(page.getByText("Review status: confirmed", { exact: true })).toBeVisible();
    await page.reload();
    await page.getByRole("tab", { name: "Relationships", exact: true }).click();
    await page.getByRole("button", { name: "Detailed knowledge graph", exact: true }).click();
    await page.getByRole("button", { name: "Business entities", exact: true }).click();
    await page.getByLabel("Mapping status").selectOption("confirmed");
    await page.getByTestId("mapping-mongo_customers").click();
    await expect(page.getByText("Review status: confirmed", { exact: true })).toBeVisible();
    await page.getByRole("button", { name: "Inspect entity: Customer", exact: true }).click();
    const entitySources = page.getByRole("region", { name: "Entity source mappings" });
    await expect(entitySources.getByText(`Showing 100 of ${entitySourceCount} source mappings`, { exact: true })).toBeVisible();
    await entitySources.getByRole("button", { name: "Show more entity sources", exact: true }).click();
    await expect(entitySources.getByText(`Showing ${entitySourceCount} of ${entitySourceCount} source mappings`, { exact: true })).toBeVisible();
    await entitySources.getByRole("button", { name: /Atlas \/ demo \/ customers \/ attribute_100 · attribute/ }).click();
    await expect(page.getByText("Stable ID: customer_attribute_100", { exact: true })).toBeVisible();
    await page.getByTestId("mapping-mongo_customers").click();
    await page.getByRole("button", { name: "Reject mapping", exact: true }).click();
    await expect(page.getByText("Review status: rejected", { exact: true })).toBeVisible();
    await page.getByRole("button", { name: "Reset mapping review", exact: true }).click();
    await expect(page.getByText("Review status: suggested", { exact: true })).toBeVisible();
    await page
      .locator('section[aria-label="Qualified relationships"] summary')
      .filter({ hasText: /proposed$/ })
      .first()
      .click();
    await page.getByRole("button", { name: "Accept relationship", exact: true }).click();
    await expect(
      page.getByText("Relationship review saved. Runtime key and permission checks still apply.", {
        exact: true,
      }),
    ).toBeVisible();
    // A short worker build must become visible without reload/tab switching.
    await page.getByRole("button", { name: "Build relationships", exact: true }).click();
    await expect(page.getByRole("button", { name: "Building…", exact: true })).toBeDisabled();
    await expect(
      page.getByRole("button", { name: "Build relationships", exact: true }),
    ).toBeEnabled({ timeout: 4000 });
    await expect(page.getByText(/Detailed graph v2 · revision 6/)).toBeVisible();
    await expect(
      page.getByRole("button", { name: "Business entities", exact: true }),
    ).toHaveAttribute("aria-pressed", "true");
    await page.screenshot({
      path: `test-results/detailed-graph-${mobile ? "mobile" : "desktop"}.png`,
      fullPage: true,
    });
    expect(errors).toEqual([]);
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(
      true,
    );
  });
  test(`stale graph blocks review on ${mobile ? "mobile" : "desktop"}`, async ({ page }) => {
    if (mobile) await page.setViewportSize({ width: 390, height: 844 });
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
      if (path.startsWith("data-relationships")) data = { ...fixture, stale: true };
      await route.fulfill({
        status: 200,
        json: { request_id: "req_stale_graph", status: 200, data },
      });
    });
    await page.goto("/app/data-intelligence");
    await page.getByRole("tab", { name: "Relationships", exact: true }).click();
    await page.getByRole("button", { name: "Detailed knowledge graph", exact: true }).click();
    await page.getByRole("button", { name: "Business entities", exact: true }).click();
    await page.getByTestId("mapping-mongo_customers").click();
    await expect(page.getByRole("button", { name: "Confirm mapping", exact: true })).toBeDisabled();
  });
}
