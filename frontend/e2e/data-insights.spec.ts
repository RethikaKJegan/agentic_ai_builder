import {test,expect} from "@playwright/test";
import {readFileSync} from "node:fs";
const graph=JSON.parse(readFileSync(new URL("./fixtures/semantic-kg.json",import.meta.url),"utf8"));
test("metadata EDA desktop overview and connection selection",async({page})=>{
 const errors:string[]=[],mutations:string[]=[];page.on("pageerror",e=>errors.push(e.message));
 const connection=(id:string,engine:string)=>({connection_id:id,name:engine==="mongodb"?"Atlas":"Supabase",engine,host:"test",database:"demo",schemas:["public"],description:"",mode:"direct",connection_status:"connected",profiling_status:"ready",generation:1,metadata_revision:1,created_at:"2026-10-18T00:00:00Z",updated_at:"2026-10-18T00:00:00Z",last_verified_at:null,last_profiled_at:null,last_error_code:null,last_error_message:null});
 const connections=[connection("pg","postgresql"),connection("mongo","mongodb")];
 await page.route("**/api/backend/**",async route=>{
  const r=route.request(),path=new URL(r.url()).pathname.replace("/api/backend/","");if(r.method()!=="GET")mutations.push(path);
  let data:unknown={items:[],total:0,has_more:false,next_cursor:null};
  if(path==="session")data={mode:"local-development",planning_available:true,runtime_available:false,approval_service_available:false,auth:{subject:{subject_id:"alice",workspace_id:"one"},roles:["admin"],permissions:["workflow.view","workflow.plan","tools.read","tools.assign"],scopes:["workspace:read","workspace:write"],decision:"allow"}};
  else if(path==="data-sources")data={configured:true,shared_demo_identity:false,items:connections};
  else if(path==="data-refresh")data={version:1,items:[]};
  else if(path==="knowledge-graph")data=graph;
  else if(path.startsWith("data-sources/")&&path.endsWith("/metadata")){
   const id=path.split("/")[1],c=connections.find(c=>c.connection_id===id)!;
   data={connection:c,snapshot:{connection_id:id,engine:c.engine,revision:1,discovered_at:c.created_at,datasets:graph.datasets.filter((d:{connection_id:string})=>d.connection_id===id).map((d:{dataset_id:string;label:string;fields:{field_id:string;name:string;types:string[]}[]})=>({dataset_id:d.dataset_id,name:d.label.split(" / ").at(-1),database:"demo",schema:id==="pg"?"public":null,kind:id==="pg"?"table":"collection",fields:d.fields.map(f=>({...f,discovery_method:id==="pg"?"declared":"sampled"})),indexes:[],constraints:[],sample_count:id==="mongo"?8:0,discovery_method:id==="pg"?"declared":"sampled"})),warnings:[],coverage:"declared",limits:{},changes:{added:[],removed:[],changed:[]}}};
  }
  await route.fulfill({status:200,json:{request_id:"req_eda_browser",status:200,data}});
 });
 await page.setViewportSize({width:1440,height:1100});await page.goto("/app/data-intelligence");await page.getByRole("tab",{name:"EDA",exact:true}).click();
 await expect(page.getByLabel("Discovered datasets",{exact:true})).toHaveText(graph.datasets.length.toString());
 await expect(page.getByRole("heading",{name:"What your fields look like"})).toBeVisible();
 await expect(page.getByText("Metadata overview · No business-row analysis")).toBeVisible();
 const select=page.getByRole("combobox",{name:"EDA connection",exact:true});await select.selectOption("mongo");
 await expect(page.getByLabel("Discovered datasets",{exact:true})).toHaveText(graph.datasets.filter((d:{connection_id:string})=>d.connection_id==="mongo").length.toString());
 await select.selectOption("");await page.getByRole("button",{name:"Refresh insights",exact:true}).click();
 await expect(page.getByLabel("Discovered datasets",{exact:true})).toHaveText(graph.datasets.length.toString());
 expect(errors).toEqual([]);expect(mutations).toEqual([]);expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);
 await page.screenshot({path:"test-results/eda-desktop.png",fullPage:true});
});
