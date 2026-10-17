import { afterEach, expect, it } from "vitest";
import { cleanup, render, screen } from "@testing-library/react";
import { SheetAccessReview } from "./SheetAccessReview";

afterEach(cleanup);

it("shows per-workflow spreadsheet scope and creation permissions for review", () => {
  render(<SheetAccessReview targets={[
    { spreadsheet_id: "restaurant-sheet", range: "Reviews!A1:F1000", identity_column: "review_id", writable_columns: ["status"], allow_create: false },
    { spreadsheet_id: "factory-sheet", range: "Followups!A1:F1000", identity_column: "case_id", writable_columns: ["draft", "findings"], allow_create: true },
  ]} />);
  expect(screen.getByText("Sheet write access")).toBeInTheDocument();
  expect(screen.getByText(/Review these destinations before approving and publishing/)).toBeInTheDocument();
  expect(screen.getByRole("link", { name: "factory-sheet", hidden: true })).toHaveAttribute("href", "https://docs.google.com/spreadsheets/d/factory-sheet/edit");
  expect(screen.getByText("Writable columns: status")).toBeInTheDocument();
  expect(screen.getByText("Existing records only")).toBeInTheDocument();
  expect(screen.getByText("Can create missing records")).toBeInTheDocument();
});

it("shows incomplete access as an error without rendering arbitrary values", () => {
  render(<SheetAccessReview targets={[{ spreadsheet_id: { invalid: true } }]} />);
  expect(screen.getByRole("alert", { hidden: true })).toHaveTextContent("Sheet access is incomplete");
  expect(screen.queryByRole("link", { hidden: true })).not.toBeInTheDocument();
});

it("does not show a write access control for read-only workflows", () => {
  const { container } = render(<SheetAccessReview targets={undefined} />);
  expect(container).toBeEmptyDOMElement();
});
