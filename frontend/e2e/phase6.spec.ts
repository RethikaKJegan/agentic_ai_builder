import { test, expect } from "@playwright/test";
for(const mobile of [false,true]){
  test(`runtime history reconnect and exact approval ${mobile?"mobile":"desktop"}`,async({page})=>{
    if(mobile)await page.setViewportSize({width:390,height:844});
    const errors:string[]=[];page.on("pageerror",error=>errors.push(error.message));
    await page.goto("/app");await page.request.get("/api/backend/session");
    const template=(await(await page.request.get("/api/backend/workflows/registry_ready")).json()).data.workflow;
    const id="wf_phase6_"+crypto.randomUUID().replaceAll("-","");
    const revision={...template,workflow_id:id,version:1,status:"draft",name:"Phase 6 approval fixture",agents:[],tools:[],inputs:[],outputs:[],conditions:[],metadata:{},approval_gates:[{approval_gate_id:"review",approver_roles:["approver"],on_reject:"stop",timeout_seconds:300}],
      nodes:[{node_id:"start",kind:"trigger",label:"Start"},{node_id:"gate",kind:"approval",label:"Review",approval_gate_id:"review"},{node_id:"finish",kind:"output",label:"Finish"}],edges:[{edge_id:"start_gate",source:"start",target:"gate"},{edge_id:"gate_finish",source:"gate",target:"finish",outcome:"approved"}]};
    const mutate=async(operation:string,path:string,payload:unknown,method="POST")=>{
      const response=await page.request.fetch("/api/backend/"+path,{method,data:{request_id:"req_phase6_browser",operation,idempotency_key:crypto.randomUUID(),payload}});
      expect(response.status(),await response.text()).toBe(200);return(await response.json()).data;
    };
    const ref={workflow_id:id,workflow_version:1};
    await mutate("save_workflow_version",`workflows/${id}/versions/1`,{...ref,base_version:0,workflow:revision},"PUT");
    await mutate("validate_workflow",`workflows/${id}/validate`,ref);
    await mutate("approve_workflow",`workflows/${id}/approve`,{...ref,action:"approve"});
    await mutate("approve_workflow",`workflows/${id}/approve`,{...ref,action:"publish"});
    const executed=await mutate("execute_workflow",`workflows/${id}/execute`,{...ref,inputs:{}});
    expect(executed.run.status).toBe("paused_for_approval");
    const recorded=(await(await page.request.get(`/api/backend/runs/${executed.run.run_id}/events?limit=1`)).json()).data;
    expect(recorded.has_more).toBe(true);expect(recorded.items).toHaveLength(1);
    const next=(await(await page.request.get(`/api/backend/runs/${executed.run.run_id}/events?limit=1&after_sequence=${recorded.next_cursor}`)).json()).data;
    expect(next.items[0].event_id).not.toBe(recorded.items[0].event_id);
    let interrupted=false;
    await page.route(`**/api/backend/runs/${executed.run.run_id}/events*`,async route=>{if(!interrupted){interrupted=true;await route.abort("failed");}else await route.continue();});
    await page.goto(`/app/approvals?run=${executed.run.run_id}`);
    await expect(page.getByText("Required roles: approver")).toBeVisible({timeout:15000});
    await page.getByRole("button",{name:"Reject",exact:true}).click();
    await expect(page.getByText(new RegExp(`Approval .* · rejected · v1`))).toBeVisible();
    expect(interrupted).toBe(true);
    await page.goto("/app/monitoring");
    await page.getByLabel("Filter workflow").fill(id);
    await page.getByLabel("Filter status").selectOption("rejected");
    await expect(page.getByRole("button",{name:new RegExp(executed.run.run_id)})).toBeVisible();
    await page.getByRole("button",{name:new RegExp(executed.run.run_id)}).click();
    await expect(page.getByRole("list",{name:"Run events"})).toContainText("approval.rejected");
    await page.reload();await page.getByLabel("Filter workflow").fill(id);await page.getByLabel("Filter status").selectOption("rejected");
    await expect(page.getByRole("button",{name:new RegExp(executed.run.run_id)})).toBeVisible();
    await page.goto("/app/governance");await expect(page.getByRole("tab",{name:"Enforced governance & usage"})).toBeVisible();
    await page.getByRole("tab",{name:"Draft policies"}).click();await expect(page.getByText(/Browser-only policy drafts/)).toBeVisible();
    expect(errors).toEqual([]);
  });
}
