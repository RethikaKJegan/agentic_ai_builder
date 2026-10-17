import {test,expect} from "@playwright/test";

// Explicit browser fixtures. Real inference/persistence are covered by Python tests.
for(const mobile of [false,true]) {
  test(`relationship review, reload and descriptions on ${mobile ? "mobile" : "desktop"}`,async({page})=>{
    if(mobile) await page.setViewportSize({width:390,height:844});
    const errors:string[]=[];page.on("pageerror",error=>errors.push(error.message));
    let revision=1;let status="proposed";let description="";
    const nodes=[
      {node_id:"pg",kind:"connection",label:"Supabase",connection_id:"pg",parent_id:null,types:[],discovery_method:"declared",description:""},
      {node_id:"mongo",kind:"connection",label:"Atlas",connection_id:"mongo",parent_id:null,types:[],discovery_method:"declared",description:""},
      {node_id:"orders",kind:"dataset",label:"northwind.orders",connection_id:"pg",parent_id:"pg",types:[],discovery_method:"declared",description:""},
      {node_id:"customers",kind:"dataset",label:"customers",connection_id:"mongo",parent_id:"mongo",types:[],discovery_method:"sampled",description:""},
      {node_id:"of",kind:"field",label:"customerID",connection_id:"pg",parent_id:"orders",types:["text"],discovery_method:"declared",description:""},
      {node_id:"cf",kind:"field",label:"customerID",connection_id:"mongo",parent_id:"customers",types:["string"],discovery_method:"sampled",description:""},
    ];
    await page.route("**/api/backend/**",async route=>{
      const path=new URL(route.request().url()).pathname.replace("/api/backend/","");
      let data:unknown={items:[],total:0,has_more:false,next_cursor:null};
      if(path==="session") data={mode:"local-development",planning_available:false,runtime_available:false,approval_service_available:false,auth:{subject:{subject_id:"test",workspace_id:"test"},roles:["admin"],permissions:["workflow.view","tools.read","tools.assign"],scopes:[],decision:"allow"}};
      else if(path==="data-sources") data={configured:true,shared_demo_identity:false,items:[]};
      else if(path.startsWith("data-relationships")) {
        if(route.request().method()==="POST") {
          const body=route.request().postDataJSON();expect(body.revision).toBe(revision);
          if(path.includes("/review/")) status=body.status;
          if(path.includes("/annotation/")) description=body.description;
          revision++;
        }
        data={stale:false,build_status:"ready",last_error:null,graph:{revision,built_at:"2026-10-18T00:00:00Z",sources:[{connection_id:"pg",revision:1,generation:1},{connection_id:"mongo",revision:1,generation:1}],warnings:[],nodes:nodes.map(node=>({...node,description:node.node_id==="orders"?description:""})),relationships:[{relationship_id:"r",kind:"suggested",source_dataset_id:"orders",target_dataset_id:"customers",field_pairs:[{source_field_id:"of",target_field_id:"cf"}],evidence:["Identifier name and type match; values unverified."],evidence_hash:"h",status,reviewed_at:status==="proposed"?null:"2026-10-18T00:00:00Z"}]}};
      }
      await route.fulfill({status:200,json:{request_id:"req_graph_browser",status:200,data}});
    });
    await page.goto("/app/data-intelligence");await page.getByRole("tab",{name:"Relationships",exact:true}).click();
    await expect(page.getByText("Graph revision 1",{exact:false})).toBeVisible();
    const map=page.getByRole("img",{name:"Dataset relationship map"});
    const fitted=await map.getAttribute("viewBox");
    await expect(page.getByRole("button",{name:"Inspect northwind.orders.customerID"})).toBeVisible();
    await page.getByRole("button",{name:"Zoom in",exact:true}).click();
    await expect(map).not.toHaveAttribute("viewBox",fitted!);
    const zoomed=await map.getAttribute("viewBox");
    await map.scrollIntoViewIfNeeded();
    const box=(await map.boundingBox())!;
    await page.mouse.move(box.x+box.width/2,box.y+20);
    await page.mouse.down();await page.mouse.move(box.x+box.width/2+55,box.y+65,{steps:5});await page.mouse.up();
    await expect(map).not.toHaveAttribute("viewBox",zoomed!);
    await page.getByRole("button",{name:"Fit all"}).click();await expect(map).toHaveAttribute("viewBox",fitted!);
    const viewport=page.getByTestId("relationship-map-viewport");
    expect(await viewport.evaluate(el=>el.scrollHeight===el.clientHeight && el.scrollWidth===el.clientWidth)).toBe(true);
    await page.getByRole("button",{name:"Inspect northwind.orders.customerID"}).click();
    await expect(page.getByRole("heading",{name:"customerID",exact:true})).toBeVisible();
    await map.screenshot({path:`test-results/detailed-map-${mobile?"mobile":"desktop"}.png`});
    await page.getByRole("button",{name:"Accept",exact:true}).click();
    await expect(page.getByRole("button",{name:"Accept",exact:true})).toBeDisabled();
    await page.reload();await page.getByRole("tab",{name:"Relationships",exact:true}).click();
    await expect(page.getByRole("button",{name:"Accept",exact:true})).toBeDisabled();
    await page.getByLabel("Explore dataset").selectOption("orders");
    await page.getByLabel("Business description").fill("Customer sales orders");
    await page.getByRole("button",{name:"Save description"}).click();
    await expect(page.getByText("Description saved.")).toBeVisible();
    await page.getByRole("button",{name:"Reject",exact:true}).click();
    await expect(page.getByRole("button",{name:"Reject",exact:true})).toBeDisabled();
    await page.screenshot({path:`test-results/relationships-${mobile?"mobile":"desktop"}.png`,fullPage:true});
    expect(errors).toEqual([]);
    expect(await page.evaluate(()=>document.documentElement.scrollWidth<=window.innerWidth)).toBe(true);
  });
}
