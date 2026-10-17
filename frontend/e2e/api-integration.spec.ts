import { test, expect } from "@playwright/test";
import { localDraft, mutation } from "./helpers";

test("generated canonical branches and gates survive explicit save and reload",async({page})=>{
 const errors:string[]=[];page.on("pageerror",error=>errors.push(error.message));
 // Legacy manually configured documents remain supported through the canonical API.
 // The overview now always infers inputs automatically and cannot create this manual fixture.
 await page.goto('/app');
 const session=await page.request.get('/api/backend/session');expect(session.status(),await session.text()).toBe(200);
 const response=await mutation(page,'plan_workflow','workflows/plan',{objective:'If an invoice arrives classify it and email the owner after approval for phase seven review',context:{generation_mode:'hierarchy',execution_input_mode:'manual'}});
 expect(response.status(),await response.text()).toBe(200);
 const workflow=(await response.json()).data.workflow;const id=workflow.workflow_id;
 const persisted=await mutation(page,'save_workflow_version',`workflows/${id}/versions/1`,{workflow_id:id,workflow_version:1,workflow,base_version:0},'PUT');
 expect(persisted.status(),await persisted.text()).toBe(200);
 await page.goto(`/app/workflows/${id}`);await expect(page.getByLabel('Workflow name',{exact:true})).toBeVisible();
 const saved=(await(await page.request.get(`/api/backend/workflows/${id}`)).json()).data.workflow;
 expect(saved.conditions.length).toBeGreaterThan(0);expect(saved.approval_gates.length).toBeGreaterThan(0);
 await page.getByLabel("Workflow name",{exact:true}).fill("Connected invoice review");
 const actions=page.getByRole("region",{name:"Workflow actions"});
 await expect(actions.getByRole("button",{name:"Validate",exact:true})).toBeDisabled();
 await actions.getByRole("button",{name:"Save draft",exact:true}).click();
 await expect(actions.getByText(/Save draft confirmed · v2/)).toBeVisible();
 await page.reload();await expect(page.getByLabel("Workflow name",{exact:true})).toHaveValue("Connected invoice review");
 const document=(await(await page.request.get(`/api/backend/workflows/${id}`)).json()).data.workflow;
 expect(document.conditions).toEqual(saved.conditions);expect(document.approval_gates).toEqual(saved.approval_gates);
 expect(document.agents.every((agent:{allowed_tool_ids:string[]})=>agent.allowed_tool_ids.length===0)).toBe(true);
 expect(JSON.stringify(document)).not.toContain("cred_browser_");expect(errors).toEqual([]);
});

test("trusted publication requires explicit approval and activation; new drafts clear grants",async({page})=>{
 await page.goto("/app/workflows/registry_ready");
 const actions=page.getByRole("region",{name:"Workflow actions"});
 await expect(page.getByLabel("Workflow name",{exact:true})).toBeVisible();
 const initial=(await(await page.request.get("/api/backend/workflows/registry_ready")).json()).data;expect(initial.registry_review.ready).toBe(true);
 await actions.getByRole("button",{name:"Validate",exact:true}).click();
 await expect(actions.getByText(/Validate confirmed/)).toBeVisible();
 await expect(actions.getByRole("button",{name:"Publish",exact:true})).toBeDisabled();
 await actions.getByRole("button",{name:"Approve",exact:true}).click();
 await expect(actions.getByText(/Approve confirmed/)).toBeVisible();
 await actions.getByRole("button",{name:"Publish",exact:true}).click();
 await expect(actions.getByText(/Publish confirmed/)).toBeVisible();
 let state=(await(await page.request.get("/api/backend/workflows/registry_ready/release-state")).json()).data;
 expect(state.release).toBeNull();
 page.once("dialog",dialog=>dialog.accept());await actions.getByRole("button",{name:"Activate",exact:true}).click();
 await expect(actions.getByText(/Activation succeeded/)).toBeVisible();
 state=(await(await page.request.get("/api/backend/workflows/registry_ready/release-state")).json()).data;
 expect(state.release.state).toBe("active");expect(state.release.workflow_version).toBe(1);
 const document=(await(await page.request.get("/api/backend/workflows/registry_ready")).json()).data.workflow;
 expect(document.agents[0].allowed_tool_ids).toEqual(["sheets_ready"]);
 await page.getByLabel("Workflow name",{exact:true}).fill("New editable registry revision");
 await actions.getByRole("button",{name:"Save draft",exact:true}).click();
 await expect(actions.getByText(/Save draft confirmed · v2/)).toBeVisible();
 const revised=(await(await page.request.get("/api/backend/workflows/registry_ready")).json()).data.workflow;
 expect(revised.agents[0].allowed_tool_ids).toEqual([]);
 state=(await(await page.request.get("/api/backend/workflows/registry_ready/release-state")).json()).data;
 expect(state.release.workflow_version).toBe(1);expect(state.release.state).toBe("active");
});

test("pending approval and risky Registry assignments cannot approve or publish",async({page})=>{
 for(const [id,reason] of [["registry_pending","APPROVAL_REQUIRED"],["registry_risky","RISK_NOT_AUTHORIZED"]]){
  await page.goto(`/app/workflows/${id}`);
  await expect(page.getByRole("region",{name:"Workflow actions"}).getByText(new RegExp(reason!))).toBeVisible();
  const actions=page.getByRole("region",{name:"Workflow actions"});
  await actions.getByRole("button",{name:"Validate",exact:true}).click();
  await expect(actions.getByRole("button",{name:"Publish",exact:true})).toBeDisabled();
  const response=await mutation(page,"approve_workflow",`workflows/${id}/approve`,{workflow_id:id,workflow_version:1,action:"approve"});
  expect(response.status()).toBeGreaterThanOrEqual(400);
  const saved=(await(await page.request.get(`/api/backend/workflows/${id}`)).json()).data.workflow;
  expect(["approved","published"]).not.toContain(saved.status);expect(saved.agents[0].allowed_tool_ids).toEqual([]);
 }
});

test("invalid graph validation fails authoritatively without creating a run",async({page})=>{
 const id=await localDraft(page,"Persisted plain workflow");
 await page.getByRole("button",{name:"Save draft",exact:true}).click();
 await expect(page.getByText(/Save draft confirmed · v1/)).toBeVisible();
 const existing=(await(await page.request.get(`/api/backend/workflows/${id}`)).json()).data.workflow;
 existing.version=2;existing.edges[0].target="missing_node";
 const save=await mutation(page,"save_workflow_version",`workflows/${id}/versions/2`,{workflow_id:id,workflow_version:2,workflow:existing,base_version:1},"PUT");expect(save.status()).toBe(200);
 const response=await mutation(page,"validate_workflow",`workflows/${id}/validate`,{workflow_id:id,workflow_version:2});
 expect(response.status()).toBeGreaterThanOrEqual(400);expect((await response.json()).data.error.error_code).toBe("WORKFLOW_VALIDATION_FAILED");
 const runs=(await(await page.request.get(`/api/backend/runs?workflow_id=${id}`)).json()).data;expect(runs.total).toBe(0);
});
