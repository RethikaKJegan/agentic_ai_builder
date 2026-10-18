import {cleanup,fireEvent,render,screen,waitFor} from "@testing-library/react";
import {afterEach,expect,it,vi} from "vitest";
import {api,ApiError} from "@/api/client";
import type {PlannedQuery,QueryResult} from "@/api/data-queries";
import DataQuestions from "./DataQuestions";
const planned=():PlannedQuery=>({plan_id:"dq_one",question:"Count orders",graph_revision:1,created_at:"2026-10-17T00:00:00Z",expires_at:2000000000,field_labels:{},dataset_labels:{orders:"Supabase / orders"},plan:{base_dataset_id:"orders",joins:[],fields:[],filters:[],group_by:[],metrics:[{label:"orders",op:"count",expression:""}],order_by:[],limit:100,explanation:"Count every order.",clarification:""}});
const result:QueryResult={plan_id:"dq_one",columns:[{key:"orders",label:"orders"}],rows:[{orders:830}],total_result_rows:1,matched_rows:830,limited:false,executed_at:"2026-10-17T00:00:00Z",explanation:"Count every order.",warnings:[],join_checks:[],sources:[{dataset_id:"orders",label:"Supabase / orders",metadata_revision:1,rows_read:830,started_at:"2026-10-17T00:00:00Z",finished_at:"2026-10-17T00:00:01Z"}]};
afterEach(()=>{cleanup();vi.restoreAllMocks();});
function setup(){vi.spyOn(api,"dataQueryStatus").mockResolvedValue({configured:true,max_rows_per_dataset:5000,max_bytes:2000000,max_datasets:4,max_result_rows:500,plan_ttl_seconds:600});return vi.spyOn(api,"planDataQuestion").mockResolvedValue(planned());}
it("reviews a grounded plan before executing and shows evidence",async()=>{const plan=setup();const execute=vi.spyOn(api,"executeDataQuestion").mockResolvedValue(result);render(<DataQuestions canManage/>);await waitFor(()=>expect(screen.getByRole("button",{name:"Create query plan"})).toBeDisabled());fireEvent.change(screen.getByLabelText("Your data question"),{target:{value:"Count orders"}});await waitFor(()=>expect(screen.getByRole("button",{name:"Create query plan"})).toBeEnabled());fireEvent.click(screen.getByRole("button",{name:"Create query plan"}));expect(await screen.findByText("Review query plan")).toBeVisible();expect(plan).toHaveBeenCalledWith("Count orders");expect(execute).not.toHaveBeenCalled();fireEvent.click(screen.getByRole("button",{name:"Run read-only query"}));expect(await screen.findByText("830",{selector:"td"})).toBeVisible();expect(execute).toHaveBeenCalledWith("dq_one");expect(screen.getByText(/830 source rows checked/)).toBeVisible();fireEvent.change(screen.getByLabelText("Your data question"),{target:{value:"Another question"}});expect(screen.queryByText("Query results")).toBeNull();});
it("shows clarification without execution",async()=>{const plan=setup();const item=planned();item.plan.clarification="Should sales include freight?";plan.mockResolvedValue(item);render(<DataQuestions canManage/>);fireEvent.change(screen.getByLabelText("Your data question"),{target:{value:"Revenue"}});await waitFor(()=>expect(screen.getByRole("button",{name:"Create query plan"})).toBeEnabled());fireEvent.click(screen.getByRole("button",{name:"Create query plan"}));expect(await screen.findByText("Should sales include freight?")).toBeVisible();expect(screen.queryByRole("button",{name:"Run read-only query"})).toBeNull();});
it("shows execution failure without stale results",async()=>{setup();vi.spyOn(api,"executeDataQuestion").mockRejectedValue(new ApiError({error_code:"DATA_QUERY_JOIN_INVALID",message:"Target keys are duplicated",request_id:"req_test",retryable:false}));render(<DataQuestions canManage/>);fireEvent.change(screen.getByLabelText("Your data question"),{target:{value:"Count"}});await waitFor(()=>expect(screen.getByRole("button",{name:"Create query plan"})).toBeEnabled());fireEvent.click(screen.getByRole("button",{name:"Create query plan"}));fireEvent.click(await screen.findByRole("button",{name:"Run read-only query"}));expect(await screen.findByText("Target keys are duplicated")).toBeVisible();expect(screen.queryByText("Query results")).toBeNull();});
it("disables query creation for readers",async()=>{setup();render(<DataQuestions canManage={false}/>);fireEvent.change(screen.getByLabelText("Your data question"),{target:{value:"Count"}});await screen.findByText(/Planning and querying require/);expect(screen.getByRole("button",{name:"Create query plan"})).toBeDisabled();});

