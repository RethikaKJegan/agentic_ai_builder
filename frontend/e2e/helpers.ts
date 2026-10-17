import { expect, type Page } from "@playwright/test";
export async function localDraft(page:Page,name:string){
 const id="wf_phase7_"+crypto.randomUUID().replaceAll("-","");
 await page.addInitScript(({id,name})=>{
  if(localStorage.getItem('phase7-local-seed'))return;
  const at=new Date().toISOString();
  localStorage.setItem('mesh-local-drafts-v1',JSON.stringify({version:1,state:{workflows:[{id,workspaceId:'local',name,description:'An isolated editable draft',prompt:'',scenario:'custom',status:'draft',versions:[],createdAt:at,updatedAt:at,nodes:[{id:'start',type:'mesh',position:{x:80,y:120},data:{kind:'trigger',label:'Start'}},{id:'finish',type:'mesh',position:{x:420,y:120},data:{kind:'output',label:'Finish'}}],edges:[{id:'start_finish',source:'start',target:'finish'}]}],agents:[]}}));
  localStorage.setItem('phase7-local-seed','1');
 },{id,name});
 await page.goto('/app/workflows/'+id);return id;
}
export async function generate(page:Page,objective:string){
 await page.goto('/app');await page.getByLabel('Process description').fill(objective);
 await page.getByRole('button',{name:'Generate workflow',exact:true}).click();
 await page.getByRole('button',{name:'Review and edit workflow',exact:true}).click();
 await expect(page.getByLabel('Workflow name',{exact:true})).toBeVisible();
 return new URL(page.url()).pathname.split('/').at(-1)!;
}
export async function mutation(page:Page,operation:string,path:string,payload:unknown,method='POST',key=crypto.randomUUID()){
 return page.request.fetch('/api/backend/'+path,{method,data:{request_id:'req_phase7_browser',operation,idempotency_key:key,payload}});
}
