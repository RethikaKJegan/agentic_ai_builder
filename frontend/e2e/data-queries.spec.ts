import {test,expect} from "@playwright/test";
for(const mobile of [false,true]) {
 for(const strategy of ["postgresql","federated"] as const) {
  test(`data question review, result and clarification ${strategy} on ${mobile?"mobile":"desktop"}`,async({page})=>{
    if(mobile)await page.setViewportSize({width:390,height:844});
    const errors:string[]=[];page.on("pageerror",error=>errors.push(error.message));let executions=0;
    await page.route("**/api/backend/**",async route=>{
      const path=new URL(route.request().url()).pathname.replace("/api/backend/","");
      let data:unknown={items:[],total:0,has_more:false,next_cursor:null};
      if(path==="session")data={mode:"local-development",planning_available:false,runtime_available:false,approval_service_available:false,auth:{subject:{subject_id:"test",workspace_id:"test"},roles:["admin"],permissions:["workflow.view","tools.read","tools.assign"],scopes:[],decision:"allow"}};
      else if(path==="data-sources")data={configured:true,shared_demo_identity:false,items:[]};
      else if(path==="data-queries")data={configured:true,max_rows_per_dataset:5000,max_bytes:2000000,max_datasets:4,max_result_rows:500,plan_ttl_seconds:600};
      else if(path==="data-queries/plan") {
        const question=route.request().postDataJSON().question as string;
        data={physical_plan:{strategy,reason:"Validated database aggregate.",operations:["aggregation","result limit"],max_source_rows:1000000,snapshot:strategy==="federated"?"independent source snapshots":"read-only repeatable read"},plan_id:"dq_browser",question,graph_revision:1,created_at:"2026-10-17T00:00:00Z",expires_at:2000000000,field_labels:{},dataset_labels:{orders:"Supabase / orders"},plan:{base_dataset_id:"orders",joins:[],fields:[],filters:[],group_by:[],metrics:[{label:"Order count",op:"count",expression:""}],order_by:[],limit:100,explanation:"Count every order.",clarification:question==="Revenue"?"Should sales include freight?":""}};
      } else if(path==="data-queries/execute"){
        expect(route.request().postDataJSON()).toEqual({plan_id:"dq_browser"});executions++;
        data={execution:{strategy,snapshot:strategy==="federated"?"independent source snapshots":"read-only repeatable read",duration_ms:25,transferred_rows:strategy==="federated"?3:1,transferred_bytes:strategy==="federated"?60:20,...(strategy==="federated"?{fragments:(["complete dimension","complete join key domain","partial aggregates"] as const).map((purpose,index)=>({dataset_ids:[index===0?"categories":"orders"],engine:index===0?"mongodb":"postgresql",purpose,snapshot:index===0?"single-statement snapshot":"read-only repeatable read",started_at:"2026-10-17T00:00:00Z",finished_at:"2026-10-17T00:00:01Z",duration_ms:5,source_rows:index===0?1:830,transferred_rows:1,transferred_bytes:20}))}:{})},plan_id:"dq_browser",columns:[{key:"Order count",label:"Order count"}],rows:[{"Order count":830}],total_result_rows:1,matched_rows:830,limited:false,executed_at:"2026-10-17T00:00:00Z",explanation:"Count every order.",warnings:["Decimal calculations are returned as exact decimal strings."],join_checks:[],sources:[{dataset_id:"orders",label:"Supabase / orders",metadata_revision:1,rows_read:830,started_at:"2026-10-17T00:00:00Z",finished_at:"2026-10-17T00:00:01Z"}]};
      }
      await route.fulfill({status:200,json:{request_id:"req_query_browser",status:200,data}});
    });
    await page.goto("/app/data-intelligence");await page.getByRole("tab",{name:"Questions",exact:true}).click();
    await page.getByLabel("Your data question").fill("Count all orders");await page.getByRole("button",{name:"Create query plan"}).click();
    await expect(page.getByText("Review query plan",{exact:true})).toBeVisible();expect(executions).toBe(0);await expect(page.getByLabel("Execution plan")).toContainText("Validated database aggregate.");
    await page.getByRole("button",{name:"Run read-only query"}).click();await expect(page.getByRole("cell",{name:"830",exact:true})).toBeVisible();
    await expect(page.getByText(/metadata revision 1 · 830 source rows checked/)).toBeVisible();expect(executions).toBe(1);await expect(page.getByLabel("Execution evidence")).toContainText(`${strategy==="federated"?3:1} rows transferred`);
    if(strategy==="federated")await expect(page.getByLabel("Database fragments")).toContainText("partial aggregates");
    await page.screenshot({path:`test-results/data-queries-${strategy}-${mobile?"mobile":"desktop"}.png`,fullPage:true});
    expect(await page.evaluate(()=>document.documentElement.scrollWidth<=window.innerWidth)).toBe(true);
    await page.getByLabel("Your data question").fill("Revenue");await expect(page.getByText("Query results",{exact:true})).toHaveCount(0);
    await page.getByRole("button",{name:"Create query plan"}).click();await expect(page.getByText("Should sales include freight?")).toBeVisible();
    await expect(page.getByRole("button",{name:"Run read-only query"})).toHaveCount(0);expect(executions).toBe(1);expect(errors).toEqual([]);
  });
}

}
