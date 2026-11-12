import { beforeEach, afterEach, it, expect, vi } from "vitest";
import { render, screen, fireEvent, waitFor, cleanup, act } from "@testing-library/react";
import { webcrypto } from "node:crypto";
import { api, ApiError } from "@/api/client";
import { useBackend } from "@/api/state";
import {
  actionDocumentSchema,
  automationSchema,
  adaptiveSchema,
  receiptLinks,
} from "@/api/orchestration";
import { caseSchema } from "@/api/business-lifecycle";
import { compositionViewSchema } from "@/api/compositions";
import fixture from "@/test/fixtures/orchestration.json";
import actualView from "@/test/fixtures/connected-plan-view.json";
import { dynamicView } from "../../../e2e/fixtures/dynamic-investigation";
import { ConnectedPlan } from "./ConnectedPlan";
import { AdaptiveCasePanel } from "./AdaptiveCasePanel";
import { AutomationPanel } from "./DurableAutomation";
import { commandKey, useOrchestrationCommand } from "./useOrchestrationCommand";
const doc = () => actionDocumentSchema.parse(structuredClone(fixture.document));

it('keeps automation diagnostics in Background while confirming delivered email',async()=>{
 const current=view();
 current.run!.status='blocked';current.run!.error_code='ADAPTIVE_FALSE_COMPLETION';
 current.run!.action_instances={sent:{state:'completed',verified_receipt:true,output:{message_id:'synthetic-confirmed'}}};
 vi.spyOn(api,'actionPlan').mockResolvedValue(doc());vi.spyOn(api,'compositionView').mockResolvedValue(current);
 render(<ConnectedPlan id={doc().composition_id} scheduled/>);
 expect(await screen.findByText('Email sent. This run needs attention.')).toBeVisible();
 expect(screen.queryByText(/Execution: ADAPTIVE_FALSE_COMPLETION/)).not.toBeInTheDocument();
 fireEvent.click(screen.getByRole('button',{name:'View execution details'}));
 expect(screen.getByRole('tab',{name:'Background'})).toHaveAttribute('aria-selected','true');
 expect(screen.getByText('Execution diagnostics')).toBeVisible();
});
const saved = () => caseSchema.parse(structuredClone(fixture.case));
const view = () =>
  compositionViewSchema.parse({
    ...dynamicView(),
    composition_id: doc().composition_id,
    planning: { mode: "action_plan", model_calls: 1 },
    run: { ...dynamicView("completed").run, ...fixture.run, error_code: null },
    tasks: doc().action_plan.actions.map((a) => ({
      ...dynamicView().tasks[0],
      id: a.action_id,
      capability_id: a.capability_id,
      depends_on: a.depends_on,
      agent_id: "actual_agent",
      tools: doc().selected_tools[a.action_id] ? [doc().selected_tools[a.action_id]!.tool_id] : [],
    })),
  });
