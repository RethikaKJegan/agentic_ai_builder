import { test,expect } from '@playwright/test';
for(const mobile of [false,true]){
 test(`explicit lifecycle, typed run and confirmed settings ${mobile?'mobile':'desktop'}`,async({page})=>{
  if(mobile)await page.setViewportSize({width:390,height:844});
  const errors:string[]=[];page.on('pageerror',e=>errors.push(e.message));
  const seedId='wf_phase3_'+crypto.randomUUID().replaceAll('-','');
  await page.addInitScript(({id})=>{
   if(localStorage.getItem('phase3-seeded'))return;
   const at=new Date().toISOString();
   localStorage.setItem('mesh-local-drafts-v1',JSON.stringify({version:1,state:{workflows:[{id,workspaceId:'local',name:'Phase 3 independent actions',description:'A synthetic deterministic workflow',prompt:'',scenario:'custom',status:'draft',versions:[],createdAt:at,updatedAt:at,nodes:[{id:'start',type:'mesh',position:{x:80,y:120},data:{kind:'trigger',label:'Start'}},{id:'finish',type:'mesh',position:{x:420,y:120},data:{kind:'output',label:'Finish'}}],edges:[{id:'start_finish',source:'start',target:'finish'}]}],agents:[]}}));
   localStorage.setItem('phase3-seeded','1');
  },{id:seedId});
  await page.goto('/app/workflows/'+seedId);
  const actions=page.getByRole('region',{name:'Workflow actions'});
  await expect(actions.getByRole('button',{name:'Save draft',exact:true})).toBeEnabled();
  await expect(actions.getByRole('button',{name:'Publish',exact:true})).toBeDisabled();
  const operations:string[]=[];page.on('request',request=>{try{const body=request.postDataJSON();if(body?.operation)operations.push(body.operation);}catch{/* GET requests have no JSON body. */}});
  await actions.getByRole('button',{name:'Save draft',exact:true}).click();
  await expect(actions.getByText(/Save draft confirmed/)).toBeVisible();
  expect(operations).toEqual(['save_workflow_version']);
  await actions.getByRole('button',{name:'Validate',exact:true}).click();
  await expect(actions.getByText(/Validate confirmed/)).toBeVisible();
  await actions.getByRole('button',{name:'Submit for approval',exact:true}).click();
  await expect(actions.getByText(/Submit for approval confirmed/)).toBeVisible();
  await expect(actions.getByRole('button',{name:'Publish',exact:true})).toBeDisabled();
  await actions.getByRole('button',{name:'Approve',exact:true}).click();
  await expect(actions.getByText(/Approve confirmed/)).toBeVisible();
  await actions.getByRole('button',{name:'Publish',exact:true}).click();
  await expect(actions.getByText(/Publish confirmed/)).toBeVisible();
  expect(operations).toEqual(['save_workflow_version','validate_workflow','submit_workflow_for_approval','approve_workflow','approve_workflow']);
  const id=new URL(page.url()).pathname.split('/').at(-1)!;
  const state=await page.request.get(`/api/backend/workflows/${id}`);const original=(await state.json()).data.workflow;
  expect(original.status).toBe('published');
  const overview=await page.request.get('/api/backend/workflow-overview');expect((await overview.json()).data.items.find((w:{workflow_id:string})=>w.workflow_id===id).release_id).toBeNull();
  page.once('dialog',dialog=>dialog.dismiss());await actions.getByRole('button',{name:'Activate',exact:true}).click();
  await page.reload();await expect(page.getByLabel('Workflow name',{exact:true})).toHaveValue('Phase 3 independent actions');
  await page.getByLabel('Workflow name',{exact:true}).fill('Unsaved phase 3 edit');
  let prompted=false;page.once('dialog',async dialog=>{prompted=true;await dialog.dismiss();});
  await page.getByRole('link',{name:'Back to workflows'}).click();expect(prompted).toBe(true);await expect(page).toHaveURL(new RegExp(id));
  page.once('dialog',dialog=>dialog.accept());await page.getByRole('link',{name:'Back to workflows'}).click();
  // Give this isolated published revision explicit input types through the actual API.
  const candidate={...original,version:2,status:'draft',inputs:[{name:'count',type:'integer',required:true},{name:'enabled',type:'boolean',required:true},{name:'details',type:'object',required:false}]};
  const mutation=async(operation:string,path:string,payload:unknown,method='POST')=>{
   const response=await page.request.fetch('/api/backend/'+path,{method,data:{request_id:'req_browser_phase3',operation,idempotency_key:crypto.randomUUID(),payload}});expect(response.status()).toBe(200);return (await response.json()).data;
  };
  await mutation('save_workflow_version',`workflows/${id}/versions/2`,{workflow_id:id,workflow_version:2,base_version:1,workflow:candidate},'PUT');
  await mutation('validate_workflow',`workflows/${id}/validate`,{workflow_id:id,workflow_version:2});
  await mutation('approve_workflow',`workflows/${id}/approve`,{workflow_id:id,workflow_version:2,action:'approve'});
  await mutation('approve_workflow',`workflows/${id}/approve`,{workflow_id:id,workflow_version:2,action:'publish'});
  await page.reload();await page.locator(`a[href='/app/workflows/${id}']`).first().locator('..').getByRole('button',{name:/Actions for/}).click();
  await page.getByRole('menuitem',{name:'Run published'}).click();
  const dialog=page.getByRole('dialog',{name:'Run Phase 3 independent actions'});await expect(dialog).toBeVisible();
  await dialog.getByLabel('count',{exact:true}).fill('1.5');await dialog.getByLabel('enabled',{exact:true}).selectOption('false');
  await dialog.getByRole('button',{name:'Start run',exact:true}).click();await expect(dialog.getByRole('alert')).toContainText('safe integer');
  await dialog.getByLabel('count',{exact:true}).fill('2');await dialog.getByLabel('details',{exact:true}).fill('{}');
  await dialog.getByRole('button',{name:'Start run',exact:true}).focus();await page.keyboard.press('Enter');
  const detailLink=dialog.getByRole('link',{name:'View run details'});await expect(detailLink).toBeVisible();
  await detailLink.click();await expect(page).toHaveURL(/\/app\/runs\?run=/);await expect(page.getByRole('list',{name:'Run events'})).toBeVisible();
  await page.goto('/app/settings');await expect(page.getByLabel('Notification preference')).toBeEnabled();
  await page.getByLabel('Notification preference').fill(mobile?'mobile-confirmed':'desktop-confirmed');
  await page.getByRole('button',{name:'Save setting',exact:true}).focus();await page.keyboard.press('Enter');
  await expect(page.getByText('Setting saved on the server.')).toBeVisible();await page.reload();
  await expect(page.getByLabel('Notification preference')).toHaveValue(mobile?'mobile-confirmed':'desktop-confirmed');
  await page.goto('/app/integrations');await page.getByRole('button',{name:'Check configuration'}).first().click();
  await expect(page.getByText('Verified',{exact:true})).toHaveCount(0);
  expect(errors).toEqual([]);
 });
}
