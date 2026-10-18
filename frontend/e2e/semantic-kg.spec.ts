import {test,expect} from "@playwright/test";
import {readFileSync} from "node:fs";
const semantic=JSON.parse(readFileSync(new URL("./fixtures/semantic-kg.json",import.meta.url),"utf8"));
for(const mobile of [false,true])test(`essential Knowledge graph ${mobile?"mobile":"desktop"}`,async({page})=>{
 if(mobile)await page.setViewportSize({width:390,height:844});
 let builds=0,saves=0,reviews=0;const view=structuredClone(semantic);const unexpected:string[]=[],errors:string[]=[];
 page.on("pageerror",e=>errors.push(e.message));
 const item={connection_id:"pg",name:"Postgres",enabled:true,interval_seconds:300,next_check_at:null,last_attempt_at:null,last_success_at:null,last_change_at:null,consecutive_failures:0,profiling_status:"ready",connection_status:"connected",metadata_revision:1,last_error_message:null};
 await page.route("**/api/backend/**",async route=>{
  const r=route.request(),path=new URL(r.url()).pathname.replace("/api/backend/","");
  let data:unknown={items:[],total:0,has_more:false,next_cursor:null};
  if(path==="session")data={mode:"local-development",planning_available:true,runtime_available:false,approval_service_available:false,auth:{subject:{subject_id:"alice",workspace_id:"one"},roles:["admin"],permissions:["workflow.view","workflow.plan","tools.read","tools.assign"],scopes:["workspace:read","workspace:write"],decision:"allow"}};
  else if(path==="data-sources")data={configured:true,shared_demo_identity:false,items:[]};
  else if(path==="knowledge-graph")data=view;
  else if(path.startsWith("knowledge-graph/review/")){
   const body=r.postDataJSON();expect(body.revision).toBe(view.revision);
   const edge=view.relationships.find((e:{relationship_id:string})=>e.relationship_id===path.split("/").at(-1));
   expect(edge.status).toBe("ambiguous");edge.predicate=body.predicate;edge.status=body.status;edge.reversed=body.reversed;edge.reviewed_at=new Date().toISOString();view.revision="reviewed";reviews++;data=view;
  }
  else if(path==="data-refresh")data={version:1,items:[item]};
  else if(path==="data-refresh/pg"){
   const body=r.postDataJSON();expect(body).toEqual({enabled:false,interval_seconds:60});saves++;data={version:1,items:[{...item,...body}]};
  }else if(path==="data-relationships/build"){builds++;data={graph:null,stale:false,build_status:"queued",last_error:null};}
  else if(r.method()!=="GET")unexpected.push(path);
  await route.fulfill({status:200,json:{request_id:"req_essential_browser",status:200,data}});
 });
 await page.goto("/app/data-intelligence");
 await page.getByRole("tab",{name:"Knowledge graph",exact:true}).click();
 const graph=page.getByRole("img",{name:"Knowledge graph",exact:true});await expect(graph).toBeVisible();
 for(const name of ["Actual records","Entity types","Generate semantic relationships","Relationship map","Detailed knowledge graph","Confirm relationship"])
  await expect(page.getByRole("button",{name,exact:true})).toHaveCount(0);
 const details=page.getByLabel("Knowledge graph details");
 await expect(details).toContainText("Inspect");
 const edge=semantic.relationships[0];const names=new Map(semantic.entities.map((e:{entity_id:string;label:string})=>[e.entity_id,e.label]));
 await page.getByRole("button",{name:`Relationship ${names.get(edge.source_entity_id)} ${edge.predicate} ${names.get(edge.target_entity_id)}`,exact:true}).locator("rect").click();
 await expect(details).toContainText("Evidence trace");await expect(details).toContainText("structural_relationship_id");
 await page.getByRole("button",{name:"Entity Customer",exact:true}).focus();await page.keyboard.press("Enter");
 await expect(details).toContainText("Atlas");
 await page.getByRole("button",{name:/^Relationship .*meaning needs review/}).first().focus();await page.keyboard.press("Enter");
 await page.getByLabel("Relationship label",{exact:true}).fill("matches");
 await page.getByRole("button",{name:"Confirm relationship",exact:true}).click();
 await expect.poll(()=>reviews).toBe(1);await expect(details).toContainText("Business: confirmed");
 await page.getByRole("button",{name:"Entity Customer",exact:true}).locator("ellipse").click();
 const links=graph.locator('g[aria-label^="Relationship "]');await expect(links).toHaveCount(4);
 const connection=page.getByRole("combobox",{name:"Knowledge graph connection",exact:true});
 await connection.selectOption("pg");await expect(links).toHaveCount(1);
 await connection.selectOption("mongo");await expect(links).toHaveCount(0);await expect(details).not.toContainText("Postgres");
 await connection.selectOption("");await expect(links).toHaveCount(4);
 await page.getByLabel("Semantic relationship status",{exact:true}).selectOption("inferred");await expect(links).toHaveCount(1);
 await page.getByLabel("Search knowledge graph",{exact:true}).fill("unrelated-payroll");await expect(page.getByText(/No entities match/)).toBeVisible();
 await page.getByLabel("Search knowledge graph",{exact:true}).fill("");
 await page.getByRole("button",{name:"Regenerate KG",exact:true}).click();await expect.poll(()=>builds).toBe(1);
 await page.getByLabel("Refresh interval seconds",{exact:true}).fill("60");
 await page.getByRole("checkbox",{name:"Automatic metadata refresh",exact:true}).uncheck();
 await page.getByRole("button",{name:"Save refresh settings",exact:true}).click();await expect.poll(()=>saves).toBe(1);
 expect(unexpected).toEqual([]);expect(errors).toEqual([]);
 expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);
 await page.screenshot({path:`test-results/essential-kg-${mobile?"mobile":"desktop"}.png`,fullPage:true});
});
