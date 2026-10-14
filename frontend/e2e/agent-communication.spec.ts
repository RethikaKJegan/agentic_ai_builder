import { test, expect } from "@playwright/test";
import fs from "node:fs";
import path from "node:path";

for (const mobile of [false, true]) {
  test(`master and sub-agent UUID diagram inspects handoffs and historical revisions on ${mobile ? "mobile" : "desktop"}`, async ({
    page,
  }) => {
    if (mobile) await page.setViewportSize({ width: 390, height: 844 });
    const errors: string[] = [];
    page.on("pageerror", error => errors.push(error.message));
    const workflow = JSON.parse(
      fs.readFileSync(
        path.resolve(
          import.meta.dirname,
          "../../shared/contracts/examples/workflows/support-triage.json",
        ),
        "utf8",
      ),
    );
    const definition = JSON.parse(
      fs.readFileSync(
        path.resolve(
          import.meta.dirname,
          "../../shared/contracts/examples/agents/valid-classifier.json",
        ),
        "utf8",
      ),
    );
    delete definition.name;
    delete definition.retry_policy;
    delete definition.guardrails;
    workflow.workflow_id = "wf_hierarchy_communication";
    workflow.version = 2;
    workflow.metadata.workspace_id = "local-workspace";
    workflow.agents = [
      { ...definition, agent_id: "master_agent", hierarchy_role: "master" },
      {
        ...definition,
        agent_id: "research_agent",
        hierarchy_role: "sub_agent",
        parent_agent_id: "master_agent",
      },
      {
        ...definition,
        agent_id: "analysis_agent",
        hierarchy_role: "sub_agent",
        parent_agent_id: "master_agent",
      },
    ];
    workflow.nodes = [
      { node_id: "start", kind: "trigger", label: "Request received", layout: { x: 0, y: 100 } },
      {
        node_id: "master",
        kind: "agent",
        label: "Master orchestrator",
        agent_id: "master_agent",
        layout: { x: 320, y: 100 },
      },
      {
        node_id: "research",
        kind: "agent",
        label: "Research specialist",
        agent_id: "research_agent",
        layout: { x: 640, y: 100 },
      },
      {
        node_id: "analysis",
        kind: "agent",
        label: "Analysis specialist",
        agent_id: "analysis_agent",
        layout: { x: 960, y: 100 },
      },
      { node_id: "finish", kind: "output", label: "Combined result", layout: { x: 1280, y: 100 } },
    ];
    workflow.edges = [
      { edge_id: "start_to_master", source: "start", target: "master" },
      { edge_id: "master_to_research", source: "master", target: "research" },
      { edge_id: "research_to_analysis", source: "research", target: "analysis" },
      { edge_id: "analysis_to_finish", source: "analysis", target: "finish" },
    ];
    workflow.conditions = [];
    workflow.approval_gates = [];
    const previous = structuredClone(workflow);
    previous.version = 1;
    previous.nodes = previous.nodes.filter(
      (node: { node_id: string }) => node.node_id !== "analysis",
    );
    previous.agents = previous.agents.filter(
      (agent: { agent_id: string }) => agent.agent_id !== "analysis_agent",
    );
    previous.edges = previous.edges.filter(
      (edge: { source: string; target: string }) =>
        edge.source !== "analysis" && edge.target !== "analysis",
    );
    previous.edges.push({ edge_id: "research_to_finish", source: "research", target: "finish" });
    const runs = [2, 1].map((version) => ({
      run_id: `run_hierarchy_v${version}`,
      workflow_id: workflow.workflow_id,
      workflow_version: version,
      status: "completed",
      approvals: [],
    }));
    const events = (run: (typeof runs)[number]) =>
      [
        {
          event_type: "node.observed",
          details: {
            node_id: "research",
            invocation_id: "aaaaaaaa-bbbb-4ccc-8ddd-eeeeeeeeeeee",
            observation: { task: "Collect supporting facts" },
          },
        },
        {
          event_type: "node.handoff",
          details: {
            node_id: "research",
            source_node_id: "master",
            target_node_id: "research",
            edge_id: "master_to_research",
            handoff_id: "11111111-2222-4333-8444-555555555555",
            transfer_kind: "mapped_data",
            stage: "inputs_prepared",
            source_agent_id: "master_agent",
            target_agent_id: "research_agent",
            target_invocation_id: "aaaaaaaa-bbbb-4ccc-8ddd-eeeeeeeeeeee",
            input_mapping: { task: "outputs.master.task" },
            mapped_fields: { task: "Collect supporting facts" },
            receiver_input: { task: "Collect supporting facts" },
            source_output: { task: "Collect supporting facts" },
          },
        },
        {
          event_type: "node.completed",
          details: { node_id: "master", selected_edges: ["master_to_research"] },
        },
        {
          event_type: "node.completed",
          details: {
            node_id: "research",
            invocation_id: "aaaaaaaa-bbbb-4ccc-8ddd-eeeeeeeeeeee",
            output: { result: "Evidence collected" },
            selected_edges: [
              run.workflow_version === 1 ? "research_to_finish" : "research_to_analysis",
            ],
          },
        },
      ].map((event, i) => ({
        ...event,
        event_id: `${run.run_id}_${i}`,
        run_id: run.run_id,
        workflow_id: run.workflow_id,
        workflow_version: run.workflow_version,
        timestamp: `2026-10-11T10:00:0${i}Z`,
        source: "runtime",
      }));
    await page.route("**/api/backend/**", async (route) => {
      const url = new URL(route.request().url());
      const destination = url.pathname.replace("/api/backend/", "");
      const collection = { items: [], total: 0, has_more: false, next_cursor: null };
      let data: unknown = collection;
      if (destination === "session")
        data = {
          mode: "local-development",
          planning_available: false,
          runtime_available: true,
          approval_service_available: true,
          auth: {
            subject: { subject_id: "operator", workspace_id: "local-workspace" },
            roles: ["admin"],
            permissions: ["workflow.view", "runs.view"],
            scopes: ["workspace:read"],
            decision: "allow",
          },
        };
      else if (destination.startsWith("workflow-overview"))
        data = { items: [], next_sequence: 0, has_more: false };
      else if (destination === "workflows") data = { ...collection, items: [workflow], total: 1 };
      else if (destination.startsWith("workflows/"))
        data = { workflow: url.searchParams.get("version") === "1" ? previous : workflow };
      else if (destination === "runs") data = { ...collection, items: runs, total: runs.length };
      else if (destination.endsWith("/events")) {
        const run = runs.find((run) => destination === `runs/${run.run_id}/events`)!;
        data = { ...collection, items: events(run), total: 4 };
      } else if (destination.startsWith("runs/"))
        data = { run: runs.find((run) => destination === `runs/${run.run_id}`) };
      await route.fulfill({ json: { request_id: "req_communication_test", status: 200, data } });
    });
    await page.goto(`/app/workflows/${workflow.workflow_id}`);
    await expect(page.getByLabel("Select workflow run")).toHaveValue("run_hierarchy_v2");
    await page.getByRole("button", { name: "Agent communication", exact: true }).click();
    const dialog = page.getByRole("dialog", { name: "Agent communication", exact: true });
    await expect(dialog.getByRole("button", { name: "Step-by-step" })).toHaveCount(0);
    await expect(dialog.getByLabel("Agent communication diagram")).toBeVisible();
    const clickAgent = async () => dialog.locator('.react-flow__node[data-id="run_hierarchy_v2:research"]').click();
    await clickAgent();
    const inspector = dialog.getByLabel("Agent details");
    await expect(inspector.getByRole("heading", { name: "Research specialist", exact: true })).toBeVisible();
    await expect(inspector.getByText("Result", { exact: true })).toBeVisible();
    await expect(inspector.getByText(/Evidence collected/).first()).toBeVisible();
    await inspector.getByText("Technical details", { exact: true }).click();
    await expect(inspector.getByText("research_agent", { exact: true })).toBeVisible();
    const firstUuid = await inspector.locator("details dl dd").first().innerText();
    expect(firstUuid).toMatch(/^[0-9a-f-]{36}$/);
    await inspector.getByRole("button", { name: "Close details" }).click();
    await dialog.getByRole("button", { name: "Information shared", exact: true }).first().click();
    await expect(inspector.getByText("Information shared", { exact: true }).last()).toBeVisible();
    await inspector.getByRole("button", { name: "Close details" }).click();
    await dialog.getByLabel("Communication run").selectOption("run_hierarchy_v1");
    await expect(dialog.getByText("Recorded run · v1", { exact: true })).toBeVisible();
    await expect(dialog.getByText("Analysis specialist", { exact: true })).toHaveCount(0);
    await dialog.locator('.react-flow__node[data-id="run_hierarchy_v1:research"]').click();
    await inspector.getByText("Technical details", { exact: true }).click();
    await expect(inspector.locator("details dl dd").first()).toHaveText(firstUuid);
    await inspector.getByRole("button", { name: "Close details" }).click();
    await dialog.getByLabel("View", { exact: true }).selectOption("configured");
    await expect(dialog.getByText("Analysis specialist", { exact: true })).toBeVisible();
    await expect(dialog.getByText(/^Spawned · Task/)).toHaveCount(0);
    await dialog.getByRole("button", { name: "Available helper", exact: true }).first().click();
    await expect(inspector.getByText(/No information exchange has been recorded/)).toBeVisible();
    expect(errors).toEqual([]);
  });
}