beforeEach(() => {
  vi.restoreAllMocks();
  sessionStorage.clear();
  Object.defineProperty(globalThis, "crypto", { configurable: true, value: webcrypto });
  useBackend.setState({
    status: "connected",
    session: {
      mode: "local-development",
      planning_available: true,
      runtime_available: true,
      approval_service_available: true,
      auth: {
        subject: { workspace_id: "one", subject_id: "alice" },
        roles: ["admin", "approver"],
        permissions: [
          "workflow.view",
          "workflow.edit",
          "workflow.plan",
          "workflow.execute",
          "workflow.validate",
          "workflow.approve",
          "events.ingest",
          "runs.view",
        ],
        scopes: ["workspace:read", "workspace:write"],
        decision: "allow",
      },
    },
  });
  vi.spyOn(api, "actionPlan").mockResolvedValue(doc());
  vi.spyOn(api, "compositionView").mockResolvedValue(view());
  vi.spyOn(api, "googleConnections").mockResolvedValue({
    items: [],
    configured: true,
    setup_message: null,
    callback_uri: null,
    callback_in_client_file: true,
    shared_demo_identity: false,
    capabilities: [],
  });
  vi.spyOn(api, "automationRecords").mockResolvedValue({
    items: [],
    has_more: false,
    next_cursor: null,
    jobs: [],
    health: {},
  });
  vi.spyOn(api, "request").mockResolvedValue({ items: [] } as never);
  vi.spyOn(api, "businessCase").mockResolvedValue(saved());
});
afterEach(() => cleanup());
it("accepts actual persisted Phase 1–3 shapes without discarding receipts", () => {
  expect(doc().action_plan.actions.length).toBeGreaterThan(4);
  expect(adaptiveSchema.parse(saved()["adaptive"]).phase).toBe("EVALUATE");
  expect(fixture.records.map((r) => automationSchema.parse(r).id)).toHaveLength(2);
  expect(view().run?.action_instances?.["send"]?.verified_receipt).toBe(true);
});
it("links only completed verified connector URLs, never generated or unsafe URLs", () => {
  expect(
    receiptLinks({
      state: "completed",
      verified_receipt: true,
      output: { spreadsheet_url: "https://docs.google.com/spreadsheets/d/real/edit" },
    }),
  ).toHaveLength(1);
  for (const value of [
    { state: "pending", verified_receipt: true },
    { state: "completed", verified_receipt: false },
  ])
    expect(receiptLinks({ ...value, output: { url: "https://example.com" } })).toEqual([]);
  expect(
    receiptLinks({
      state: "completed",
      verified_receipt: true,
      output: { url: "javascript:alert(1)", event_url: "https://user:pass@example.com" },
    }),
  ).toEqual([]);
});
it("shows actual dependencies, agent assignments, provenance and verified artifacts", async () => {
  render(<ConnectedPlan id={doc().composition_id} />);
  expect(await screen.findByLabelText('Dynamic investigation workflow canvas')).toBeVisible();
  fireEvent.click(screen.getByRole('tab',{name:'Steps'}));
  expect(await screen.findByText("1. read")).toBeVisible();
  expect(screen.getByText(/business.read.complaints · Agent: actual_agent/)).toBeVisible();
  expect(screen.getAllByText("INFERRED").length).toBeGreaterThan(0);
  expect(screen.getByRole("link", { name: /Open verified artifact/ })).toHaveAttribute(
    "href",
    String(fixture.run.action_instances.sheet.output.spreadsheet_url),
  );
});
it("uses only the pending approval exact payload and prevents duplicate decisions", async () => {
  const v = view();
  v.run!.approvals = [
    {
      approval_id: "approval_exact",
      workflow_id: v.workflow_id,
      workflow_version: 1,
      status: "pending",
      allowed_decisions: ["approved", "rejected"],
      resolved_payload: { to: "engineer@example.com", body: "Exact content" },
      action_digest: "exact_digest",
    },
  ];
  vi.mocked(api.compositionView).mockResolvedValue(v);
  const post = vi.spyOn(api, "request").mockImplementation(async () => ({}) as never);
  render(<ConnectedPlan id={doc().composition_id} />);
  const button = await screen.findByRole("button", { name: "Approve exact payload" });
  fireEvent.click(button);
  fireEvent.click(button);
  await waitFor(() => expect(post).toHaveBeenCalledTimes(1));
  expect(post.mock.calls[0]?.[1]).toMatchObject({
    approval_id: "approval_exact",
    decision: "approved",
  });
  expect(screen.getByText(/Exact content/)).toBeInTheDocument();
});
it("disables approval without its actual payload or backend decision authority", async () => {
  const v = view();
  v.run!.approvals = [
    {
      approval_id: "no_payload",
      workflow_id: v.workflow_id,
      workflow_version: 1,
      status: "pending",
      allowed_decisions: ["approved"],
    },
  ];
  vi.mocked(api.compositionView).mockResolvedValue(v);
  render(<ConnectedPlan id={doc().composition_id} />);
  expect(await screen.findByRole("button", { name: "Approve exact payload" })).toBeDisabled();
});
it("handles stale approval without replay and refreshes saved state", async () => {
  const v = view();
  v.run!.approvals = [
    {
      approval_id: "stale",
      workflow_id: v.workflow_id,
      workflow_version: 1,
      status: "pending",
      allowed_decisions: ["approved"],
      resolved_payload: { to: "engineer@example.com" },
      action_digest: "digest",
    },
  ];
  vi.mocked(api.compositionView).mockResolvedValue(v);
  const post = vi.mocked(api.request).mockRejectedValue(
    new ApiError(
      {
        error_code: "APPROVAL_CONFLICT",
        message: "Approval changed",
        request_id: "stale",
        retryable: false,
      },
      undefined,
      { httpStatus: 409, outcome: "rejected" },
    ),
  );
  render(<ConnectedPlan id={doc().composition_id} />);
  fireEvent.click(await screen.findByRole("button", { name: "Approve exact payload" }));
  await screen.findByText("Approval changed");
  expect(post).toHaveBeenCalledTimes(1);
  expect(screen.queryByText("Retry identical command")).not.toBeInTheDocument();
});
it("scopes stable retry keys to owner, workspace and exact payload without saving content", async () => {
  const a = await commandKey("one:alice", "send", { body: "Private text" });
  expect(await commandKey("one:alice", "send", { body: "Private text" })).toBe(a);
  expect(await commandKey("two:alice", "send", { body: "Private text" })).not.toBe(a);
  expect(await commandKey("one:alice", "send", { body: "Changed text" })).not.toBe(a);
  expect(JSON.stringify(sessionStorage)).not.toContain("Private text");
});
it("retries unknown commands only explicitly with the identical key", async () => {
  vi.spyOn(Storage.prototype, "getItem").mockImplementation(() => {
    throw new Error("Storage unavailable");
  });
  const calls: unknown[] = [];
  let failed = true;
  function Harness() {
    const c = useOrchestrationCommand();
    return (
      <>
        <button
          disabled={c.busy}
          onClick={() =>
            void c.act("write", { payload: 1 }, async (body) => {
              calls.push(body);
              if (failed) {
                failed = false;
                throw new Error("Lost response");
              }
            })
          }
        >
          Submit
        </button>
        {c.unknown && <button onClick={c.retry}>Retry</button>}
      </>
    );
  }
  render(<Harness />);
  fireEvent.click(screen.getByText("Submit"));
  await screen.findByText("Retry");
  expect(calls).toHaveLength(1);
  fireEvent.click(screen.getByText("Retry"));
  await waitFor(() => expect(calls).toHaveLength(2));
  expect(calls[0]).toEqual(calls[1]);
});
it("submits typed missing recipients against current case revision", async () => {
  const c = saved();
  const a = adaptiveSchema.parse(c["adaptive"]);
  a.status = "waiting";
  a.pending_wait = {
    wait_id: "wait_recipient",
    kind: "input",
    deadline: Date.now() / 1000 + 86400,
    schemas: { recipient: { type: "string", format: "email" } },
  };
  c["adaptive"] = a;
  vi.mocked(api.businessCase).mockResolvedValue(c);
  const post = vi.spyOn(api, "adaptiveCommand").mockResolvedValue(c);
  render(<AdaptiveCasePanel value={c} onSnapshot={() => {}} />);
  fireEvent.change(await screen.findByLabelText("Requested recipient"), {
    target: { value: "engineer@example.com" },
  });
  const submit = screen.getByRole("button", { name: "Supply requested information" });
  await waitFor(() => expect(submit).toBeEnabled());
  fireEvent.click(submit);
  await waitFor(() => expect(post).toHaveBeenCalledOnce());
  expect(post.mock.calls[0]).toMatchObject([
    c.case_id,
    "supply",
    {
      expected_revision: c.revision,
      wait_id: "wait_recipient",
      inputs: { recipient: "engineer@example.com" },
      request_key: expect.any(String),
    },
  ]);
});
it("shows five persisted states, revisions and reconciliation without offering unsafe continuation", async () => {
  const c = saved();
  const a = adaptiveSchema.parse(c["adaptive"]);
  a.status = "blocked";
  a.phase = "EVALUATE";
  c["adaptive"] = a;
  vi.mocked(api.businessCase).mockResolvedValue(c);
  render(<AdaptiveCasePanel value={c} onSnapshot={() => {}} />);
  expect(
    screen.getByLabelText("Five-state orchestration").querySelector('[aria-current="step"]'),
  ).toHaveTextContent("EVALUATE");
  expect(screen.getByRole("button", { name: "Continue bounded evaluation" })).toBeDisabled();
  expect(screen.getByText(/Unknown writes and interrupted evaluator calls/)).toBeVisible();
});
it("displays saved automation jobs, deadlines and worker errors without implying success", async () => {
  const r = automationSchema.parse({
    ...fixture.records[0],
    last_error_code: "ACTION_EFFECT_UNVERIFIED",
    state: "requires_reconciliation",
  });
  vi.mocked(api.automationRecords).mockResolvedValue({
    items: [r],
    has_more: false,
    next_cursor: null,
    jobs: [{ job_id: "job_error", last_error_code: "ACTION_EFFECT_UNVERIFIED" }],
    health: { state: "unknown" },
  });
  render(<AutomationPanel />);
  expect(await screen.findByText("ACTION_EFFECT_UNVERIFIED")).toBeVisible();
  expect(screen.getByText("requires reconciliation")).toBeVisible();
});
it("requires reviewed consent scope before posting and retains the saved identifier", async () => {
  vi.spyOn(api, "createAutomation").mockImplementation(async (_kind, body) =>
    automationSchema.parse({
      id: "auto_new",
      kind: "authorization",
      state: "active",
      request: body,
    }),
  );
  render(<AutomationPanel />);
  fireEvent.click(screen.getByText("Configure reviewed automation"));
  fireEvent.change(screen.getByLabelText("Automation type"), {
    target: { value: "authorizations" },
  });
  fireEvent.change(screen.getByLabelText("Five-field cron"), { target: { value: "0 9 * * *" } });
  fireEvent.change(screen.getByLabelText("Deadline"), {
    target: { value: "2027-01-01T09:00:00Z" },
  });
  fireEvent.change(screen.getByLabelText("Business purpose"), {
    target: { value: "Daily report" },
  });
  fireEvent.change(screen.getByLabelText("Authorized content scope"), {
    target: { value: "Complaint findings" },
  });
  fireEvent.change(screen.getByLabelText("Permitted operations"), {
    target: {
      value: '{"extension_mail_send":{"properties":{"to":{"const":"engineer@example.com"}}}}',
    },
  });
  fireEvent.click(screen.getByRole("button", { name: "Review automation scope" }));
  expect(api.createAutomation).not.toHaveBeenCalled();
  fireEvent.click(
    await screen.findByRole("button", { name: "Confirm reviewed recurring consent" }),
  );
  await waitFor(() => expect(api.createAutomation).toHaveBeenCalledOnce());
  expect(await screen.findByText(/Saved authorization: auto_new/)).toBeVisible();
});
it("removes scoped automation immediately when the identity changes", async () => {
  vi.mocked(api.automationRecords).mockResolvedValue({
    items: [automationSchema.parse(fixture.records[0])],
    has_more: false,
    next_cursor: null,
    jobs: [],
    health: {},
  });
  render(<AutomationPanel />);
  await screen.findAllByText(new RegExp(fixture.records[0]!.id));
  vi.mocked(api.automationRecords).mockResolvedValue({
    items: [],
    has_more: false,
    next_cursor: null,
    jobs: [],
    health: {},
  });
  await act(async () =>
    useBackend.setState((s) => ({
      session: {
        ...s.session!,
        auth: { ...s.session!.auth, subject: { workspace_id: "two", subject_id: "bob" } },
      },
    })),
  );
  expect(screen.queryAllByText(new RegExp(fixture.records[0]!.id))).toHaveLength(0);
});

