import { displayText } from "@/lib/display-text";
import { ProcurementProjectCommunication } from './ProcurementProjectCommunication';
import { CommunicationDiagram } from './CommunicationDiagram';
import { workflowDiagram } from '@/domain/communication-diagram';
import type { Workflow, Agent } from "@/domain/types";
import { Link } from "@/lib/navigation";
export function HierarchyView({
  workflow,
  agents,
  onEdit,
}: {
  workflow: Workflow;
  agents: Agent[];
  onEdit: (id: string) => void;
}) {
  if (workflow.canonical?.metadata['procurement_plan']) return <ProcurementProjectCommunication workflowId={workflow.id} version={workflow.serverVersion??1} view="hierarchy"/>;
  const definitions = workflow.canonical?.agents ?? [];
  const definitionIds = new Set(definitions.map((a) => `${workflow.id}::${a.agent_id}`));
  const rows = [
    ...definitions.map((definition) => ({
      id: `${workflow.id}::${definition.agent_id}`,
      definition,
      node: workflow.nodes.find((n) => n.data.agentId === `${workflow.id}::${definition.agent_id}`),
    })),
    ...workflow.nodes
      .filter((n) => n.data.kind === "agent" && !definitionIds.has(n.data.agentId ?? ""))
      .map((node) => ({ id: node.data.agentId ?? node.id, definition: undefined, node })),
  ];
  return (
    <section aria-label="Agent hierarchy" className="flex h-full min-h-0 flex-col">
      <div className="flex min-h-0 flex-1"><CommunicationDiagram model={workflowDiagram(workflow,[])}/></div>
      <details className="max-h-80 overflow-y-auto border-t bg-background p-4"><summary className="cursor-pointer text-sm font-medium">Agent responsibilities and configuration</summary>
      <h2 className="font-semibold">Agent hierarchy</h2>
      <p className="my-2 text-sm text-muted-foreground">
        Parent links describe delegation intent. Execution dependencies are shown separately in
        Design. Presentation-only hierarchy links do not create runtime delegation; executable
        delegation requires a supported canonical node configuration and server validation.
      </p>
      {!rows.length ? (
        <p>No agents are defined. Add an AI agent in Design if this process requires one.</p>
      ) : (
        <ul className="space-y-3">
          {rows.map((row) => {
            const agent = agents.find((a) => a.id === row.id);
            const definition = row.definition;
            const parentDefinition = definitions.find(
              (a) => a.agent_id === definition?.parent_agent_id,
            );
            const parentNode = workflow.nodes.find((p) => p.id === row.node?.data.parentNodeId);
            const parent = parentDefinition?.role ?? parentNode?.data.label;
            const role =
              definition?.hierarchy_role === "master" || row.node?.data.role === "master"
                ? "Master"
                : parent || definition?.hierarchy_role === "sub_agent"
                  ? "Delegated"
                  : "Independent";
            const parentMasterNode = workflow.nodes.find(
              (n) => n.data.agentId === `${workflow.id}::${parentDefinition?.agent_id}`,
            );
            const configured =
              !!parentMasterNode &&
              !!(
                workflow.canonical?.metadata["dynamic_delegation"] as
                  Record<string, unknown> | undefined
              )?.[parentMasterNode.id];
            return (
              <li
                key={row.id}
                className="rounded-xl border border-border bg-background p-4"
                style={{ marginLeft: parent ? 12 : 0 }}
              >
                <h3 className="font-medium">
                  {role} · {displayText(agent?.name ?? definition?.role ?? row.node?.data.label)}
                </h3>
                <p className="text-sm">
                  Parent: {parent ?? "None declared"}
                  {(definition?.parent_agent_id || row.node?.data.parentNodeId) && !parent
                    ? " · invalid parent reference"
                    : ""}
                </p>
                <p className="mt-1 text-sm">
                  Responsibility:{" "}
                  {displayText(agent?.purpose ||
                    definition?.goal ||
                    row.node?.data.description ||
                    "Needs configuration")}
                </p>
                <p className="mt-1 text-xs text-muted-foreground">
                  Agent configuration: {agent ? "Defined; server validation required" : "Missing"} ·
                  Tools: {agent?.tools.join(", ") || "No reviewed tool grants"}
                </p>
                <p className="mt-1 text-xs text-muted-foreground">
                  {row.node
                    ? "Has an execution graph step."
                    : configured
                      ? "Specialist template; runtime delegation configured on its master. Selection depends on recorded runtime decisions."
                      : "Specialist template; no supported runtime delegation configured. This relationship alone is non-executable."}
                </p>
                {row.node ? (
                  <button
                    type="button"
                    onClick={() => onEdit(row.node!.id)}
                    className="mt-2 rounded-lg border border-border px-3 py-1.5 text-sm"
                  >
                    Edit in Design
                  </button>
                ) : agent ? (
                  <Link
                    to="/app/agents"
                    search={{ agent: agent.id }}
                    className="mt-2 inline-block rounded-lg border border-border px-3 py-1.5 text-sm"
                  >
                    Edit agent configuration
                  </Link>
                ) : null}
              </li>
            );
          })}
        </ul>
      )}
      </details>
    </section>
  );
}
