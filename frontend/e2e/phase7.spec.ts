import { test, expect } from "@playwright/test";
import { generate, mutation } from "./helpers";
for(const mobile of [false,true]){
 test(`complete isolated release journey and controlled failure ${mobile?'mobile':'desktop'}`,async({page})=>{
  test.setTimeout(120000);if(mobile)await page.setViewportSize({width:390,height:844});
  const errors:string[]=[];page.on('pageerror',error=>errors.push(error.message));
  const id=await generate(page,'Classify a support request for release acceptance '+crypto.randomUUID());
  const original=(await(await page.request.get(`/api/backend/workflows/${id}`)).json()).data.workflow;
  await page.locator('summary').filter({hasText:'Workflow outline and connections'}).click();
  await page.getByRole('button',{name:/Master orchestrator.*agent/}).first().click();
  await page.getByLabel('Instructions',{exact:true}).fill('Classify the request and return a structured result. Phase seven reviewed instruction.');
  await page.getByRole('button',{name:'Close inspector',exact:true}).click();
  await page.getByRole('button',{name:'Add step',exact:true}).click();await page.getByRole('menuitem',{name:'Router',exact:true}).click();
  await page.getByLabel('Condition expression').fill("'yes'");await page.getByLabel('Condition outcomes').fill('yes, no');
  await page.getByRole('button',{name:'Close inspector',exact:true}).click();
  const master=original.nodes.find((node:{node_id:string})=>node.node_id==='master_orchestrator');
  const outgoing=original.edges.find((edge:{source:string})=>edge.source===master.node_id);
  const targetLabel=original.nodes.find((node:{node_id:string})=>node.node_id===outgoing.target).label;
  page.once('dialog',dialog=>dialog.accept());await page.getByRole('button',{name:`Remove connection ${outgoing.edge_id}`,exact:true}).click();
  const source=page.getByLabel('Connection source'),target=page.getByLabel('Connection target');
  const router=await source.locator('option').filter({hasText:/Router|Condition/}).getAttribute('value');expect(router).toBeTruthy();
  await source.selectOption(master.node_id);await target.selectOption(router!);await page.getByRole('button',{name:'Connect steps',exact:true}).click();
  await source.selectOption(router!);await target.selectOption({label:targetLabel});
  await page.getByLabel('Connection outcome').selectOption('yes');await page.getByRole('button',{name:'Connect steps',exact:true}).click();
  await page.getByLabel('Connection outcome').selectOption('no');await page.getByRole('button',{name:'Connect steps',exact:true}).click();
  const actions=page.getByRole('region',{name:'Workflow actions'});
  await actions.getByRole('button',{name:'Save draft',exact:true}).click();await expect(actions.getByText(/Save draft confirmed · v2/)).toBeVisible();
  await page.reload();const saved=(await(await page.request.get(`/api/backend/workflows/${id}`)).json()).data.workflow;
  expect(saved.version).toBe(2);expect(saved.conditions.find((condition:{expression:string})=>condition.expression==="'yes'")).toBeTruthy();
  expect(saved.agents.some((agent:{instructions:string})=>agent.instructions.includes('Phase seven reviewed instruction'))).toBe(true);
  await actions.getByRole('button',{name:'Validate',exact:true}).click();await expect(actions.getByText(/Validate confirmed · v2/)).toBeVisible();
  // Product simulation is intentionally unavailable; it must never start execution.
  await page.getByText('Workflow lifecycle · 14 stages',{exact:true}).click();
  await expect(page.getByText(/no supported side-effect-free runtime simulation/)).toBeVisible();
  expect((await(await page.request.get(`/api/backend/runs?workflow_id=${id}`)).json()).data.total).toBe(0);
  // Changed executable agent definitions require an explicit trusted operator
  // Registry review. The fixture invokes the real registration/validation API.
  const review=await page.request.post(`/api/backend/__test__/registry-review/${id}/2`);expect(review.status(),await review.text()).toBe(200);expect((await review.json()).data.tool_grants_issued).toBe(false);
  await actions.getByRole('button',{name:'Submit for approval',exact:true}).click();await expect(actions.getByText(/Submit for approval confirmed/)).toBeVisible();
  await actions.getByRole('button',{name:'Approve',exact:true}).click();await expect(actions.getByText(/Approve confirmed/)).toBeVisible();
  await actions.getByRole('button',{name:'Publish',exact:true}).click();await expect(actions.getByText(/Publish confirmed/)).toBeVisible();
  page.once('dialog',dialog=>dialog.accept());await actions.getByRole('button',{name:'Activate',exact:true}).click();await expect(actions.getByText(/Activation succeeded/)).toBeVisible();
  const release=(await(await page.request.get(`/api/backend/workflows/${id}/release-state`)).json()).data.release;expect(release.state).toBe('active');expect(release.workflow_version).toBe(2);
  const inputValues=Object.fromEntries(saved.inputs.map((field:{name:string;type:string})=>[field.name,field.type==='boolean'?true:field.type==='object'?{}:field.type==='array'?[]:field.type==='integer'||field.type==='number'?1:'Review this support request']));
  const key=crypto.randomUUID();const executed=await mutation(page,'execute_workflow',`workflows/${id}/execute`,{workflow_id:id,workflow_version:2,inputs:inputValues},'POST',key);expect(executed.status(),await executed.text()).toBe(200);
  const run=(await executed.json()).data.run;const firstEvents=(await(await page.request.get(`/api/backend/runs/${run.run_id}/events?limit=500`)).json()).data.items;expect(run.status,JSON.stringify(firstEvents.filter((event:{event_type:string})=>['node.failed','runtime.denied','run.failed','run.blocked'].includes(event.event_type)))).toBe('completed');
  const repeat=await mutation(page,'execute_workflow',`workflows/${id}/execute`,{workflow_id:id,workflow_version:2,inputs:inputValues},'POST',key);expect((await repeat.json()).data.run.run_id).toBe(run.run_id);
  await page.getByRole('tab',{name:'Execution',exact:true}).click();await page.getByRole('button',{name:'Refresh trace',exact:true}).click();
  await expect(page.getByText(new RegExp(`Read-only historical revision v2 · Run ${run.run_id}`))).toBeVisible();
  await page.getByRole('button',{name:/Router.*condition/}).click();await expect(page.getByLabel('Node execution trace').getByText('yes',{exact:true})).toBeVisible();
  const candidate={...saved,version:3,status:'draft',inputs:saved.inputs};candidate.conditions.find((condition:{expression:string})=>condition.expression==="'yes'").expression='outputs.master_orchestrator.missing';
  for(const agent of candidate.agents){agent.allowed_tool_ids=[];}for(const tool of candidate.tools){delete tool.configuration_reference;}
  const save=await mutation(page,'save_workflow_version',`workflows/${id}/versions/3`,{workflow_id:id,workflow_version:3,base_version:2,workflow:candidate},'PUT');expect(save.status(),await save.text()).toBe(200);
  for(const operation of ['validate_workflow','approve_workflow','approve_workflow']){
   const action=operation==='approve_workflow'?(await(await page.request.get(`/api/backend/workflows/${id}`)).json()).data.workflow.status==='approved'?'publish':'approve':undefined;
   const response=await mutation(page,operation,`workflows/${id}/${operation==='validate_workflow'?'validate':'approve'}`,{workflow_id:id,workflow_version:3,...(action?{action}:{})});expect(response.status(),await response.text()).toBe(200);
  }
  const failedKey=crypto.randomUUID();const payload={workflow_id:id,workflow_version:3,inputs:inputValues};
  const failure=await mutation(page,'execute_workflow',`workflows/${id}/execute`,payload,'POST',failedKey);expect(failure.status()).toBe(200);const failed=(await failure.json()).data.run;expect(['failed','blocked']).toContain(failed.status);
  const again=await mutation(page,'execute_workflow',`workflows/${id}/execute`,payload,'POST',failedKey);expect((await again.json()).data.run.run_id).toBe(failed.run_id);
  await page.goto(`/app/runs?run=${failed.run_id}`);await expect(page.getByText(new RegExp(`Failed node: ${router}`))).toBeVisible();
  const events=(await(await page.request.get(`/api/backend/runs/${failed.run_id}/events?limit=500`)).json()).data.items;
  expect(events.find((event:{event_type:string;details:{node_id:string}})=>event.event_type==='node.failed'&&event.details.node_id===router)).toBeTruthy();
  const previous=(await(await page.request.get(`/api/backend/workflows/${id}/release-state`)).json()).data.release;expect(previous.workflow_version).toBe(2);expect(previous.release_id).toBe(release.release_id);
  expect((await(await page.request.get(`/api/backend/runs?workflow_id=${id}`)).json()).data.total).toBe(2);expect(errors).toEqual([]);
 });
}

