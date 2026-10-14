import { render, screen } from "@testing-library/react";
import { expect, it } from "vitest";
import { ReadableEvidence } from "./CommunicationEvidence";
it("keeps false, zero and missing evidence distinct in the inspector", () => {
  render(<ReadableEvidence value={{ quantity: 0, accepted: false, missing: null }} />);
  expect(screen.getByText("0")).toBeInTheDocument();
  expect(screen.getByText("No")).toBeInTheDocument();
  expect(screen.getByText("Not supplied")).toBeInTheDocument();
});
