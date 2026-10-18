import { act, cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import { api } from "@/api/client";
import fixture from "../../../e2e/fixtures/detailed-graph.json";
import { detailedViewSchema } from "@/api/data-relationships";
import DetailedGraph from "./DetailedGraph";

const data = () => detailedViewSchema.parse(structuredClone(fixture));
afterEach(() => {
  cleanup();
  vi.useRealTimers();
  vi.restoreAllMocks();
});

it("exposes every entity source in qualified pages and preserves its page during refresh", async () => {
  vi.useFakeTimers();
  const value = data();
  const graph = value.graph!;
  const original = graph.mappings.find((mapping) => mapping.node_id === "mongo_customers")!;
  const field = graph.nodes.find((node) => node.node_id === "mongo_customers_customerID")!;
  for (let index = 0; index < 101; index++) {
    const id = `customer_attribute_${index}`;
    graph.nodes.push({ ...field, node_id: id, label: `attribute_${index}` });
    graph.mappings.push({ ...original, node_id: id, role: "attribute" });
  }
  const total = graph.mappings.filter((mapping) => mapping.entity_id === original.entity_id).length;
  const read = vi.spyOn(api, "detailedGraph").mockResolvedValue(value);
  render(<DetailedGraph canManage onChanged={() => {}} />);
  await act(async () => {});
  fireEvent.click(screen.getByRole("button", { name: "Business entities" }));
  fireEvent.click(screen.getByTestId("mapping-mongo_customers"));
  fireEvent.click(screen.getByRole("button", { name: "Inspect entity: Customer" }));
  const sources = within(screen.getByRole("region", { name: "Entity source mappings" }));
  expect(sources.getByText(`Showing 100 of ${total} source mappings`)).toBeVisible();
  expect(sources.queryByRole("button", { name: /attribute_100 · attribute/ })).toBeNull();
  fireEvent.click(sources.getByRole("button", { name: "Show more entity sources" }));
  expect(sources.getByText(`Showing ${total} of ${total} source mappings`)).toBeVisible();
  const last = sources.getByRole("button", { name: /Atlas \/ demo \/ customers \/ attribute_100 · attribute/ });
  expect(last).toBeVisible();
  // A same-entity refresh must not collapse the expanded source list.
  read.mockResolvedValue({ ...value, graph: { ...graph, revision: graph.revision + 1 } });
  await act(async () => { await vi.advanceTimersByTimeAsync(6000); });
  expect(screen.getByText(new RegExp(`Detailed graph v2 · revision ${graph.revision + 1}`))).toBeVisible();
  expect(sources.getByText(`Showing ${total} of ${total} source mappings`)).toBeVisible();
  fireEvent.click(sources.getByRole("button", { name: /attribute_100 · attribute/ }));
  expect(screen.getByText("Stable ID: customer_attribute_100")).toBeVisible();
  fireEvent.click(screen.getByRole("button", { name: "Inspect entity: Customer" }));
  expect(screen.getByText(`Showing 100 of ${total} source mappings`)).toBeVisible();
});

it.each([false, true])("navigates exact relationship fields while reviews stay disabled (stale=%s)", async (stale) => {
  const value = data();
  value.stale = stale;
  vi.spyOn(api, "detailedGraph").mockResolvedValue(value);
  render(<DetailedGraph canManage={stale} onChanged={() => {}} />);
  await screen.findByText(/Detailed graph v2/);
  const relationships = within(screen.getByRole("region", { name: "Qualified relationships" }));
  fireEvent.click(relationships.getAllByText(/proposed$/, { selector: "summary" })[0]!);
  expect(relationships.getAllByRole("button", { name: "Accept relationship" })[0]).toBeDisabled();
  fireEvent.click(relationships.getAllByRole("button", { name: "Postgres / demo / Postgres / orders / customerID" })[0]!);
  expect(screen.getByText("Stable ID: pg_orders_customerID")).toBeVisible();
  expect(screen.getByRole("button", { name: "Confirm mapping" })).toBeDisabled();
  fireEvent.click(relationships.getAllByRole("button", { name: "Atlas / demo / customers / customerID" })[0]!);
  expect(screen.getByText("Stable ID: mongo_customers_customerID")).toBeVisible();
  expect(screen.getByRole("button", { name: "Confirm mapping" })).toBeDisabled();
});
it("shows real containment and field metadata without changing IDs", async () => {
  vi.spyOn(api, "detailedGraph").mockResolvedValue(data());
  render(<DetailedGraph canManage onChanged={() => {}} />);
  fireEvent.click(await screen.findByRole("button", { name: "Expand Postgres" }));
  fireEvent.click(screen.getByRole("button", { name: "Expand demo" }));
  fireEvent.click(screen.getByRole("button", { name: "Expand Postgres" }));
  fireEvent.click(screen.getByRole("button", { name: "Expand Postgres.orders" }));
  fireEvent.click(screen.getByRole("button", { name: "customerID (field)" }));
  expect(screen.getByText("Stable ID: pg_orders_customerID")).toBeVisible();
  expect(screen.getByLabelText("Mapping role")).toHaveValue("reference");
});
it("saves an exact revision-bound business review and follows the shared entity", async () => {
  const saved = data();
  saved.graph!.revision = 2;
  saved.graph!.mappings.find((m) => m.node_id === "mongo_customers")!.status = "confirmed";
  const call = vi
    .spyOn(api, "detailedGraph")
    .mockResolvedValueOnce(data())
    .mockResolvedValue(saved);
  const changed = vi.fn();
  render(<DetailedGraph canManage onChanged={changed} />);
  fireEvent.click(await screen.findByRole("button", { name: "Business entities" }));
  fireEvent.click(screen.getByTestId("mapping-mongo_customers"));
  fireEvent.click(screen.getByRole("button", { name: "Confirm mapping" }));
  await waitFor(() =>
    expect(call).toHaveBeenCalledWith("mongo_customers", {
      revision: 1,
      entity_name: "Customer",
      role: "represents",
      status: "confirmed",
    }),
  );
  expect(changed).toHaveBeenCalledOnce();
  fireEvent.click(screen.getByRole("button", { name: "Inspect entity: Customer" }));
  expect(screen.getByRole("heading", { name: "Customer" })).toBeVisible();
  expect(screen.getAllByRole("button", { name: /customerID · reference/ }).length).toBeGreaterThan(
    0,
  );
});
it.each([false, true])("disables reviews for read-only or stale state (%s)", async (stale) => {
  const value = data();
  value.stale = stale;
  vi.spyOn(api, "detailedGraph").mockResolvedValue(value);
  render(<DetailedGraph canManage={stale} onChanged={() => {}} />);
  fireEvent.click(await screen.findByRole("button", { name: "Business entities" }));
  fireEvent.click(screen.getByTestId("mapping-mongo_customers"));
  expect(screen.getByRole("button", { name: "Confirm mapping" })).toBeDisabled();
});
it("filters business review state and resets focused exploration", async () => {
  const value = data();
  value.graph!.mappings.find((m) => m.node_id === "pg_orders")!.status = "needs_review";
  vi.spyOn(api, "detailedGraph").mockResolvedValue(value);
  render(<DetailedGraph canManage onChanged={() => {}} />);
  fireEvent.click(await screen.findByRole("button", { name: "Business entities" }));
  fireEvent.change(screen.getByLabelText("Mapping status"), { target: { value: "needs_review" } });
  expect(screen.getByRole("button", { name: /Order · represents.*needs_review/ })).toBeVisible();
  expect(screen.queryByTestId("mapping-mongo_customers")).not.toBeInTheDocument();
  fireEvent.click(screen.getByRole("button", { name: "Reset explorer" }));
  expect(screen.getByLabelText("Mapping status")).toHaveValue("all");
});
it("shows failures and retries instead of inventing graph contents", async () => {
  const call = vi
    .spyOn(api, "detailedGraph")
    .mockRejectedValueOnce(new Error("fixture failure"))
    .mockResolvedValue(data());
  render(<DetailedGraph canManage onChanged={() => {}} />);
  await waitFor(() => expect(call).toHaveBeenCalledOnce());
  expect(screen.queryByText(/Detailed graph v2/)).not.toBeInTheDocument();
  fireEvent.click(await screen.findByRole("button", { name: /Retry/ }));
  expect(await screen.findByText(/Detailed graph v2/)).toBeVisible();
});
it("searches all technical nodes and preserves declared versus unknown evidence", async () => {
  vi.spyOn(api, "detailedGraph").mockResolvedValue(data());
  render(<DetailedGraph canManage onChanged={() => {}} />);
  await screen.findByText(/Detailed graph v2/);
  fireEvent.change(screen.getByLabelText("Find graph items"), { target: { value: "orders" } });
  expect(screen.getByRole("button", { name: "Postgres.orders (dataset)" })).toBeVisible();
  expect(screen.getByText(/source_references_target/)).toBeInTheDocument();
  expect(screen.getAllByText(/Direction: unknown/).length).toBeGreaterThan(0);
});
it("reviews a relationship with the displayed revision and reloads its qualified evidence", async () => {
  vi.spyOn(api, "detailedGraph").mockResolvedValue(data());
  const review = vi
    .spyOn(api, "relationships")
    .mockResolvedValue({ graph: null, stale: false, build_status: "ready", last_error: null });
  render(<DetailedGraph canManage onChanged={() => {}} />);
  await screen.findByText(/Detailed graph v2/);
  fireEvent.click(screen.getAllByText(/proposed$/, { selector: "summary" })[0]!);
  fireEvent.click(screen.getAllByRole("button", { name: "Accept relationship" })[0]!);
  await waitFor(() =>
    expect(review).toHaveBeenCalledWith(
      "review",
      data().graph!.relationships.find((e) => e.kind === "suggested")!.relationship_id,
      { revision: 1, status: "accepted" },
    ),
  );
  expect(await screen.findByText(/Relationship review saved/)).toBeVisible();
});