test('settings and integration failures recover without a fabricated verification',async({page})=>{
 let failed=true;
 await page.route('**/api/backend/workspace/settings',async route=>{
  if(failed)await route.fulfill({status:503,json:{request_id:'req_phase7_settings',status:503,data:{error:{error_code:'SERVICE_UNAVAILABLE',message:'Settings temporarily unavailable.',request_id:'req_phase7_settings',retryable:false}}}});
  else await route.continue();
 });
 await page.goto('/app/settings');await expect(page.getByRole('alert').filter({hasText:'SERVICE_UNAVAILABLE'})).toContainText('Settings temporarily unavailable');await expect(page.getByLabel('Notification preference')).toBeDisabled();
 failed=false;await page.getByRole('button',{name:'Reload settings',exact:true}).click();await expect(page.getByLabel('Notification preference')).toBeEnabled();await expect(page.getByRole('alert').filter({hasText:'SERVICE_UNAVAILABLE'})).toHaveCount(0);
 let rejected=true;
 await page.route('**/api/backend/integrations/*/test',async route=>{
  if(rejected)await route.fulfill({status:403,json:{request_id:'req_phase7_provider',status:403,data:{error:{error_code:'OPERATION_NOT_AUTHORIZED',message:'Provider checks are not authorized.',request_id:'req_phase7_provider',retryable:false}}}});
  else await route.continue();
 });
 await page.goto('/app/integrations');await page.getByRole('button',{name:'Check configuration',exact:true}).first().click();
 await expect(page.getByRole('alert').filter({hasText:'OPERATION_NOT_AUTHORIZED'})).toContainText('Provider checks are not authorized');await expect(page.getByText('Verified',{exact:true})).toHaveCount(0);
 rejected=false;await page.getByRole('button',{name:'Check configuration',exact:true}).first().click();
 await expect(page.getByRole('alert').filter({hasText:'OPERATION_NOT_AUTHORIZED'})).toHaveCount(0);await expect(page.getByText('Verified',{exact:true})).toHaveCount(0);
});
