import { cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import { api } from "@/api/client";
import { plannedQuerySchema, selectionPreviewSchema } from "@/api/data-queries";
import fixture from "../../../e2e/fixtures/source-selection.json";
import SelectedSources from "./SelectedSources";
import DataQuestions from "./DataQuestions";

const preview = () => selectionPreviewSchema.parse(structuredClone(fixture));
afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
});

it("shows qualified source purposes, exact linking pairs and metadata limits", () => {
  render(<SelectedSources preview={preview()} />);
  expect(screen.getByLabelText("Selected graph subset")).toBeVisible();
  expect(screen.getByText(/1 catalog datasets are outside this plan/)).toBeVisible();
  const details = within(screen.getByRole("region", { name: "Selected source details" }));
  expect(details.getByText("Provides calculation fields.")).toBeVisible();
  expect(details.getByText(/orders \/ amount/).closest("li")).toHaveTextContent("metric");
  const joins = within(screen.getByRole("region", { name: "Selected linking fields" }));
  expect(
    joins.getByText(/orders \/ customer_id = Atlas \/ demo \/ customers \/ customer_id/),
  ).toBeVisible();
  fireEvent.change(screen.getByLabelText("Inspect selected dataset"), {
    target: { value: "customers" },
  });
  expect(details.getByText(/Confirmed concept: Customer/)).toBeVisible();
  fireEvent.keyDown(
    screen.getByRole("button", {
      name: "Inspect selected source: Supabase / demo / public / orders",
    }),
    { key: "Enter" },
  );
  expect(screen.getByLabelText("Inspect selected dataset")).toHaveValue("orders");
  fireEvent.click(screen.getByText("Metadata coverage warnings"));
  expect(screen.getByText("Atlas fields were discovered by sampling.")).toBeVisible();
});

it.each(["postgresql", "mongodb"] as const)(
  "renders a single %s source without invented joins",
  (engine) => {
    const value = preview();
    value.sources = value.sources.filter((source) => source.engine === engine);
    value.relationships = [];
    render(<SelectedSources preview={value} />);
    expect(screen.getByText("Selected sources (1)")).toBeVisible();
    expect(screen.getByText("Single dataset; no relationship join is planned.")).toBeVisible();
  },
);

it("keeps selection until execution and clears previews when the question changes", async () => {
  vi.spyOn(api, "dataQueryStatus").mockResolvedValue({
    configured: true,
    max_rows_per_dataset: 5000,
    max_bytes: 2000000,
    max_datasets: 4,
    max_result_rows: 500,
    plan_ttl_seconds: 600,
  });
  const planned = plannedQuerySchema.parse({
    plan_id: "dq_selection",
    question: "Sales by customer",
    graph_revision: 1,
    created_at: "2026-10-18T00:00:00Z",
    expires_at: 2000000000,
    field_labels: {},
    dataset_labels: {},
    selection_preview: preview(),
    plan: {
      base_dataset_id: "orders",
      joins: [{ relationship_id: "orders_customers", target_dataset_id: "customers" }],
      fields: [],
      filters: [],
      group_by: ["customer_name"],
      metrics: [{ label: "sales", op: "sum", expression: "order_amount" }],
      order_by: [],
      limit: 100,
      explanation: "Sum order amounts by customer name.",
      clarification: "",
    },
  });
  const plan = vi.spyOn(api, "planDataQuestion").mockResolvedValue(planned);
  const execute = vi.spyOn(api, "executeDataQuestion").mockResolvedValue({
    plan_id: planned.plan_id,
    executed_plan: planned.plan,
    columns: [],
    rows: [],
    total_result_rows: 0,
    matched_rows: 0,
    limited: false,
    executed_at: "2026-10-18T00:00:01Z",
    explanation: planned.plan.explanation,
    warnings: [],
    join_checks: [],
    sources: [],
  });
  render(<DataQuestions canManage />);
  fireEvent.change(screen.getByLabelText("Your data question"), {
    target: { value: "Sales by customer" },
  });
  await waitFor(() =>
    expect(screen.getByRole("button", { name: "Create query plan" })).toBeEnabled(),
  );
  fireEvent.click(screen.getByRole("button", { name: "Create query plan" }));
  expect(await screen.findByText("Selected sources (2)")).toBeVisible();
  expect(execute).not.toHaveBeenCalled();
  fireEvent.click(screen.getByRole("button", { name: "Run read-only query" }));
  expect(await screen.findByText("Executed logical read plan", { exact: true })).toBeVisible();
  fireEvent.click(screen.getByText("Executed logical read plan", { exact: true }));
  expect(screen.getByLabelText("Executed logical query")).toHaveTextContent("order_amount");
  fireEvent.change(screen.getByLabelText("Your data question"), {
    target: { value: "Something else" },
  });
  expect(screen.queryByText("Selected sources (2)")).toBeNull();
  plan.mockResolvedValue({
    ...planned,
    plan: { ...planned.plan, clarification: "Which customer population?" },
  });
  fireEvent.click(screen.getByRole("button", { name: "Create query plan" }));
  expect(await screen.findByText("Which customer population?")).toBeVisible();
  expect(screen.queryByRole("region", { name: "Selected sources" })).toBeNull();
  expect(execute).toHaveBeenCalledOnce();
});