it("parses the actual connected backend view including null conditions", () => {
  expect(compositionViewSchema.parse(actualView).tasks[0]?.condition).toBeNull();
});

it("accepts actual occurrence records with canonical references and no duplicated request", () => {
  expect(
    automationSchema.parse({
      id: "occ_real",
      kind: "occurrence",
      state: "completed",
      schedule_id: "auto_schedule",
      run_id: "run_real",
    }).request,
  ).toEqual({});
});

it('prepares a goal-mode plan without approving or executing it automatically',async()=>{
 const document={...doc(),interaction_mode:'goal'};
 vi.mocked(api.actionPlan).mockResolvedValue(document);
 vi.mocked(api.compositionView).mockResolvedValue({...view(),run:null,workflow_status:'draft'});
 render(<ConnectedPlan id={document.composition_id}/>);
 const review=await screen.findByRole('button',{name:/^Validate$/});
 await waitFor(()=>expect(review).toBeEnabled());
 expect(screen.queryByRole('button',{name:'Save workflow draft'})).not.toBeInTheDocument();
 expect(screen.queryByRole('button',{name:'Validate workflow'})).not.toBeInTheDocument();
 fireEvent.click(review);
 await waitFor(()=>expect(api.request).toHaveBeenCalledWith('validate_workflow',expect.anything(),expect.stringContaining('_validate')));
 expect(vi.mocked(api.request).mock.calls.some(([operation])=>operation==='approve_workflow'||operation==='execute_workflow')).toBe(false);
});


