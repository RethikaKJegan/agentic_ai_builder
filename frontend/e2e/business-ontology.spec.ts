import { test, expect } from "@playwright/test";
import { readFileSync } from "node:fs";
const fixture=JSON.parse(readFileSync(new URL("./fixtures/business-ontology.json",import.meta.url),"utf8"));

for(const mobile of [false,true])test(`business ontology reviews, evidence and refresh settings on ${mobile?"mobile":"desktop"}`,async({page})=>{
  if(mobile)await page.setViewportSize({width:390,height:844});
  const view=structuredClone(fixture);const errors:string[]=[];page.on("pageerror",e=>errors.push(e.message));
  const setting={connection_id:"pg",name:"Postgres",enabled:true,interval_seconds:300,next_check_at:Date.now()/1000+300,last_attempt_at:null,last_success_at:null,last_change_at:null,consecutive_failures:0,profiling_status:"ready",connection_status:"connected",metadata_revision:1,last_error_message:null};
  let reviews=0,settings=0;
  await page.route("**/api/backend/**",async route=>{
    const path=new URL(route.request().url()).pathname.replace("/api/backend/","");
    let data:unknown={items:[],total:0,has_more:false,next_cursor:null};
    if(path==="session")data={mode:"local-development",planning_available:false,runtime_available:false,approval_service_available:false,auth:{subject:{subject_id:"test",workspace_id:"test"},roles:["admin"],permissions:["workflow.view","tools.read","tools.assign"],scopes:[],decision:"allow"}};
    else if(path==="data-sources")data={configured:true,shared_demo_identity:false,items:[]};
    else if(path==="data-relationships")data={graph:null,stale:false,build_status:"ready",last_error:null};
    else if(path.startsWith("data-ontology")){
      if(route.request().method()==="POST"){
        const body=route.request().postDataJSON();expect(body.revision).toBe(view.revision);
        const edge=view.relationships.find((e:{relationship_id:string})=>e.relationship_id===path.split("/").at(-1));
        edge.predicate=body.predicate;edge.status=body.status;edge.reviewed_at=new Date().toISOString();
        if(edge.reversed!==body.reversed)[edge.source_entity_id,edge.target_entity_id]=[edge.target_entity_id,edge.source_entity_id];
        edge.reversed=body.reversed;view.revision=`review_${++reviews}`;
      }
      data=view;
    }else if(path.startsWith("data-refresh")){
      if(route.request().method()==="POST"){Object.assign(setting,route.request().postDataJSON());settings++;}
      data={version:1,items:[setting]};
    }
    await route.fulfill({status:200,json:{request_id:"req_ontology_browser",status:200,data}});
  });
  await page.goto("/app/data-intelligence");
  await page.getByRole("tab",{name:"Relationships",exact:true}).click();
  await page.getByRole("button",{name:"Knowledge graph",exact:true}).click();
  await expect(page.getByRole("img",{name:"Knowledge graph"})).toBeVisible();
  await page.getByRole("button",{name:"Inspect entity Order",exact:true}).click();
  await expect(page.getByLabel("Knowledge graph details")).toContainText("Postgres / demo / northwind / orders");
  const edge=view.relationships.find((e:{technical_status:string})=>e.technical_status==="declared");
  const names=new Map(view.entities.map((e:{entity_id:string;label:string})=>[e.entity_id,e.label]));
  await page.getByRole("button",{name:`Inspect relationship ${names.get(edge.source_entity_id)} ${edge.predicate} ${names.get(edge.target_entity_id)}`,exact:true}).click();
  await expect(page.getByText("Technical linking fields",{exact:true})).toBeVisible();
  await page.getByLabel("Relationship label",{exact:true}).fill("places");
  await page.getByRole("checkbox",{name:"Reverse business direction"}).check();
  await page.getByRole("button",{name:"Confirm relationship",exact:true}).click();
  await expect.poll(()=>reviews).toBe(1);
  await page.getByRole("button",{name:"Zoom knowledge graph in"}).click();
  await expect(page.getByLabel("Knowledge graph zoom",{exact:true})).toHaveText("130%");
  await page.getByRole("button",{name:"Fit knowledge graph",exact:true}).click();
  await page.getByLabel("Refresh interval seconds",{exact:true}).fill("60");
  await page.getByRole("button",{name:"Save refresh settings",exact:true}).click();
  await expect.poll(()=>settings).toBe(1);
  expect(setting.interval_seconds).toBe(60);
  await page.reload();await page.getByRole("tab",{name:"Relationships",exact:true}).click();
  await page.getByRole("button",{name:"Knowledge graph",exact:true}).click();
  await expect(page.getByRole("button",{name:"Inspect relationship Customer places Order",exact:true})).toBeVisible();
  await expect(page.getByLabel("Refresh interval seconds",{exact:true})).toHaveValue("60");
  expect(await page.evaluate(()=>document.documentElement.scrollWidth<=window.innerWidth)).toBe(true);
  expect(errors).toEqual([]);
  await page.screenshot({path:`test-results/ontology-${mobile?"mobile":"desktop"}.png`,fullPage:true});
});
