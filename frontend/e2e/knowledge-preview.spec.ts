import {test,expect} from "@playwright/test";
for(const mobile of [false,true])test(`one prompt submits automatic KG planning ${mobile?"mobile":"desktop"}`,async({page})=>{
 if(mobile)await page.setViewportSize({width:390,height:844});
 let plans=0,previews=0,accounts=0;const errors:string[]=[];page.on("pageerror",e=>errors.push(e.message));
 await page.route("**/api/backend/**",async route=>{
  const path=new URL(route.request().url()).pathname.replace("/api/backend/","");
  let data:unknown={items:[],total:0,has_more:false,next_cursor:null};
  if(path==="session")data={mode:"local-development",planning_available:true,runtime_available:false,approval_service_available:false,auth:{subject:{subject_id:"alice",workspace_id:"one"},roles:["admin"],permissions:["workflow.view","workflow.plan","workflow.edit","tools.read","tools.assign"],scopes:["workspace:read"],decision:"allow"}};
  else if(path==="knowledge-graph/preview")previews++;
  else if(path==="integrations/google/connections")accounts++;
  else if(path==="workflows/plan"){
   plans++;const body=route.request().postDataJSON();expect(body.payload.objective).toBe("Review our Northwind inventory");
   expect(body.payload.context).toEqual({generation_mode:"hierarchy",delegation_mode:"runtime_v1",execution_input_mode:"automatic"});
   await route.fulfill({status:503,json:{request_id:"req_auto_kg",status:503,data:{error:{error_code:"MODEL_UNAVAILABLE",message:"The test model is unavailable. Retry generation.",request_id:"req_auto_kg",retryable:false}}}});return;
  }
  await route.fulfill({status:200,json:{request_id:"req_auto_browser",status:200,data}});
 });
 await page.goto("/app");
 await expect(page.getByRole("button",{name:"Preview sources and tools",exact:true})).toHaveCount(0);
 await expect(page.getByRole("combobox")).toHaveCount(0);
 await page.getByRole("textbox",{name:"Process description",exact:true}).fill("Review our Northwind inventory");
 await page.getByRole("button",{name:"Generate workflow",exact:true}).click();
 await expect(page.getByRole("alert").filter({hasText:"The test model is unavailable"})).toBeVisible();
 expect(plans).toBe(1);expect(previews).toBe(0);expect(accounts).toBe(0);
 await expect(page.getByRole("region",{name:"Knowledge graph source preview"})).toHaveCount(0);
 await expect(page.getByRole("textbox",{name:"Process description"})).toHaveValue("Review our Northwind inventory");
 expect(errors).toEqual([]);await page.screenshot({path:`test-results/automatic-kg-${mobile?"mobile":"desktop"}.png`,fullPage:true});
});