it('restores the visual graph, report tab and saved-context inspector',async()=>{
 render(<ConnectedPlan id={doc().composition_id}/>);
 expect(await screen.findByLabelText('Dynamic investigation workflow canvas')).toBeVisible();
 expect(screen.getByRole('tab',{name:'Workflow'})).toHaveAttribute('aria-selected','true');
 fireEvent.click(screen.getByRole('tab',{name:'Background'}));
 fireEvent.click(screen.getByRole('button',{name:/Agents and tools/}));
 expect(await screen.findByRole('heading',{name:'Agents and tools'})).toBeVisible();
 fireEvent.keyDown(document,{key:'Escape'});
 fireEvent.click(screen.getByRole('tab',{name:'Reports'}));
 expect(await screen.findByRole('tabpanel',{name:'Investigation report'})).toBeVisible();
});

it('keeps polling after a transient read failure without executing a command',async()=>{
 vi.useFakeTimers({shouldAdvanceTime:true});
 try{
  vi.mocked(api.actionPlan).mockRejectedValueOnce(new ApiError({error_code:'API_UNAVAILABLE',message:'Network interrupted',request_id:'read_disconnect',retryable:true})).mockResolvedValue(doc());
  render(<ConnectedPlan id={doc().composition_id}/>);
  await act(async()=>{await vi.advanceTimersByTimeAsync(3100);});
  expect(await screen.findByLabelText('Dynamic investigation workflow canvas')).toBeVisible();
  expect(api.request).not.toHaveBeenCalled();
 }finally{vi.useRealTimers();}
});


