import { render, screen } from "@testing-library/react";
import { expect, it, vi } from "vitest";
import { api } from "@/api/client";
import type { CanonicalWorkflow, RunEvent } from "@/api/contracts.generated";
import type { ProjectCommunication } from "@/domain/procurement-communication";
import fixture from "../../../e2e/fixtures/multitask-delegation.json";
vi.mock("./CommunicationDiagram", () => ({
  DiagramLegend: () => null,
  CommunicationDiagram: ({
    model,
  }: {
    model: import("@/domain/communication-diagram").DiagramModel;
  }) => (
    <div>
      {model.cards.map((card) => (
        <div key={card.id}>
          {card.label}
          {card.spawned && <span>Spawned helper</span>}
        </div>
      ))}
    </div>
  ),
}));
import { ProcurementProjectCommunication } from "./ProcurementProjectCommunication";

it("opens project actions with their actual names and explains helper exchanges through the shared view", async () => {
  const actionWorkflow = {
    ...fixture.workflow,
    name: "Review incoming documents",
  } as CanonicalWorkflow;
  const project = {
    project_id: "test",
    phase: "ACTIVE",
    root_workflow: { ...actionWorkflow, name: "Document processing" },
    configured_workflow: null,
    truncated: false,
    actions: [
      {
        key: "send_internal_id",
        workflow: actionWorkflow,
        run: fixture.runs[0]!.run,
        events: fixture.runs[0]!.events as RunEvent[],
      },
    ],
  } as ProjectCommunication;
  const spy = vi.spyOn(api, "procurementProjectCommunication").mockResolvedValue(project);
  const view = render(<ProcurementProjectCommunication workflowId="root" version={1} />);
  expect(await screen.findByText("Review incoming documents")).toBeInTheDocument();
  expect(screen.getAllByText("Spawned helper")).toHaveLength(3);
  expect(screen.queryByText("Send RFQs")).not.toBeInTheDocument();
  expect(screen.queryByRole("button", { name: "Step-by-step" })).not.toBeInTheDocument();
  view.unmount();
  spy.mockRestore();
});
