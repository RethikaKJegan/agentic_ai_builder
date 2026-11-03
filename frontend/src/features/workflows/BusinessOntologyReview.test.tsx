import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import type { CanonicalWorkflow } from "@/api/contracts.generated";
import { BusinessOntologyReview } from "./BusinessOntologyReview";

afterEach(() => { cleanup(); vi.restoreAllMocks(); });
const trace = {
  retrieval_version: "simpson-business-planning-v1", state: "incorporated", version_id: "bov_saved", revision: 4,
  definition_sha256: "a".repeat(64), trace_sha256: "b".repeat(64), truncated: false,
  references: [{ ref: "policy:cnhtest", kind: "policy", label: "CNH supplied implementation", definition: "Check invoice, sale and operating hours together.", interpretation_basis: "descriptive_implementation", evidence: [{ source_id: "source_saved", title: "Supplied warranty service", source_kind: "application_code", source_sha256: "c".repeat(64), quote: "hours <= 2000" }] }],
  contributions: [{ node_id: "check_warranty", node_name: "Check warranty", refs: ["policy:cnhtest"], application: "Adds the operating-hours check to warranty assessment." }],
};
function doc(overrides = {}) { return { workflow_id: "test_workflow", metadata: { business_ontology: { ...trace, ...overrides } }, nodes: [{ node_id: "check_warranty", label: "Assess warranty", kind: "agent" }] } as unknown as CanonicalWorkflow; }
it("shows step-level evidence and distinguishes application code from policy", () => {
  render(<BusinessOntologyReview document={doc()} />);
  expect(screen.getByText(/Business knowledge version 4/)).toBeInTheDocument();
  expect(screen.getByRole("heading", { name: "Assess warranty" })).toBeInTheDocument();
  expect(screen.getByText(/Adds the operating-hours check/)).toBeInTheDocument();
  fireEvent.click(screen.getByText(/View supporting sources/));
  expect(screen.getByText("hours <= 2000")).toBeVisible();
  expect(screen.getByText(/not verified written policy/)).toBeVisible();
});
it.each(["not_configured", "no_match", "no_definitions", "not_authorized"])("does not claim incorporation for %s", state => {
  render(<BusinessOntologyReview document={doc({ state, contributions: [], references: [] })} />);
  expect(screen.queryByText(/informed 1 proposed/)).not.toBeInTheDocument();
  expect(screen.getByRole("status")).toBeVisible();
});
it("shows an unreadable trace without claiming success", () => {
  render(<BusinessOntologyReview document={doc({ state: "invented" })} />);
  expect(screen.getByRole("status")).toHaveTextContent("No incorporation claim");
});
it("preserves the historical contribution after its step is removed", () => {
  render(<BusinessOntologyReview document={{ ...doc(), nodes: [] }} />);
  expect(screen.getByRole("status")).toHaveTextContent("since been removed");
});
it("exports the full original trace including source provenance", () => {
  const create = vi.fn(() => "blob:evidence");
  Object.defineProperty(URL, "createObjectURL", { configurable: true, value: create });
  vi.spyOn(HTMLAnchorElement.prototype, "click").mockImplementation(() => {});
  render(<BusinessOntologyReview document={doc()} />);
  fireEvent.click(screen.getByRole("button", { name: "Download ontology evidence" }));
  expect(create).toHaveBeenCalledOnce();
  expect(create.mock.calls[0]).toHaveLength(1);
});
it("does not invent evidence for an older workflow", () => {
  const { container } = render(<BusinessOntologyReview document={{ ...doc(), metadata: {} }} />);
  expect(container).toBeEmptyDOMElement();
});

it("shows business meaning first while hiding source IDs and hashes", () => {
  render(<BusinessOntologyReview document={doc()} />);
  expect(screen.getByText("Check invoice, sale and operating hours together.")).toBeVisible();
  for (const detail of screen.getAllByText(/SHA-256:/)) expect(detail).not.toBeVisible();
  expect(screen.getByText(/Source: source_saved/)).not.toBeVisible();
  fireEvent.click(screen.getByText(/View supporting sources/));
  expect(screen.getByText("hours <= 2000")).toBeVisible();
  for (const detail of screen.getAllByText(/SHA-256:/)) expect(detail).not.toBeVisible();
  fireEvent.click(screen.getByText("Technical source details"));
  expect(screen.getByText(/Source: source_saved/)).toBeVisible();
});
it("renders camel case business terms as words", () => {
  const d=doc();
  (d.metadata["business_ontology"] as typeof trace).references[0]!.label="ReportedSymptom";
  render(<BusinessOntologyReview document={d} />);
  expect(screen.getByRole("heading",{name:"Reported Symptom"})).toBeVisible();
});
