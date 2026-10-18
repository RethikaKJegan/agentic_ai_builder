import {test,expect} from "@playwright/test";

for(const mobile of [false,true])for(const scenario of ["refresh","cancel","expiry"] as const){
  test(`query jobs ${scenario} on ${mobile?"mobile":"desktop"}`,async({page})=>{
    if(mobile)await page.setViewportSize({width:390,height:844});
    const errors:string[]=[];page.on('pageerror',error=>errors.push(error.message));
    let submitted=false,complete=false,cancelled=false,submissions=0,resultReads=0;
    const created=Date.now()/1000;let expires=created+900;
    const planned={plan_id:"dq_browser",question:"Count orders",graph_revision:1,created_at:new Date().toISOString(),expires_at:created+600,field_labels:{},dataset_labels:{orders:"Supabase / orders"},physical_plan:{strategy:"postgresql",reason:"Validated database count.",operations:["aggregation","result limit"],max_source_rows:1000000,snapshot:"read-only repeatable read"},plan:{base_dataset_id:"orders",joins:[],fields:[],filters:[],group_by:[],metrics:[{label:"orders",op:"count",expression:""}],order_by:[],limit:100,explanation:"Count every order.",clarification:""}};
    function job(){return {job_id:"dqj_"+"b".repeat(32),plan_id:planned.plan_id,state:cancelled?"cancelled":complete?"succeeded":"running",attempt:1,created_at:created,updated_at:Date.now()/1000,deadline_at:created+180,progress:{stage:cancelled?"Cancelled":complete?"Complete":"Checking complete PostgreSQL sources",completed_fragments:complete?1:0,transferred_rows:complete?1:0,transferred_bytes:complete?20:0},result_expires_at:complete?expires:null,result_available:complete&&Date.now()/1000<expires,error:null,planned_query:planned};}
    await page.route('**/api/backend/**',async route=>{
      const path=new URL(route.request().url()).pathname.replace('/api/backend/','');let data:unknown={items:[],total:0,has_more:false,next_cursor:null};let status=200;
      if(path==='session')data={mode:"local-development",planning_available:false,runtime_available:false,approval_service_available:false,auth:{subject:{subject_id:"test",workspace_id:"test"},roles:["admin"],permissions:["workflow.view","tools.read","tools.assign"],scopes:[],decision:"allow"}};
      else if(path==='data-sources')data={configured:true,shared_demo_identity:false,items:[]};
      else if(path==='data-queries')data={configured:true,max_rows_per_dataset:5000,max_bytes:2000000,max_datasets:4,max_result_rows:500,plan_ttl_seconds:600,jobs_available:true,job_timeout_seconds:180,result_ttl_seconds:900};
      else if(path==='data-queries/plan')data=planned;
      else if(path==='data-queries/jobs'){
        if(route.request().method()==='POST'){
          expect(route.request().postDataJSON()).toEqual({plan_id:planned.plan_id});expect(route.request().headers()['idempotency-key']).toMatch(/^[a-f0-9-]{36}$/);submitted=true;submissions++;status=202;data=job();
        }else data={items:submitted?[job()]:[]};
      }else if(path.endsWith('/cancel')){cancelled=true;data=job();}
      else if(path==='data-queries/jobs/dqj_'+"b".repeat(32))data=job();
      else if(path.endsWith('/result')){
        expect(complete&&!cancelled).toBe(true);resultReads++;
        data={plan_id:planned.plan_id,columns:[{key:"orders",label:"orders"}],rows:[{orders:830}],total_result_rows:1,matched_rows:830,limited:false,executed_at:new Date().toISOString(),explanation:"Count every order.",warnings:[],join_checks:[],sources:[{dataset_id:"orders",label:"Supabase / orders",metadata_revision:1,rows_read:830,started_at:new Date().toISOString(),finished_at:new Date().toISOString()}]};
      }else if(path==='data-queries/execute')throw Error('The job UI must not execute synchronously');
      await route.fulfill({status,json:{request_id:"req_jobs_browser",status,data}});
    });
    async function questions(){await page.goto('/app/data-intelligence');await page.getByRole('tab',{name:'Questions',exact:true}).click();}
    await questions();await page.getByLabel('Your data question').fill('Count orders');await page.getByRole('button',{name:'Create query plan'}).click();await page.getByRole('button',{name:'Run read-only query'}).click();
    await expect(page.getByLabel('Query job')).toContainText('running');await expect(page.getByRole('button',{name:'Cancel query'})).toBeVisible();
    if(scenario==='cancel'){
      await page.getByRole('button',{name:'Cancel query'}).click();await expect(page.getByLabel('Query job')).toContainText('cancelled');expect(resultReads).toBe(0);
      await questions();await expect(page.getByLabel('Query job')).toContainText('cancelled');await expect(page.getByText('Query results',{exact:true})).toHaveCount(0);
    }else{
      if(scenario==='refresh'){await questions();await expect(page.getByLabel('Query job')).toContainText('running');}
      complete=true;if(scenario==='expiry')expires=Date.now()/1000+2;
      await expect(page.getByRole('cell',{name:'830',exact:true})).toBeVisible();
      if(scenario==='expiry'){
        await expect(page.getByText(/The temporary result expired/)).toBeVisible({timeout:5000});await expect(page.getByRole('cell',{name:'830',exact:true})).toHaveCount(0);
        const reads=resultReads;await questions();await expect(page.getByText(/The temporary result expired/)).toBeVisible();expect(resultReads).toBe(reads);
      }
    }
    expect(submissions).toBe(1);await page.getByLabel('Query job').scrollIntoViewIfNeeded();await page.screenshot({path:`test-results/query-jobs-${scenario}-${mobile?"mobile":"desktop"}.png`,fullPage:true});
    expect(await page.evaluate(()=>document.documentElement.scrollWidth<=window.innerWidth)).toBe(true);expect(errors).toEqual([]);
  });
}
