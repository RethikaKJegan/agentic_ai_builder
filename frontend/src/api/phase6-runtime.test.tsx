import { act, cleanup, fireEvent, render, renderHook, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { api } from "./client";
import { useBackend } from "./state";
import { useMesh } from "@/domain/store";
import { useRunFeed, sharedRead } from "@/features/runs/useRunFeed";
import { ApprovalControl, ServerRunView } from "@/features/runs/ServerRunView";
import { AgentControlTab } from "@/features/governance/AgentControlTab";
import Governance from "@/screens/app.governance";
import { RunMonitoring } from "@/features/runs/RunMonitoring";
import type { RunEvent } from "./contracts.generated";
const run={run_id:"run_phase6",workflow_id:"wf_phase6",workflow_version:1,status:"running" as const,approvals:[]};
const event=(sequence:number):RunEvent=>({event_id:`evt_${sequence}`,run_id:run.run_id,workflow_id:run.workflow_id,workflow_version:1,event_type:"node.started",timestamp:"2026-10-17T00:00:00Z",source:"runtime",details:{node_id:`node_${sequence}`,recorded_sequence:sequence}});
const collection={items:[run],total:1,has_more:false,next_cursor:null};
beforeEach(()=>{
  useBackend.setState({status:"connected",error:null,session:{mode:"local-development",planning_available:true,runtime_available:true,approval_service_available:true,auth:{subject:{subject_id:"reviewer",workspace_id:"local-workspace"},roles:["approver"],permissions:["runs.view","workflow.approve"],scopes:["workspace:read"],decision:"allow"}}});
  vi.spyOn(api,"runs").mockResolvedValue(collection);
});
afterEach(()=>{cleanup();vi.restoreAllMocks();vi.useRealTimers();});
it("coalesces simultaneous reads without caching the response",async()=>{
  let resolve!:(n:number)=>void;const read=vi.fn(()=>new Promise<number>(r=>{resolve=r;}));
  const first=sharedRead("phase6-shared",read),second=sharedRead("phase6-shared",read);
  expect(read).toHaveBeenCalledTimes(1);resolve(7);expect(await first).toBe(7);expect(await second).toBe(7);
  await sharedRead("phase6-shared",async()=>8).then(value=>expect(value).toBe(8));
});
it("drains persisted event pages for a terminal run then stops polling",async()=>{
  vi.useFakeTimers();const request=vi.spyOn(api,"request").mockImplementation(async op=>op==="get_run"?{run:{...run,status:"completed"}} as never:{items:[event(1)],total:2,has_more:true,next_cursor:"1"} as never);
  const page=vi.spyOn(api,"eventPage").mockResolvedValue({items:[event(2)],total:1,has_more:false,next_cursor:null});
  const {result}=renderHook(()=>useRunFeed(run.run_id,true));await act(async()=>{});
  expect(result.current.events).toHaveLength(1);
  await act(async()=>{await vi.advanceTimersByTimeAsync(250);});
  expect(page).toHaveBeenCalledWith(run.run_id,1);expect(result.current.events).toHaveLength(2);
  const calls=request.mock.calls.length;await act(async()=>{await vi.advanceTimersByTimeAsync(60000);});expect(request).toHaveBeenCalledTimes(calls);
});
it("retains confirmed events after interruption and resumes at the confirmed sequence",async()=>{
  vi.useFakeTimers();vi.spyOn(api,"request").mockImplementation(async op=>op==="get_run"?{run} as never:{items:[event(1)],has_more:false} as never);
  const page=vi.spyOn(api,"eventPage").mockRejectedValueOnce(new Error("network" )).mockResolvedValue({items:[event(1),event(2)],total:2,has_more:false,next_cursor:null});
  const {result}=renderHook(()=>useRunFeed(run.run_id,true));await act(async()=>{});
  await act(async()=>{await vi.advanceTimersByTimeAsync(3000);});expect(result.current.events).toHaveLength(1);expect(result.current.error).not.toBeNull();
  await act(async()=>{await vi.advanceTimersByTimeAsync(3000);});expect(result.current.events).toHaveLength(2);expect(result.current.error).toBeNull();expect(page).toHaveBeenLastCalledWith(run.run_id,1);
});
it("does not overlap a slow update or commit an old selection",async()=>{
  vi.useFakeTimers();let resolve!:(v:unknown)=>void;
  const request=vi.spyOn(api,"request").mockImplementation(()=>new Promise(r=>{resolve=r;}) as never);
  const {rerender,result}=renderHook(({id})=>useRunFeed(id,true),{initialProps:{id:run.run_id}});
  await act(async()=>{await vi.advanceTimersByTimeAsync(20000);});expect(request).toHaveBeenCalledTimes(1);
  rerender({id:"run_other"});await act(async()=>{});resolve({run});await act(async()=>{});expect(result.current.run).toBeNull();
});
it("passes filters and cursor to the server before showing an older page",async()=>{
  const runs=vi.mocked(api.runs);runs.mockResolvedValue({...collection,has_more:true,next_cursor:"10"});
  render(<ServerRunView />);await screen.findByRole("button",{name:/run_phase6/});
  fireEvent.change(screen.getByLabelText("Filter status"),{target:{value:"failed"}});
  await waitFor(()=>expect(runs).toHaveBeenLastCalledWith(expect.objectContaining({status:"failed",limit:50})));
  fireEvent.click(screen.getByRole("button",{name:"Older runs"}));
  await waitFor(()=>expect(runs).toHaveBeenLastCalledWith(expect.objectContaining({status:"failed",cursor:"10"})));
});
it("shows no approval button when the server denies the exact gate role",()=>{
  render(<ApprovalControl approval={{approval_id:"approval_gate",workflow_id:run.workflow_id,workflow_version:1,status:"pending",required_roles:["admin"],allowed_decisions:[]}} />);
  expect(screen.getByText(/Required roles: admin/)).toBeVisible();expect(screen.queryByRole("button",{name:"Approve"})).toBeNull();expect(screen.getByText(/exact gate role/)).toBeVisible();
});
it("local organization-admin flags cannot enable draft control edits for a server viewer",()=>{
  useMesh.setState({role:"org-admin"} as never);useBackend.setState({session:{...useBackend.getState().session!,auth:{...useBackend.getState().session!.auth,roles:["viewer"],permissions:["runs.view"]}}});
  render(<AgentControlTab />);expect(screen.getByRole("switch",{name:"organization agent execution"})).toBeDisabled();expect(screen.getByText(/Effective browser draft:/)).toBeVisible();
});
it("keeps organization governance read-only without draft editors",()=>{
  vi.spyOn(api,"monitoring").mockReturnValue(new Promise(()=>{}));render(<Governance />);
  expect(screen.getByText("Read-only",{exact:true})).toBeVisible();expect(screen.getByRole("tab",{name:"Organization Policies"})).toBeVisible();expect(screen.queryByRole("tab",{name:"Draft policies"})).toBeNull();
});
it("shows disabled source, schedule, preparation and versioned enforcement scope",async()=>{
  vi.spyOn(api,"monitoring").mockResolvedValue({runs:{total:0,active:0,completed:0,failed:0},events:0,usage:{llm_calls:0,tool_calls:0,tokens:0,retries:0,estimated_cost_usd:0},latest:[],sources:[{binding_id:"binding",workflow_id:"workflow",provider_id:"generic_rest",health:"disabled",release_state:"disabled",delivery:"poll",event_type:"row.created",workflow_version:3,source:"resource",preparation_succeeded:false,baseline_ready:false,schedule:"*/5 * * * *",timezone:"UTC"}],policies:[{workflow_id:"workflow",version:2,scope:"workspace:local-workspace",enforcement:"active_release",policy_version:7,action_approval_required:true,agents:[]}]});
  render(<RunMonitoring />);fireEvent.click(screen.getByText("Runtime monitoring",{exact:true}));await screen.findByText(/Release: disabled/);expect(screen.getByText(/Preparation: not ready/)).toHaveTextContent("Schedule:");expect(screen.getByText(/cannot receive active automation/)).toBeVisible();expect(screen.getByText(/Policy version 7/)).toHaveTextContent("v2");
});