it("shows the physical strategy and actual transfer evidence",async()=>{const request=setup();const item=planned();item.physical_plan={strategy:"postgresql",reason:"Validated database aggregate.",operations:["filters","aggregation","result limit"],max_source_rows:1000000,snapshot:"read-only repeatable read"};request.mockResolvedValue(item);vi.spyOn(api,"executeDataQuestion").mockResolvedValue({...result,execution:{strategy:"postgresql",snapshot:"read-only repeatable read",duration_ms:25,transferred_rows:1,transferred_bytes:20}});render(<DataQuestions canManage/>);fireEvent.change(screen.getByLabelText("Your data question"),{target:{value:"Count orders"}});await waitFor(()=>expect(screen.getByRole("button",{name:"Create query plan"})).toBeEnabled());fireEvent.click(screen.getByRole("button",{name:"Create query plan"}));expect(await screen.findByLabelText("Execution plan")).toHaveTextContent("Validated database aggregate.");fireEvent.click(screen.getByRole("button",{name:"Run read-only query"}));expect(await screen.findByLabelText("Execution evidence")).toHaveTextContent("1 rows transferred");});

it("reviews federation and shows independent fragment read evidence",async()=>{
  const request=setup();const item=planned();item.physical_plan={strategy:"federated",reason:"Complete join checks before weighted aggregate merging.",operations:["partial aggregation","weighted merge","global limit"],max_source_rows:1000000,snapshot:"independent source snapshots"};request.mockResolvedValue(item);
  vi.spyOn(api,"executeDataQuestion").mockResolvedValue({...result,execution:{strategy:"federated",snapshot:"independent source snapshots",duration_ms:35,transferred_rows:6,transferred_bytes:500,fragments:[{dataset_ids:["orders"],engine:"postgresql",purpose:"partial aggregates",snapshot:"read-only repeatable read",started_at:"2026-10-17T00:00:00Z",finished_at:"2026-10-17T00:00:01Z",duration_ms:20,source_rows:6001,transferred_rows:2,transferred_bytes:200}]}});
  render(<DataQuestions canManage/>);fireEvent.change(screen.getByLabelText("Your data question"),{target:{value:"Category sales"}});await waitFor(()=>expect(screen.getByRole("button",{name:"Create query plan"})).toBeEnabled());fireEvent.click(screen.getByRole("button",{name:"Create query plan"}));expect(await screen.findByLabelText("Execution plan")).toHaveTextContent("Federated execution");fireEvent.click(screen.getByRole("button",{name:"Run read-only query"}));expect(await screen.findByLabelText("Database fragments")).toHaveTextContent("6,001 source rows checked");expect(screen.getByLabelText("Database fragments")).toHaveTextContent("2 intermediate rows transferred");
});

