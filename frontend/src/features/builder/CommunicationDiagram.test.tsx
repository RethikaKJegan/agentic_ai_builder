import { render } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import { Position } from "@xyflow/react";
import { Connection } from "./CommunicationDiagram";

vi.mock("@xyflow/react", async importOriginal => ({
  ...await importOriginal<typeof import("@xyflow/react")>(),
  EdgeLabelRenderer: () => null,
}));
afterEach(() => vi.restoreAllMocks());

it("renders the actual SVG path without forwarding React Flow internals to the DOM", () => {
  const errors = vi.spyOn(console, "error").mockImplementation(() => {});
  const props = {
    id: "connection", source: "coordinator", target: "helper",
    sourceX: 0, sourceY: 0, targetX: 120, targetY: 120,
    sourcePosition: Position.Bottom, targetPosition: Position.Top,
    sourceHandleId: "out", targetHandleId: "in", animated: false,
    selectable: true, deletable: true, pathOptions: { offset: 20 },
    style: { stroke: "#16a34a", strokeWidth: 2.5 }, markerEnd: "url(#arrow)",
  } as Parameters<typeof Connection>[0];
  const view = render(<svg><Connection {...props} /></svg>);
  const path = view.container.querySelector(".react-flow__edge-path")!;
  expect(path).toHaveAttribute("marker-end", "url(#arrow)");
  expect(path).toHaveStyle({ stroke: "#16a34a", strokeWidth: 2.5 });
  for (const key of ["animated", "selectable", "deletable", "sourceX", "sourceY", "targetX", "targetY", "sourcePosition", "targetPosition", "sourceHandleId", "targetHandleId", "pathOptions"])
    expect(path).not.toHaveAttribute(key);
  expect(errors).not.toHaveBeenCalled();
});
