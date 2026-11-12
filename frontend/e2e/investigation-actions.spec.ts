import {test,expect} from '@playwright/test';
import {createHmac,randomBytes} from 'node:crypto';
for(const tenant of ['simpsons','subway'])for(const mobile of [false,true])test(`${tenant} workflow duplicate/rename/delete persist on ${mobile?'mobile':'desktop'}`,async({page})=>{
 if(mobile)await page.setViewportSize({width:390,height:844});
 const payload=`${Math.floor(Date.now()/1000)+3600}.${randomBytes(24).toString('hex')}`;
 const secret=process.env['BUILDER_LOGIN_SECRET']!;
 await page.context().addCookies([{name:'builder_workspace_access',value:`${payload}.${createHmac('sha256',secret).update(payload).digest('hex')}`,domain:'127.0.0.1',path:'/'}]);
 let name='Complaint comparison';let deleted=false;let copied=false;let renameCalls=0;let deleteCalls=0;let rejectRename=true;
 const errors:string[]=[];page.on('pageerror',e=>errors.push(e.message));
 await page.route('**/api/backend/**',async route=>{
  const request=route.request();const target=new URL(request.url()).pathname.replace('/api/backend/','');let data:unknown={items:[],total:0,has_more:false,next_cursor:null};
  if(target==='session')data={mode:'local-development',planning_available:true,runtime_available:true,approval_service_available:true,auth:{subject:{subject_id:'local-builder',workspace_id:'local-workspace'},roles:['admin'],permissions:['workflow.view','workflow.plan','workflow.execute','workflow.edit','workflow.delete','tools.read','runs.view'],scopes:['workspace:read','workspace:write'],decision:'allow'}};
  else if(target.startsWith('workflow-overview'))data={items:[],next_sequence:0,has_more:false};
  else if(target==='business-ontology/v1/investigations')data={items:[...(copied?[{workflow_id:'investigation_copy_fixture',display_name:'Complaint comparison (copy)',objective:'Compare complaint C123 with inspection.',created_at:'2026-11-04T10:00:00Z',node_count:16,run_id:null,status:'planned'}]:[]),...(deleted?[]:[{workflow_id:'investigation_actions_fixture',display_name:name,objective:'Compare complaint C123 with inspection.',created_at:'2026-11-03T10:00:00Z',node_count:16,run_id:'run_actions_fixture',status:'completed'}])],jobs:[]};
  else if(target.endsWith('/plans/investigation_actions_fixture/duplicate')){copied=true;data={workflow_id:'investigation_copy_fixture'};}
  else if(target.endsWith('/plans/investigation_actions_fixture')){
   if(request.method()==='PUT'){
    renameCalls++;
    if(rejectRename){rejectRename=false;await route.fulfill({status:409,json:{request_id:'req_actions',status:409,data:{correlation_id:'req_actions',error:{error_code:'INVESTIGATION_CONFLICT',message:'Please retry this change.',request_id:'req_actions',retryable:false}}}});return;}
    name=request.postDataJSON().display_name;data={workflow_id:'investigation_actions_fixture',display_name:name};
   }else if(request.method()==='DELETE'){deleteCalls++;deleted=true;data={workflow_id:'investigation_actions_fixture',deleted:true};}
  }
  await route.fulfill({json:{request_id:'req_actions',status:200,data}});
 });
 await page.goto('/app/workflows');
 await expect(page.getByText('Complaint comparison',{exact:true})).toBeVisible();
 await expect(page.getByText('Persistent business lifecycle',{exact:true})).toHaveCount(0);
 await expect(page.getByText('Business investigations',{exact:true})).toHaveCount(0);
 await page.getByRole('button',{name:'Actions for Complaint comparison',exact:true}).click();
 await page.getByRole('menuitem',{name:'Duplicate',exact:true}).click();
 await expect(page.getByText('Complaint comparison (copy)',{exact:true})).toBeVisible();
 await page.reload();
 await expect(page.getByText('Complaint comparison (copy)',{exact:true})).toBeVisible();
 await expect(page.getByText('Complaint comparison',{exact:true})).toBeVisible();
 await page.getByRole('button',{name:'Actions for Complaint comparison',exact:true}).click();
 await page.getByRole('menuitem',{name:'Rename',exact:true}).click();
 await expect(page).toHaveURL(/\/app\/workflows$/);
 await page.getByRole('textbox',{name:'Workflow name'}).fill('Replacement evidence review');
 await page.getByRole('button',{name:'Save name',exact:true}).click();
 await expect(page.getByRole('alert')).toContainText('Please retry this change.');
 await page.getByRole('button',{name:'Save name',exact:true}).click();
 await expect(page.getByRole('dialog')).toHaveCount(0);
 await page.reload();await expect(page.getByText('Replacement evidence review',{exact:true})).toBeVisible();
 await page.getByRole('button',{name:'Actions for Replacement evidence review',exact:true}).click();
 await page.getByRole('menuitem',{name:'Delete workflow',exact:true}).click();
 await page.getByRole('button',{name:'Cancel',exact:true}).click();expect(deleteCalls).toBe(0);
 await page.getByRole('button',{name:'Actions for Replacement evidence review',exact:true}).click();
 await page.getByRole('menuitem',{name:'Delete workflow',exact:true}).click();
 await expect(page.getByRole('dialog')).toContainText('Saved execution history is retained.');
 await page.getByRole('dialog').getByRole('button',{name:'Delete workflow',exact:true}).click();
 await expect(page.getByText('Replacement evidence review',{exact:true})).toHaveCount(0);
 await page.reload();await expect(page.getByText('Complaint comparison (copy)',{exact:true})).toBeVisible();
 expect(renameCalls).toBe(2);expect(deleteCalls).toBe(1);expect(errors).toEqual([]);
 expect(await page.evaluate(()=>document.documentElement.scrollWidth<=window.innerWidth)).toBe(true);
 await page.screenshot({path:`../.local/workflow-presentation-${tenant}-${mobile?'mobile':'desktop'}.png`,fullPage:true});
});