function backgroundJob(state:"queued"|"running"|"succeeded"|"failed"|"cancelled"="queued") {
  const current=Date.now()/1000;
  return {job_id:"dqj_"+"a".repeat(32),plan_id:"dq_one",state,attempt:state==="queued"?0:1,created_at:current,updated_at:current,deadline_at:current+180,progress:{stage:state==="succeeded"?"Complete":"Checking complete sources",completed_fragments:0,transferred_rows:0,transferred_bytes:0},result_expires_at:state==="succeeded"?current+900:null,result_available:state==="succeeded",error:state==="failed"?{code:"DATA_QUERY_STALE",message:"Relationship review changed. Create a fresh plan."}:null,planned_query:planned()};
}
function setupJobs(){
  setup();vi.mocked(api.dataQueryStatus).mockResolvedValue({configured:true,max_rows_per_dataset:5000,max_bytes:2000000,max_datasets:4,max_result_rows:500,plan_ttl_seconds:600,jobs_available:true,job_timeout_seconds:180,result_ttl_seconds:900});
  vi.spyOn(api,"dataQueryJobs").mockResolvedValue({items:[]});
  vi.spyOn(api,"dataQueryJobResult").mockResolvedValue(result);
  return vi.spyOn(api,"dataQueryJob").mockResolvedValue(backgroundJob());
}
async function createReviewedPlan(){
  fireEvent.change(screen.getByLabelText("Your data question"),{target:{value:"Count orders"}});
  await waitFor(()=>expect(screen.getByRole("button",{name:"Create query plan"})).toBeEnabled());
  fireEvent.click(screen.getByRole("button",{name:"Create query plan"}));
  await screen.findByText("Review query plan");
}
it("submits a durable job and retrieves only its complete result",async()=>{
  const poll=setupJobs();poll.mockResolvedValueOnce(backgroundJob()).mockResolvedValue(backgroundJob("succeeded"));
  const submit=vi.spyOn(api,"submitDataQueryJob").mockResolvedValue(backgroundJob());const synchronous=vi.spyOn(api,"executeDataQuestion");
  render(<DataQuestions canManage/>);await createReviewedPlan();fireEvent.click(screen.getByRole("button",{name:"Run read-only query"}));
  expect(await screen.findByLabelText("Query job")).toHaveTextContent("queued");expect(screen.queryByText("Query results")).toBeNull();
  expect(await screen.findByText("830",{selector:"td"},{timeout:3000})).toBeVisible();
  expect(submit).toHaveBeenCalledTimes(1);expect(submit.mock.calls[0]![1]).toMatch(/^[a-f0-9-]{36}$/);expect(synchronous).not.toHaveBeenCalled();
});
it("recovers a server-owned job after refresh without resubmitting",async()=>{
  const poll=setupJobs();poll.mockResolvedValue(backgroundJob("succeeded"));vi.mocked(api.dataQueryJobs).mockResolvedValue({items:[backgroundJob("running")]});
  const submit=vi.spyOn(api,"submitDataQueryJob");render(<DataQuestions canManage/>);
  expect(await screen.findByText("830",{selector:"td"})).toBeVisible();expect(submit).not.toHaveBeenCalled();expect(screen.getByLabelText("Your data question")).toHaveValue("Count orders");
});
it("cancels a pending job without displaying rows",async()=>{
  const poll=setupJobs();vi.mocked(api.dataQueryJobs).mockResolvedValue({items:[backgroundJob("running")]});
  const cancel=vi.spyOn(api,"cancelDataQueryJob").mockImplementation(async()=>{const value=backgroundJob("cancelled");poll.mockResolvedValue(value);return value;});
  render(<DataQuestions canManage/>);fireEvent.click(await screen.findByRole("button",{name:"Cancel query"}));
  await waitFor(()=>expect(screen.getByLabelText("Query job")).toHaveTextContent("cancelled"));expect(cancel).toHaveBeenCalledTimes(1);expect(api.dataQueryJobResult).not.toHaveBeenCalled();expect(screen.queryByText("Query results")).toBeNull();
});
it("keeps the submission key after an uncertain network response",async()=>{
  setupJobs().mockResolvedValue(backgroundJob("succeeded"));const submit=vi.spyOn(api,"submitDataQueryJob").mockRejectedValueOnce(new ApiError({error_code:"NETWORK_ERROR",message:"Connection interrupted",request_id:"req_retry",retryable:true})).mockResolvedValue(backgroundJob());
  render(<DataQuestions canManage/>);await createReviewedPlan();fireEvent.click(screen.getByRole("button",{name:"Run read-only query"}));await screen.findByText("Connection interrupted");fireEvent.click(screen.getByRole("button",{name:"Run read-only query"}));
  await screen.findByText("830",{selector:"td"});expect(submit.mock.calls[0]![1]).toBe(submit.mock.calls[1]![1]);
});
it("does not display a result arriving after its retention window",async()=>{
  const poll=setupJobs();const value=backgroundJob("succeeded");value.result_expires_at=Date.now()/1000+.15;poll.mockResolvedValue(value);vi.mocked(api.dataQueryJobs).mockResolvedValue({items:[value]});
  let deliver!:(value:QueryResult)=>void;vi.mocked(api.dataQueryJobResult).mockImplementation(()=>new Promise(resolve=>{deliver=resolve;}));
  render(<DataQuestions canManage/>);await waitFor(()=>expect(api.dataQueryJobResult).toHaveBeenCalled());await screen.findByText(/The temporary result expired/);deliver(result);
  await waitFor(()=>expect(screen.queryByText("830",{selector:"td"})).toBeNull());
});
it("does not overwrite a typed question with late recovery metadata",async()=>{
  setupJobs();let deliver!:(value:{items:ReturnType<typeof backgroundJob>[]})=>void;vi.mocked(api.dataQueryJobs).mockImplementation(()=>new Promise(resolve=>{deliver=resolve;}));
  render(<DataQuestions canManage/>);await waitFor(()=>expect(api.dataQueryJobs).toHaveBeenCalled());fireEvent.change(screen.getByLabelText("Your data question"),{target:{value:"My new question"}});deliver({items:[backgroundJob("running")]});
  await screen.findByText("Recent query jobs");expect(screen.getByLabelText("Your data question")).toHaveValue("My new question");expect(screen.queryByLabelText("Query job")).toBeNull();
});
it("allows status recovery after a polling failure",async()=>{
  const poll=setupJobs();poll.mockRejectedValueOnce(new Error("Status connection lost")).mockResolvedValue(backgroundJob("succeeded"));vi.mocked(api.dataQueryJobs).mockResolvedValue({items:[backgroundJob("running")]});
  render(<DataQuestions canManage/>);fireEvent.click(await screen.findByRole("button",{name:"Retry job status"}));expect(await screen.findByText("830",{selector:"td"})).toBeVisible();
});
it("shows failed job evidence without retrieving rows",async()=>{
  setupJobs().mockResolvedValue(backgroundJob("failed"));vi.mocked(api.dataQueryJobs).mockResolvedValue({items:[backgroundJob("running")]});render(<DataQuestions canManage/>);
  expect(await screen.findByText("Relationship review changed. Create a fresh plan.")).toBeVisible();expect(api.dataQueryJobResult).not.toHaveBeenCalled();expect(screen.queryByText("Query results")).toBeNull();
});
