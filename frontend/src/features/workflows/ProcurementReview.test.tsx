import { afterEach, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { ProcurementReview } from "./ProcurementReview";
import type { Workflow } from "@/domain/types";
import { api, ApiError } from "@/api/client";
vi.mock("@/api/state", () => ({ useBackend: () => ({ overview: { workflow_demo: { published_version: 1 } }, can: () => true, initialize: vi.fn().mockResolvedValue(undefined) }) }));

afterEach(() => { cleanup(); vi.restoreAllMocks(); });
const plan = { project_id: "project_demo", name: "Workshop procurement", simulation: true,
  context: { delivery_location: "Chennai", delivery_deadline: null, quote_deadline: null, time_zone: "Asia/Kolkata", comparison_currency: "INR" },
  requirements: { spreadsheet_url: "https://docs.google.com/spreadsheets/d/req/edit", range: "Items!A1:F101", columns: { item_id: "Reference", quantity: "Amount" } },
  vendors: { spreadsheet_url: "https://docs.google.com/spreadsheets/d/vendors/edit", range: "Contacts!A1:D101", columns: { email: "Contact Email" } } };
const workflow = { id: "workflow_demo", serverVersion: 1, canonical: { status: "published", metadata: { procurement_plan: plan } } } as unknown as Workflow;

it("reviews actual project mappings and leaves missing context visible", () => {
  render(<ProcurementReview workflow={workflow} />);
  fireEvent.click(screen.getByText("Procurement setup & status"));
  expect(screen.getByDisplayValue("Contact Email")).toBeDisabled();
  expect(screen.getByDisplayValue("Amount")).toBeDisabled();
  expect(screen.queryByText("Save project settings")).not.toBeInTheDocument();
  expect(screen.getByText(/each spreadsheet write, Gmail draft and RFQ send/i)).toBeInTheDocument();
});

it("shows actual phase, counts, run references and resource link", async () => {
  vi.spyOn(api, "procurementStatus").mockResolvedValue({ project_id: "project_demo", phase: "SENDING", issues: [], candidates: [],
    record_counts: { boq_item: 4, rfq: 4 }, resources: [{ provider: "google_sheets", resource_type: "spreadsheet", resource_id: "tracking_book", metadata: {} }],
    actions: { send_vendor: { workflow_id: "send_workflow", state: "paused_for_approval", run_id: "run_demo" } } });
  render(<ProcurementReview workflow={workflow} />);
  fireEvent.click(screen.getByText("Procurement setup & status"));
  fireEvent.click(screen.getByText("Refresh project status"));
  await waitFor(() => expect(screen.getByText("SENDING")).toBeInTheDocument());
  expect(screen.getByText(/run_demo/)).toBeInTheDocument();
  expect(screen.getByRole("link", { name: "Open tracking spreadsheet" })).toHaveAttribute("href", "https://docs.google.com/spreadsheets/d/tracking_book/edit");
});

it("leaves ordinary workflows without a procurement panel", () => {
  const { container } = render(<ProcurementReview workflow={{ id: "ordinary" } as Workflow} />);
  expect(container).toBeEmptyDOMElement();
});

it("starts the published revision directly with no spreadsheet trigger input", async () => {
  const request = vi.spyOn(api, "request").mockResolvedValue({ run: { run_id: "run_start", workflow_id: "workflow_demo", workflow_version: 1, status: "completed", approvals: [] } });
  vi.spyOn(api, "procurementStatus").mockResolvedValue({ project_id: "project_demo", phase: "TRACKING", issues: [], candidates: [], record_counts: {}, resources: [], actions: {} });
  render(<ProcurementReview workflow={workflow} />);
  fireEvent.click(screen.getByText("Procurement setup & status"));
  fireEvent.click(screen.getByText("Start procurement"));
  await waitFor(() => expect(request).toHaveBeenCalledWith("execute_workflow", { workflow_id: "workflow_demo", workflow_version: 1, inputs: {} }, expect.any(String)));
  expect(screen.getByText(/No new spreadsheet row is needed/)).toBeInTheDocument();
});

it("reviews candidate evidence and keeps unknown emails unselectable", async () => {
  vi.spyOn(api, "procurementStatus").mockResolvedValue({ project_id: "project_demo", phase: "SHORTLIST_REVIEW", issues: [],
    candidates: [{ candidate_id: "supplier_a", name: "Supplier A", email: "sales@example.com", categories: ["Equipment"],
      assessment: "Published products; delivery unknown", contact_state: "PUBLISHED", evidence: [{ url: "https://example.com", quote: "Equipment", content_sha256: "hash" }] },
      { candidate_id: "supplier_b", name: "Supplier B", email: null, categories: ["Equipment"], assessment: "No contact", contact_state: "MISSING_EMAIL", evidence: [] }],
    shortlist_digest: "current_digest", record_counts: {}, resources: [], actions: {} });
  const review = vi.spyOn(api, "procurementSuppliersReview").mockResolvedValue({});
  render(<ProcurementReview workflow={workflow} />);
  fireEvent.click(screen.getByText("Procurement setup & status")); fireEvent.click(screen.getByText("Refresh project status"));
  await waitFor(() => expect(screen.getByLabelText("Supplier B")).toBeDisabled());
  fireEvent.click(screen.getByLabelText("Supplier A")); fireEvent.click(screen.getByText("Approve selected suppliers"));
  await waitFor(() => expect(review).toHaveBeenCalledWith("project_demo", "approved", ["supplier_a"], "current_digest"));
});

it("shows a ready-to-start state when the project has not been created", async () => {
  vi.spyOn(api, "procurementStatus").mockRejectedValue(new ApiError({ error_code: "PROCUREMENT_PROJECT_NOT_FOUND", message: "Not found", request_id: "req_test", retryable: false }));
  render(<ProcurementReview workflow={workflow} />);
  fireEvent.click(screen.getByText("Refresh project status"));
  await waitFor(() => expect(screen.getByText(/Ready to start/)).toBeInTheDocument());
  expect(screen.queryByRole("alert")).not.toBeInTheDocument();
});
