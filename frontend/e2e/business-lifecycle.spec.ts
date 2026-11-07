import {test,expect,type Page} from '@playwright/test';
import {createHmac,randomBytes} from 'node:crypto';
import {caseSchema,type BusinessCase} from '../src/api/business-lifecycle';
async function login(page:Page){
 const payload=`${Math.floor(Date.now()/1000)+3600}.${randomBytes(24).toString('hex')}`;
 await page.context().addCookies([{name:'builder_workspace_access',value:`${payload}.${createHmac('sha256',process.env['BUILDER_LOGIN_SECRET']!).update(payload).digest('hex')}`,domain:'127.0.0.1',path:'/'}]);
}
for(const mobile of [false,true])test(`real lifecycle API, Simpson and retail on ${mobile?'mobile':'desktop'}`,async({page})=>{
 if(mobile)await page.setViewportSize({width:390,height:844});await login(page);const errors:string[]=[];page.on('pageerror',e=>errors.push(e.message));
 await page.goto('/app/workflows');const panel=page.getByRole('region',{name:'Persistent business lifecycle'});await expect(panel.getByRole('button',{name:'Create case'})).toBeEnabled();
 for(const retail of [false,true]){
  await panel.getByText('Create lifecycle case',{exact:true}).click().catch(()=>{});
  // Explicitly open the existing disclosure when a previous case is selected.
  await panel.locator('details').filter({has:page.getByText('Create lifecycle case',{exact:true})}).first().evaluate(e=>e.setAttribute('open',''));
  if(retail){await panel.getByLabel('Client knowledge package').selectOption('retail_complaint_fixture:1');await expect(panel.getByLabel('Business process')).toHaveValue('retail_complaint_fixture:1');}
  await panel.getByLabel('Lifecycle investigation goal').fill(retail?'Analyse retail complaint RETAIL-C1 and its order.':'Compare complaint C123 with inspection through its business lifecycle.');
  await panel.getByLabel('complaint id',{exact:true}).fill(retail?'RETAIL-C1':'C123');
  if(retail)await panel.getByLabel('resolution',{exact:true}).selectOption('replacement_proposal');else await panel.getByLabel('resolution path',{exact:true}).selectOption('replacement');
  await panel.getByLabel('monitoring required',{exact:true}).selectOption('true');
  if(!retail)await panel.getByLabel('capa required',{exact:true}).selectOption('true');
  const [created]=await Promise.all([page.waitForResponse(r=>r.request().method()==='POST'&&r.url().endsWith('/cases')),panel.getByRole('button',{name:'Create case',exact:true}).click()]);expect(created.ok(),await created.text()).toBe(true);await expect(panel.getByRole('button',{name:'Prepare',exact:true})).toBeEnabled();
  const id=await panel.getByLabel('Lifecycle case ID').inputValue();await Promise.all([page.waitForResponse(r=>r.request().method()==='POST'&&r.url().endsWith('/prepare')),panel.getByRole('button',{name:'Prepare',exact:true}).click()]);await expect(panel.getByRole('button',{name:'Drive / continue',exact:true})).toBeEnabled();
  let snapshot:BusinessCase|undefined;
  for(let attempt=0;attempt<10;attempt++){
   await panel.getByRole('button',{name:'Drive / continue',exact:true}).click();await expect(panel.getByRole('button',{name:'Refresh status',exact:true})).toBeEnabled({timeout:90000});
   const response=await page.request.get(`/api/backend/business-ontology/v1/cases/${id}`);expect(response.ok()).toBe(true);snapshot=caseSchema.parse((await response.json()).data);
   if(['COMPLETED','COMPLETED_PROVISIONALLY'].includes(snapshot.case_status))break;
   const waiting=Object.values(snapshot.stages).find(s=>s.execution_status==='WAITING_FOR_AUTHORIZATION');
   if(!waiting){
    // A bounded driver command may stop before the next approval. Continue via
    // another explicit UI command; do not increase server execution budgets.
    await expect(panel.getByText(/Driver stopped: budget exhausted/)).toBeVisible();
    continue;
   }
   await panel.getByRole('button',{name:'Agents & tools',exact:true}).click();await panel.getByLabel('Agent stage').selectOption(waiting!.stage_instance_id);
   await expect(panel.getByRole('button',{name:'Validate workflow',exact:true})).toBeEnabled();await panel.getByRole('button',{name:'Validate workflow',exact:true}).click();
   await expect(panel.getByRole('button',{name:'Approve workflow',exact:true})).toBeEnabled();await panel.getByRole('button',{name:'Approve workflow',exact:true}).click();await expect(panel.getByRole('button',{name:'Refresh status',exact:true})).toBeEnabled();
  }
  expect(snapshot?.case_status).toBe('COMPLETED_PROVISIONALLY');await panel.getByRole('button',{name:'Progress',exact:true}).click();await expect(panel.getByTestId('lifecycle-stage')).toHaveCount(retail?8:12);
  await panel.getByRole('button',{name:'Agents & tools',exact:true}).click();await expect(panel.getByRole('button',{name:'Inspect master and specialists'})).toBeVisible();await panel.getByText('Saved tool calls and verified receipts',{exact:true}).click();
  await panel.getByRole('button',{name:'Evidence & assumptions',exact:true}).click();await expect(panel.getByText(/ACTUAL records an identified source/)).toBeVisible();await panel.getByRole('button',{name:'Pending activities',exact:true}).click();await expect(panel.getByRole('heading',{name:'Pending real-world activities'})).toBeVisible();
  await page.reload();await panel.getByLabel('Lifecycle case ID').fill(id);await panel.getByRole('button',{name:'Open case',exact:true}).click();await expect(panel.getByRole('button',{name:'Inspect report'})).toBeVisible();await panel.getByRole('button',{name:'Inspect report'}).click();await expect(panel.getByRole('heading',{name:'Analytical lifecycle report'})).toBeVisible();
  await panel.getByRole('button',{name:'Memory & recovery',exact:true}).click();await expect(panel.getByRole('heading',{name:'Memory, learning and reassessment'})).toBeVisible();
  await page.screenshot({path:`test-results/lifecycle-${retail?'retail':'simpson'}-${mobile?'mobile':'desktop'}.png`,fullPage:true});
 }
 await panel.locator('details').filter({has:page.getByText('Create lifecycle case',{exact:true})}).first().evaluate(e=>e.setAttribute('open',''));
 await panel.getByLabel('Lifecycle investigation goal').fill('Cancellation acceptance only; no business execution.');
 await panel.getByLabel('complaint id',{exact:true}).fill('UI-CANCEL-NONBUSINESS');await panel.getByRole('button',{name:'Create case',exact:true}).click();
 await expect(panel.getByRole('button',{name:'Cancel',exact:true})).toBeEnabled();const cancelledId=await panel.getByLabel('Lifecycle case ID').inputValue();page.once('dialog',d=>d.accept());await panel.getByRole('button',{name:'Cancel',exact:true}).click();await expect(panel.getByRole('button',{name:'Refresh status',exact:true})).toBeEnabled();
 const cancelled=await page.request.get(`/api/backend/business-ontology/v1/cases/${cancelledId}`);expect((await cancelled.json()).data.case_status).toBe('CANCELLED');
 expect(errors).toEqual([]);expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);
});