it("allows a scoped adaptive read while a command is pending without replaying it", async () => {
  let finish!: () => void;
  vi.spyOn(api,"businessCaseCommand").mockImplementation(()=>new Promise(resolve=>{finish=()=>resolve({} as never);}));
  const onSnapshot=vi.fn();
  const current=saved();current["adaptive"]={...adaptiveSchema.parse(current["adaptive"]),status:"running",pending_wait:null};
  vi.mocked(api.businessCase).mockResolvedValue(current);
  render(<AdaptiveCasePanel value={current} onSnapshot={onSnapshot}/>);
  const advance=await screen.findByRole("button",{name:"Continue bounded evaluation"});
  await waitFor(()=>expect(advance).toBeEnabled());
  fireEvent.click(advance);
  await waitFor(()=>expect(api.businessCaseCommand).toHaveBeenCalledTimes(1));
  const reads=vi.mocked(api.businessCase).mock.calls.length;
  const refresh=screen.getByRole("button",{name:"Refresh adaptive state"});
  expect(refresh).toBeEnabled();fireEvent.click(refresh);
  await waitFor(()=>expect(vi.mocked(api.businessCase).mock.calls.length).toBeGreaterThan(reads));
  expect(advance).toBeDisabled();
  expect(api.businessCaseCommand).toHaveBeenCalledTimes(1);
  await act(async()=>finish());
});

it('shows a blocked automatic draft without follow-up fields or enabled review/execution',async()=>{
 const draft=doc();draft['state']='blocked';draft['interaction_mode']='goal';draft['overview_intent']={question_free:true,blocked_requirements:[{requirement:'UNRESOLVED_REQUEST'}]};
 const blocked=view();blocked.state='blocked';blocked.run=null;blocked.workflow_status=null;blocked.gaps=[{description:'No verified destination is available.'}];
 vi.spyOn(api,'actionPlan').mockResolvedValue(draft);vi.spyOn(api,'compositionView').mockResolvedValue(blocked);
 const request=vi.spyOn(api,'request');render(<ConnectedPlan id={draft.composition_id}/>);
 await screen.findByText('Workflow draft blocked');
 expect(screen.getByRole('button',{name:'Validate'})).toBeDisabled();
 expect(screen.queryByRole('textbox')).toBeNull();expect(screen.queryByText(/Which|Supply the intended/)).toBeNull();
 expect(request).not.toHaveBeenCalled();
});

it('runs only after explicit review, preserving workflow approval and preventing duplicate submissions',async()=>{
 const current={...view(),run:null,workflow_status:'validated'};
 vi.mocked(api.compositionView).mockResolvedValue(current);
 vi.mocked(api.request).mockImplementation(async operation=>operation==='execute_workflow'?{run:{run_id:'run_confirmed'}} as never:{} as never);
 const onRun=vi.fn();render(<ConnectedPlan id={doc().composition_id} onRun={onRun}/>);
 await screen.findByLabelText('Dynamic investigation workflow canvas');
 expect(api.request).not.toHaveBeenCalled();
 fireEvent.click(screen.getByRole('button',{name:'Run'}));
 expect(await screen.findByRole('dialog')).toBeVisible();expect(api.request).not.toHaveBeenCalled();
 const confirm=screen.getByRole('button',{name:'Confirm and run'});fireEvent.click(confirm);fireEvent.click(confirm);
 await waitFor(()=>expect(onRun).toHaveBeenCalledExactlyOnceWith('run_confirmed'));
 expect(vi.mocked(api.request).mock.calls.map(([op])=>op)).toEqual(['approve_workflow','execute_workflow']);
});

it('does not execute while approving a workflow for its separate schedule',async()=>{
 vi.mocked(api.compositionView).mockResolvedValue({...view(),run:null,workflow_status:'validated'});
 render(<ConnectedPlan id={doc().composition_id} scheduled/>);await screen.findByLabelText('Dynamic investigation workflow canvas');
 fireEvent.click(screen.getByRole('button',{name:'Run'}));fireEvent.click(await screen.findByRole('button',{name:'Approve workflow'}));
 await waitFor(()=>expect(api.request).toHaveBeenCalledWith('approve_workflow',expect.anything(),expect.any(String)));
 expect(vi.mocked(api.request).mock.calls.some(([op])=>op==='execute_workflow')).toBe(false);
});

it('loads continuation automation only inside the selected workflow Background tab',async()=>{
 render(<ConnectedPlan id={doc().composition_id}/>);
 await screen.findByRole('tab',{name:'Background'});
 expect(api.automationRecords).not.toHaveBeenCalled();
 expect(screen.queryByText('Background continuation & recurring automation')).toBeNull();
 fireEvent.click(screen.getByRole('tab',{name:'Background'}));
 expect(await screen.findByText('Background continuation & recurring automation')).toBeVisible();
 expect(api.automationRecords).toHaveBeenCalledWith(undefined,view().workflow_id);
});
