import { semanticViewSchema, recordGraphSchema } from "./semantic-kg";
import { knowledgePreviewSchema, type KnowledgeSelection } from "./knowledge-graph";
import { plannedQuerySchema, queryResultSchema, queryStatusSchema, queryJobSchema, queryJobListSchema } from "./data-queries";
import { relationshipViewSchema, detailedViewSchema } from "./data-relationships";
import { databaseOperationSchema, databaseOperationsSchema, databaseRecordSchema, type DatabaseStep } from "./data-operations";
import { databaseConnectionSchema, databaseConnectionsSchema, databaseMetadataSchema, type DatabaseConfig } from "./data-sources";
import { ontologySchema, refreshSchema } from "./data-ontology";
import { safeError } from "./feedback";
import { z } from "zod";
import { assertWorkflowReferences } from "./control";
import {
  ApiResponseSchema, ApiRequestSchema, AuthContextSchema, CanonicalWorkflowSchema, CanonicalToolSchema,
  SafeErrorSchema, RunEventSchema, RunStatusSchema, CollectionSchema,
  type CanonicalWorkflow, type Operation, type SafeError,
} from "./contracts.generated";

function queryString(filters:Record<string, unknown>) {
  const query=new URLSearchParams();
  for(const [key,value] of Object.entries(filters))if(value!==undefined && value!=="")query.set(key,String(value));
  return query.size?`?${query}`:"";
}
const metadata = { correlation_id: z.string().optional(), contract_versions: z.record(z.string()).optional() };
export const registryReviewSchema = z.object({ workflow_id: z.string(), workflow_version: z.number().int().positive(),
  ready: z.boolean(), reason_codes: z.array(z.string()), items: z.array(z.object({
    agent_id: z.string(), agent_version: z.number().int().positive().optional(), capability: z.string().nullable(),
    tool_id: z.string().nullable(), authorization_state: z.enum(["authorized", "pending_approval", "denied"]),
    reason_codes: z.array(z.string()), tool_version: z.number().int().positive().nullable().optional(),
    policy_version: z.number().int().positive().nullable().optional(), approval_required: z.boolean().optional(),
  }).strict()) }).strict();
const workflowData = z.object({ workflow: CanonicalWorkflowSchema, registry_review: registryReviewSchema.optional(), ...metadata });
const toolsData = CollectionSchema.extend({ items: z.array(z.object({
  tool_id: z.string(), definition: CanonicalToolSchema, version: z.number().int().positive(),
  credential_configured: z.boolean(), authorization_state: z.enum(["requires_assignment", "authorized", "pending_approval", "denied"]),
}).passthrough()), ...metadata });
const capabilitiesData = CollectionSchema.extend({ items: z.array(z.object({ capability: z.string(), registered_tool_ids: z.array(z.string()) })), ...metadata });
const workflowsData = CollectionSchema.extend({ items: z.array(CanonicalWorkflowSchema), ...metadata });
export const approvalRecordSchema = z.object({ approval_id: z.string(), workflow_id: z.string(), workflow_version: z.number().int().positive(),
  status: z.enum(["pending", "approved", "rejected", "timed_out", "unmatched"]), action_digest: z.string().nullable().optional(),
  allowed_decisions: z.array(z.enum(["approved", "rejected"])).default([]), required_roles: z.array(z.string()).optional() });
const runData = z.object({ run: z.object({ run_id: z.string(), workflow_id: z.string(), workflow_version: z.number().int().positive(), status: RunStatusSchema,
  approvals: z.array(approvalRecordSchema).default([]) }).passthrough(), ...metadata });
const eventsData = CollectionSchema.extend({ items: z.array(RunEventSchema), ...metadata });
const approvalData = approvalRecordSchema.extend(metadata);
const sessionData = z.object({ planning_jobs_available: z.boolean().optional(), auth: AuthContextSchema, mode: z.string(), planning_available: z.boolean(), runtime_available: z.boolean(), approval_service_available: z.boolean(), ...metadata });
export const workflowOverviewSchema = z.object({ workflow_id: z.string(), name: z.string(), draft_version: z.number().int().positive().nullable(),
  published_version: z.number().int().positive().nullable(), release_id: z.string().nullable(),
  activation_state: z.enum(["preparing", "active", "failed", "disabled", "deleting"]).nullable(),
  active_run_count: z.number().int().nonnegative(), latest_run_id: z.string().nullable(),
  latest_run_status: RunStatusSchema.nullable(), pending_approval_count: z.number().int().nonnegative(), updated_at: z.string() }).strict();
const overviewCollectionSchema = z.object({ items: z.array(workflowOverviewSchema), next_sequence: z.number().int().nonnegative(), has_more: z.boolean(), next_cursor: z.string().nullable().optional(), total: z.number().int().nonnegative().optional(), ...metadata });
const lifecycleOperationSchema = z.object({ operation_id: z.string(), workspace_id: z.string(), workflow_id: z.string(), subject_id: z.string(),
  idempotency_key: z.string(), expected_release_id: z.string().nullable(), kind: z.enum(["activate_release", "disable_release", "delete_workflow"]),
  state: z.enum(["preparing", "succeeded", "failed", "cleanup_pending"]), error_code: z.string().nullable() }).strict();
const releaseSchema = z.object({ release_id: z.string(), workspace_id: z.string(), revision: z.object({ workflow_id: z.string(), workflow_version: z.number().int().positive() }),
  state: z.enum(["preparing", "active", "failed", "disabled", "deleting"]), generation: z.number().int().positive(), automation_identity_id: z.string(),
  agent_versions: z.record(z.string(), z.number().int().positive()), tool_versions: z.record(z.string(), z.number().int().positive()), policy_version: z.number().int().positive(),
  trigger_binding_ids: z.array(z.string()), created_at: z.string() }).strict();
const activationSchema = z.object({ operation: lifecycleOperationSchema, release: releaseSchema, ...metadata });
const lifecycleResultSchema = z.object({ operation: lifecycleOperationSchema, ...metadata });
export type WorkflowOverview = z.infer<typeof workflowOverviewSchema>;

type Ref = { workflow_id: string; workflow_version: number };
export type Payloads = {
  plan_workflow: { objective: string; context?: Record<string, unknown> };
  list_workflows: Record<string, never>;
  get_workflow: { workflow_id: string; workflow_version?: number };
  save_workflow_version: Ref & { workflow: CanonicalWorkflow; base_version: number };
  validate_workflow: Ref;
  approve_workflow: Ref & { action: "approve" | "publish" };
  execute_workflow: Ref & { inputs: Record<string, unknown> };
  get_run: { run_id: string };
  list_run_events: { run_id: string };
  list_tools: Record<string, never>;
  list_capabilities: Record<string, never>;
  decide_approval: { approval_id: string; decision: "approved" | "rejected"; workflow_id: string; workflow_version: number };
};
const responseSchemas = { plan_workflow: workflowData, list_workflows: workflowsData, get_workflow: workflowData,
  save_workflow_version: workflowData, validate_workflow: workflowData, approve_workflow: workflowData,
  execute_workflow: runData, get_run: runData, list_run_events: eventsData, list_tools: toolsData,
  list_capabilities: capabilitiesData, decide_approval: approvalData };
const planningJobSchema = z.object({ job_id: z.string(), state: z.enum(["queued", "running", "succeeded", "failed", "cancelled"]), result: ApiResponseSchema.nullable() });
export type PlanningJob = z.infer<typeof planningJobSchema>;
export type Session = z.infer<typeof sessionData>;
export type ToolRecord = z.infer<typeof toolsData>["items"][number];
export type RegistryReview = z.infer<typeof registryReviewSchema>;
export type ApprovalRecord = z.infer<typeof approvalRecordSchema>;
export type RunRecord = z.infer<typeof runData>["run"];

export const GoogleConnectionSchema=z.object({connection_id:z.string().regex(/^gc_[a-f0-9]{32}$/),account_email:z.string(),granted_scopes:z.array(z.string()),status:z.enum(["connected","verification_failed","reconnect_required","disconnected"]),revision:z.number().int().positive(),created_at:z.string(),updated_at:z.string(),last_verified_at:z.string().nullable(),last_error_code:z.string().nullable(),capabilities:z.record(z.string(),z.boolean())});
export type GoogleConnection=z.infer<typeof GoogleConnectionSchema>;

export class ApiError extends Error {
  public readonly error: SafeError;
  constructor(error: SafeError, public readonly correlationId?: string, public readonly context: {httpStatus?:number;outcome?:"unknown"|"rejected"} = {}) { const sanitized=safeError(error);super(sanitized.message);this.error=sanitized; }

}
function fail(code: string, message: string, requestId = "req_client", retryable = false): never {
  throw new ApiError({ error_code: code, message, request_id: requestId, retryable },undefined, /setting save|approval submission|release activation|release disable|workflow deletion/.test(message)?{outcome:"unknown"}:{});
}
export function containsSecret(value: unknown): boolean {
  if (typeof value === "string") return /\bsk-[\w-]{8,}|Bearer\s+[\w.-]+|:\/\/[^/\s:@]+:[^/\s@]+@|-----BEGIN .*PRIVATE KEY|(?:api[_-]?key|password|secret|token)\s*[:=]\s*\S+/i.test(value);
  if (Array.isArray(value)) return value.some(containsSecret);
  if (value && typeof value === "object") return Object.entries(value).some(([key, child]) => /^(api_key|password|client_secret|access_token|refresh_token|private_key)$/i.test(key) || containsSecret(child));
  return false;
}

function route(operation: Operation, payload: Payloads[Operation]): [string, string] {
  const p = payload as Partial<Ref & { run_id: string; approval_id: string }>;
  const id = encodeURIComponent(p.workflow_id ?? "");
  switch (operation) {
    case "plan_workflow": return ["workflows/plan", "POST"];
    case "list_workflows": return ["workflows", "GET"];
    case "get_workflow": return [`workflows/${id}${p.workflow_version ? `?version=${p.workflow_version}` : ""}`, "GET"];
    case "save_workflow_version": return [`workflows/${id}/versions/${p.workflow_version}`, "PUT"];
    case "validate_workflow": return [`workflows/${id}/validate`, "POST"];
    case "approve_workflow": return [`workflows/${id}/approve`, "POST"];
    case "execute_workflow": return [`workflows/${id}/execute`, "POST"];
    case "list_tools": return ["tools", "GET"];
    case "list_capabilities": return ["agents/capabilities", "GET"];
    case "get_run": return [`runs/${encodeURIComponent(p.run_id ?? "")}`, "GET"];
    case "list_run_events": return [`runs/${encodeURIComponent(p.run_id ?? "")}/events`, "GET"];
    case "decide_approval": return [`approvals/${encodeURIComponent(p.approval_id ?? "")}/decision`, "POST"];
  }
}

async function retryKey(operation: string, payload: unknown, reset = false): Promise<string> {
  // Store only a digest and retry key, never workflow documents, prompts or credentials.
  const digest = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(JSON.stringify({ operation, payload })));
  const slot = "mesh-api-retry-v1:" + Array.from(new Uint8Array(digest), (n) => n.toString(16).padStart(2, "0")).join("");
  try {
    if (reset) localStorage.removeItem(slot);
    const existing = localStorage.getItem(slot);
    if (existing) return existing;
    const key = crypto.randomUUID();
    localStorage.setItem(slot, key);
    return key;
  } catch { return crypto.randomUUID(); }
}

export class WorkflowClient {
  async knowledgeGraph(relationshipId?:string,body?:object) {
    const value=await this.read(relationshipId?`knowledge-graph/review/${encodeURIComponent(relationshipId)}`:"knowledge-graph",relationshipId?{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(body)}:undefined);
    const parsed=semanticViewSchema.safeParse(value);
    if(!parsed.success)return fail("INVALID_API_DATA","The semantic Semantic Intelligence response is invalid.");
    return parsed.data;
  }
  async inferKnowledgeGraph() {
    return semanticViewSchema.parse(await this.read("knowledge-graph/infer",{method:"POST"}));
  }
  async knowledgeRecords(body:object) {
    const parsed=recordGraphSchema.safeParse(await this.read("knowledge-graph/records",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(body)}));
    if(!parsed.success)return fail("INVALID_API_DATA","The actual-record graph response is invalid.");
    return parsed.data;
  }
  async knowledgePreview(objective:string,selection?:KnowledgeSelection) {
    const value=await this.read("knowledge-graph/preview",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({objective,...(selection?{selection}:{})})});
    const parsed=knowledgePreviewSchema.safeParse(value);
    if(!parsed.success)return fail("INVALID_API_DATA","The Semantic Intelligence preview is invalid.");
    return parsed.data;
  }
  async databaseOperations() {
    return databaseOperationsSchema.parse(await this.read("data-operations"));
  }
  async databaseOperation(operationId:string) {
    return databaseOperationSchema.parse(await this.read(`data-operations/${encodeURIComponent(operationId)}`));
  }
  async readDatabaseRecord(body: {connection_id:string;dataset_id:string;identity:Record<string,unknown>}) {
    return databaseRecordSchema.parse(await this.read("data-operations/read",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(body)}));
  }
  async prepareDatabaseOperation(steps:DatabaseStep[],key:string) {
    return databaseOperationSchema.parse(await this.read("data-operations/prepare",{method:"POST",headers:{"Content-Type":"application/json","Idempotency-Key":key},body:JSON.stringify({steps})}));
  }
  async executeDatabaseOperation(operationId:string) {
    return databaseOperationSchema.parse(await this.read(`data-operations/${encodeURIComponent(operationId)}/execute`,{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({confirm:true})}));
  }
  async recoverDatabaseOperation(operationId:string,key:string) {
    return databaseOperationSchema.parse(await this.read(`data-operations/${encodeURIComponent(operationId)}/recover`,{method:"POST",headers:{"Content-Type":"application/json","Idempotency-Key":key},body:"{}"}));
  }
  async dataQueryStatus() {
    const parsed=queryStatusSchema.safeParse(await this.read("data-queries"));
    if(!parsed.success)return fail("INVALID_API_DATA","The query configuration response is invalid.");
    return parsed.data;
  }
  async planDataQuestion(question:string) {
    const parsed=plannedQuerySchema.safeParse(await this.read("data-queries/plan",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({question})}));
    if(!parsed.success)return fail("INVALID_API_DATA","The query plan response is invalid.");
    return parsed.data;
  }
  async executeDataQuestion(planId:string) {
    const parsed=queryResultSchema.safeParse(await this.read("data-queries/execute",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({plan_id:planId})}));
    if(!parsed.success)return fail("INVALID_API_DATA","The query result response is invalid.");
    return parsed.data;
  }

  async submitDataQueryJob(planId:string,key:string) {
    const parsed=queryJobSchema.safeParse(await this.read("data-queries/jobs",{method:"POST",headers:{"Content-Type":"application/json","Idempotency-Key":key},body:JSON.stringify({plan_id:planId})}));
    if(!parsed.success)return fail("INVALID_API_DATA","The query job response is invalid.");
    return parsed.data;
  }
  async dataQueryJobs() {
    const parsed=queryJobListSchema.safeParse(await this.read("data-queries/jobs"));
    if(!parsed.success)return fail("INVALID_API_DATA","The query jobs response is invalid.");
    return parsed.data;
  }
  async dataQueryJob(jobId:string) {
    const parsed=queryJobSchema.safeParse(await this.read(`data-queries/jobs/${encodeURIComponent(jobId)}`));
    if(!parsed.success)return fail("INVALID_API_DATA","The query job response is invalid.");
    return parsed.data;
  }
  async cancelDataQueryJob(jobId:string) {
    const parsed=queryJobSchema.safeParse(await this.read(`data-queries/jobs/${encodeURIComponent(jobId)}/cancel`,{method:"POST"}));
    if(!parsed.success)return fail("INVALID_API_DATA","The query cancellation response is invalid.");
    return parsed.data;
  }
  async dataQueryJobResult(jobId:string) {
    const parsed=queryResultSchema.safeParse(await this.read(`data-queries/jobs/${encodeURIComponent(jobId)}/result`));
    if(!parsed.success)return fail("INVALID_API_DATA","The query result response is invalid.");
    return parsed.data;
  }

  async detailedGraph(nodeId?:string,body?:object) {
    const value=await this.read(nodeId ? `data-relationships/v2/mapping/${encodeURIComponent(nodeId)}` : "data-relationships/v2",nodeId ? {method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(body)} : undefined);
    const parsed=detailedViewSchema.safeParse(value);
    if(!parsed.success)return fail("INVALID_API_DATA","The detailed graph response is invalid.");
    return parsed.data;
  }

  async ontology(relationshipId?:string,body?:object) {
    const value=await this.read(relationshipId?`data-ontology/${encodeURIComponent(relationshipId)}`:"data-ontology",relationshipId?{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(body)}:undefined);
    const parsed=ontologySchema.safeParse(value);
    if(!parsed.success)return fail("INVALID_API_DATA","The Semantic Intelligence response is invalid.");
    return parsed.data;
  }

  async dataRefresh(connectionId?:string,body?:object) {
    const value=await this.read(connectionId?`data-refresh/${encodeURIComponent(connectionId)}`:"data-refresh",connectionId?{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(body)}:undefined);
    const parsed=refreshSchema.safeParse(value);
    if(!parsed.success)return fail("INVALID_API_DATA","The automatic refresh response is invalid.");
    return parsed.data;
  }

  async relationships(action?: "build" | "review" | "annotation", itemId?: string, body?: object) {
    const path = action === "build" ? "data-relationships/build" : action ? `data-relationships/${action}/${encodeURIComponent(itemId ?? "")}` : "data-relationships";
    const parsed = relationshipViewSchema.safeParse(await this.read(path, action ? {method:"POST", headers:{"Content-Type":"application/json"}, body:JSON.stringify(body ?? {})} : undefined));
    if (!parsed.success) return fail("INVALID_API_DATA", "The relationship response is invalid.");
    return parsed.data;
  }

  async dataSources() {
    const parsed=databaseConnectionsSchema.safeParse(await this.read("data-sources"));
    if(!parsed.success)return fail("INVALID_API_DATA","The database connection response is invalid.");
    return parsed.data;
  }
  async databaseMetadata(connectionId:string) {
    const parsed=databaseMetadataSchema.safeParse(await this.read(`data-sources/${encodeURIComponent(connectionId)}/metadata`));
    if(!parsed.success)return fail("INVALID_API_DATA","The database metadata response is invalid.");
    return parsed.data;
  }
  async connectDatabase(config:DatabaseConfig,test=false,connectionId?:string) {
    const result=await this.read(test?"data-sources/test":connectionId?`data-sources/${encodeURIComponent(connectionId)}/credentials`:"data-sources",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(config)});
    const parsed=(test?z.object({success:z.boolean(),message:z.string()}):databaseConnectionSchema).safeParse(result);
    if(!parsed.success)return fail("INVALID_API_DATA","The database connection result is invalid.");
    return parsed.data;
  }
  async databaseAction(connectionId:string,action:"verify"|"refresh-metadata"|"disconnect"|"delete") {
    const parsed=databaseConnectionSchema.safeParse(await this.read(`data-sources/${encodeURIComponent(connectionId)}/${action}`,{method:"POST",headers:{"Content-Type":"application/json"},body:"{}"}));
    if(!parsed.success)return fail("INVALID_API_DATA","The database action result is invalid.");
    return parsed.data;
  }
  private sessionRecovery: Promise<boolean> | null = null;
  private sessionGeneration = 0;
  private sessionMode: string | null = null;
  private planningJobsAvailable = false;
  private planningListeners = new Set<(job: PlanningJob) => void>();
  subscribePlanning(listener: (job: PlanningJob) => void) {
    this.planningListeners.add(listener);
    return () => { this.planningListeners.delete(listener); };
  }
  private reportPlanning(job: PlanningJob) {
    for (const listener of this.planningListeners) listener(job);
  }
  async cancelPlanning(jobId: string) {
    const job = planningJobSchema.safeParse(await this.read(`planning-jobs/${encodeURIComponent(jobId)}`, { method: "DELETE" }));
    if (!job.success) return fail("INVALID_API_DATA", "The cancellation response is invalid.");
    this.reportPlanning(job.data);
    return job.data;
  }
  constructor(private readonly transport: typeof fetch = (...args) => fetch(...args), private readonly base = "/api/backend/") {
    if (base !== "/api/backend/") throw new Error("Use the relative same-origin workflow API path.");
  }
  private async renewLocalSession() {
    if (!this.sessionRecovery) {
      this.sessionRecovery = this.session().then((session) => {
        if (session.mode !== "local-development") return false;
        this.sessionGeneration += 1;
        return true;
      }).finally(() => { this.sessionRecovery = null; });
    }
    return this.sessionRecovery;
  }
  private async read(path: string, options: RequestInit = {}, recoverSession = true): Promise<unknown> {
    const headers=new Headers(options.headers);
    let reference=headers.get("X-Request-ID") ?? new URLSearchParams(path.split("?")[1]).get("request_id");
    if(!reference&&typeof options.body==="string"){try{const parsed=JSON.parse(options.body);if(typeof parsed.request_id==="string")reference=parsed.request_id;}catch{/* Non-JSON bodies never become references. */}}
    if(!reference||!/^[\w-]{1,128}$/.test(reference))reference=crypto.randomUUID();
    headers.set("X-Request-ID",reference);options={...options,headers};
    const mutation=!!options.method && !["GET","HEAD"].includes(options.method.toUpperCase());
    for(let attempt=0;;attempt++){
      try{return await this.readOnce(path,options,recoverSession);}
      catch(error){
        if(!(error instanceof ApiError))throw error;
        if(!mutation && attempt===0 && error.error.retryable && [502,503,504].includes(error.context.httpStatus??0) && ["DATABASE_BUSY","API_DATABASE_BUSY","API_DATABASE_SERIALIZATION_RETRY","API_DATABASE_DEADLOCK","API_DATABASE_UNAVAILABLE","API_TIMEOUT","API_UNAVAILABLE","UPSTREAM_UNAVAILABLE","BACKEND_UNAVAILABLE","PROXY_TIMEOUT","SERVICE_UNAVAILABLE"].includes(error.error.error_code)){
          await new Promise(resolve=>setTimeout(resolve,200));continue;
        }
        if(mutation)throw new ApiError(error.error,error.correlationId,{...error.context,outcome:[400,401,403,404,409,422].includes(error.context.httpStatus??0)?"rejected":"unknown"});
        throw error;
      }
    }
  }
  private async readOnce(path: string, options: RequestInit = {}, recoverSession = true): Promise<unknown> {
    const generation = this.sessionGeneration;
    let response: Response;
    try { response = await this.transport(this.base + path, { credentials: "same-origin", cache: "no-store", ...options }); }
    catch { return fail("API_UNAVAILABLE", "The workflow API is unavailable. Retry when it is connected.", new Headers(options.headers).get("X-Request-ID") ?? "req_client", true); }
    let raw: unknown;
    try { raw = await response.json(); } catch { return fail("INVALID_API_RESPONSE", "The API returned an unusable response."); }
    if (containsSecret(raw)) return fail("UNSAFE_API_RESPONSE", "The API returned unsafe data. Nothing was displayed.");
    const envelope = ApiResponseSchema.safeParse(raw);
    if (!envelope.success) return fail("INVALID_API_RESPONSE", "The API response does not match the accepted envelope.");
    const data = envelope.data.data;
    if (!response.ok || envelope.data.status >= 400) {
      const error = SafeErrorSchema.safeParse(data && !Array.isArray(data) ? data["error"] : null);
      if (!error.success) return fail("INVALID_API_ERROR", "The API did not return a safe error.", envelope.data.request_id);
      // The local middleware rejects an expired cookie before executing actions.
      // Retry only that explicit rejection, preserving the exact original body/key.
      if (recoverSession && (this.sessionMode === null || this.sessionMode === "local-development") &&
          (typeof window === "undefined" || ["localhost", "127.0.0.1", "[::1]"].includes(window.location.hostname)) &&
          path !== "session" && response.status === 401 && error.data.error_code === "AUTHENTICATION_REQUIRED") {
        if (generation !== this.sessionGeneration || await this.renewLocalSession()) return this.readOnce(path, options, false);
      }
      const correlation = data && !Array.isArray(data) && typeof data["correlation_id"] === "string" ? data["correlation_id"] : undefined;
      throw new ApiError(error.data, correlation, {httpStatus:response.status});
    }
    return data;
  }
  async session(): Promise<Session> {
    const result = sessionData.safeParse(await this.read("session"));
    if (!result.success) return fail("INVALID_SESSION", "The session response is invalid.");
    this.sessionMode = result.data.mode;
    this.planningJobsAvailable = result.data.planning_jobs_available === true;
    return result.data;
  }

  async monitoring(cursors:{source_cursor?:string|undefined;policy_cursor?:string|undefined}={}) {
    const count=z.number().finite().nonnegative();
    const schema=z.object({runs:z.object({total:count,active:count,completed:count,failed:count}),events:count,status_breakdown:z.record(z.string(),count).optional(),duration_seconds:z.object({avg:count}).passthrough().optional(),
      usage:z.object({llm_calls:count,tool_calls:count,tokens:count,retries:count,estimated_cost_usd:count}),latest:z.array(z.object({run_id:z.string(),status:RunStatusSchema,correlation_id:z.string(),trace_reference:z.string()})),
      sources:z.array(z.object({binding_id:z.string(),workflow_id:z.string(),provider_id:z.string(),health:z.string(),error_code:z.string().nullable().optional(),baseline_ready:z.boolean(),last_successful_poll:z.string().nullable().optional(),state:z.string().optional(),release_state:z.string().optional(),workflow_version:z.number().optional(),delivery:z.string().optional(),event_type:z.string().optional(),source:z.string().optional(),schedule:z.string().nullable().optional(),timezone:z.string().nullable().optional(),preparation_succeeded:z.boolean().optional()})).optional(),
      policies:z.array(z.object({workflow_id:z.string(),version:z.number().int().positive(),action_approval_required:z.boolean(),scope:z.string().optional(),enforcement:z.string().optional(),policy_version:z.number().nullable().optional(),agents:z.array(z.object({agent_id:z.string(),guardrails:z.record(z.string(),z.boolean()).nullish().transform(value=>value??{}),limits:z.object({max_llm_calls:count,max_tool_calls:count,max_retries:count}).passthrough()}))})).optional(),
      source_next_cursor:z.string().nullable().optional(),policy_next_cursor:z.string().nullable().optional(),audit:z.array(z.object({event_id:z.string(),event_type:z.string(),run_id:z.string(),timestamp:z.string()})).optional(),...metadata});
    const result=schema.safeParse(await this.read(`monitoring${queryString(cursors)}`));
    if(!result.success)return fail("INVALID_API_DATA","The monitoring response is invalid.");
    return result.data;
  }

  async knowledge() {
    const parsed = z.object({ items: z.array(z.record(z.string(), z.unknown())), total: z.number() }).safeParse(await this.read("workspace/knowledge"));
    if (!parsed.success) return fail("INVALID_API_DATA", "The knowledge response is invalid.");
    return parsed.data;
  }
  async settings() {
    const parsed = z.object({ items: z.array(z.object({ key: z.string(), value: z.unknown(), updated_at: z.string() })), total: z.number() }).safeParse(await this.read("workspace/settings"));
    if (!parsed.success) return fail("INVALID_API_DATA", "The settings response is invalid.");
    return parsed.data;
  }
  async saveNotification(value: string) {
    if (containsSecret(value)) return fail("SENSITIVE_DATA_DETECTED", "Keep credentials in server configuration.");
    const parsed = z.object({ key: z.literal("notifications"), value: z.string(), updated_at: z.string() }).safeParse(await this.read("workspace/settings/notifications", {
      method: "PUT", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ value }),
    }));
    if (!parsed.success || parsed.data.value !== value) return fail("INVALID_API_DATA", "The setting save was not confirmed.");
    return parsed.data;
  }
  async googleToolCheckDraft(connectionId:string,toolId:string,inputs:Record<string,unknown>,sheetTargets:unknown[]=[]) {
    const parsed=workflowData.safeParse(await this.read('integrations/google/tool-check-draft',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({connection_id:connectionId,tool_id:toolId,inputs,sheet_targets:sheetTargets})}));
    if(!parsed.success)return fail('INVALID_API_DATA','The Google tool-check draft was not confirmed.');
    return parsed.data;
  }
  async googleConnections() {
    const result=z.object({configured:z.boolean(),setup_message:z.string().nullable(),callback_uri:z.string().nullable(),callback_in_client_file:z.boolean(),shared_demo_identity:z.boolean(),capabilities:z.array(z.string()),items:z.array(GoogleConnectionSchema)}).safeParse(await this.read("integrations/google/connections"));
    if(!result.success)return fail("INVALID_API_DATA","The Google connection list is invalid.");
    return result.data;
  }
  async renameWorkflow(workflowId:string,name:string,expectedName:string) {
    const result=z.object({workflow_id:z.string(),name:z.string().min(1).max(200)}).parse(await this.read(`workflows/${encodeURIComponent(workflowId)}/rename`,{
      method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({name,expected_name:expectedName})}));
    if(result.workflow_id!==workflowId)return fail("REFERENCE_MISMATCH","The renamed workflow did not match the selected workflow.");
    return result;
  }
  async authorizeGoogle(capabilities:string[],connectionId?:string) {
    const path=connectionId?`integrations/google/connections/${encodeURIComponent(connectionId)}/authorize`:"integrations/google/authorize";
    const result=z.object({authorization_url:z.string().url()}).safeParse(await this.read(path,{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({capabilities})}));
    if(!result.success)return fail("INVALID_API_DATA","Google authorization could not be started.");
    const target=new URL(result.data.authorization_url);
    if(target.origin!=="https://accounts.google.com"||target.pathname!=="/o/oauth2/v2/auth")return fail("INVALID_API_DATA","The Google authorization destination is invalid.");
    return result.data;
  }
  async googleConnectionAction(connectionId:string,action:"verify"|"disconnect") {
    const result=GoogleConnectionSchema.safeParse(await this.read(`integrations/google/connections/${encodeURIComponent(connectionId)}/${action}`,{method:"POST",headers:{"Content-Type":"application/json"},body:"{}"}));
    if(!result.success)return fail("INVALID_API_DATA","The Google connection action could not be confirmed.");
    return result.data;
  }

  async integrationCheck(provider: string, mode: "configuration" | "connection" = "configuration") {
    const parsed = z.object({ provider: z.string(), configured: z.boolean(), verified: z.boolean(), tested: z.boolean(),
      state: z.enum(["not_configured", "configured", "verified", "connection_failed"]), live_test_supported: z.boolean(), message: z.string() })
      .safeParse(await this.read(`integrations/${encodeURIComponent(provider)}/test`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ mode }) }));
    if (!parsed.success || parsed.data.provider !== provider || parsed.data.verified !== (parsed.data.state === "verified") || parsed.data.tested !== parsed.data.verified) return fail("INVALID_API_DATA", "The integration check response is invalid.");
    return parsed.data;
  }
  async submitApproval(payload: Ref) {
    const parsed = workflowData.safeParse(await this.lifecycle("submit_workflow_for_approval", `workflows/${encodeURIComponent(payload.workflow_id)}/submit-for-approval`, payload));
    if (!parsed.success) return fail("INVALID_API_DATA", "The approval submission was not confirmed.");
    return parsed.data;
  }

  async procurementCommunication(workflowId: string, version: number) {
    const result = workflowData.safeParse(await this.read(`procurement/workflows/${encodeURIComponent(workflowId)}/${version}/communication`));
    if (!result.success) return fail("INVALID_API_DATA", "The procurement communication response is invalid.");
    return result.data;
  }

  async procurementStatus(projectId: string) {
    const schema = z.object({ project_id: z.string(), phase: z.string(), issues: z.array(z.string()),
      candidates: z.array(z.object({ candidate_id: z.string(), name: z.string(), email: z.string().nullable(),
        categories: z.array(z.string()), assessment: z.string(), contact_state: z.string(),
        evidence: z.array(z.object({ url: z.string(), quote: z.string(), content_sha256: z.string() })) })).default([]),
      shortlist_digest: z.string().nullable().optional(), supplier_mode: z.string().optional(),
      recommendations: z.array(z.object({ scope_digest: z.string(), item_ids: z.array(z.string()), reason: z.string(),
        quotation_id: z.string().nullable(), amount: z.string().nullable(), currency: z.string() }).passthrough()).optional(),
      calendar_events: z.record(z.string(), z.string()).optional(),
      fulfilment_policy: z.object({ revision: z.number(), settings: z.object({ enabled: z.literal(true), buyer_email: z.string(),
        manager_email: z.string(), acceptance_hours: z.number(), reminder_hours: z.number(), allow_delivery_reschedule: z.boolean() }) }).passthrough().nullable().optional(),
      fulfilment_review: z.record(z.string(), z.object({ po_id: z.string(), reason: z.string() })).optional(),
      orders: z.array(z.object({ po_id: z.string(), po_number: z.string(), status: z.string(), tracking_references: z.array(z.string()),
        unresolved_exception_ids: z.array(z.string()), items: z.array(z.object({ item_id: z.string(), unit: z.string(), ordered_quantity: z.string(),
          packed_quantity: z.string(), dispatched_quantity: z.string(), delivered_quantity: z.string(), buyer_accepted_quantity: z.string() }).passthrough()) }).passthrough()).optional(),
      activity: z.array(z.object({ event_id: z.string(), purchase_order_id: z.string(), event_kind: z.string(),
        actor_role: z.string(), note: z.string(), observed_at: z.string() }).passthrough()).optional(),
      records: z.array(z.object({ record_id:z.string(), record_type:z.string(), data:z.record(z.unknown()) }).passthrough()).optional(),
      record_counts: z.record(z.string(), z.number()), resources: z.array(z.object({
        provider: z.string(), resource_type: z.string(), resource_id: z.string(), metadata: z.record(z.string(), z.unknown()),
      }).passthrough()), actions: z.record(z.string(), z.object({ workflow_id: z.string(),
      run_id: z.string().optional(), workflow_version: z.number().int().positive().optional(), state: z.string(), approvals: z.array(approvalRecordSchema).optional(),
      }).passthrough()).default({}) }).passthrough();
    const result = schema.safeParse(await this.read(`procurement/projects/${encodeURIComponent(projectId)}`));
    if (!result.success) return fail("INVALID_API_DATA", "The procurement status response is invalid.");
    return result.data;
  }

  async procurementSuppliersReview(projectId: string, decision: "approved" | "rejected", candidateIds: string[], digest: string) {
    return this.read(`procurement/projects/${encodeURIComponent(projectId)}/suppliers-review`, { method: "POST",
      headers: { "Content-Type": "application/json" }, body: JSON.stringify({ request_id: `req_${crypto.randomUUID()}`,
        operation: "procurement_suppliers_review", idempotency_key: await retryKey("procurement_suppliers_review",{projectId,decision,candidateIds,digest}),
        payload: { decision, candidate_ids: candidateIds, expected_digest: digest } }) });
  }

  async procurementFulfilmentActivate(projectId: string, workflowId: string, version: number, expectedRevision: number,
    settings: { enabled: true; buyer_email: string; manager_email: string; acceptance_hours: number; reminder_hours: number; allow_delivery_reschedule: boolean }) {
    return this.read(`procurement/projects/${encodeURIComponent(projectId)}/fulfilment-activate`, { method: "POST",
      headers: { "Content-Type": "application/json" }, body: JSON.stringify({ request_id: `req_${crypto.randomUUID()}`,
        operation: "procurement_fulfilment_activate", idempotency_key: await retryKey("procurement_fulfilment_activate",{projectId,workflowId,version,expectedRevision,settings}),
        payload: { settings, expected_revision: expectedRevision, workflow_id: workflowId, workflow_version: version } }) });
  }

  async procurementProjectCommunication(workflowId: string, version: number) {
    const schema = z.object({ project_id: z.string(), phase: z.string(), root_workflow: CanonicalWorkflowSchema,
      root_run: runData.shape.run.nullable().optional(), root_events: z.array(RunEventSchema).optional(),
      configured_workflow: CanonicalWorkflowSchema.nullable(), truncated: z.boolean(), actions: z.array(z.object({
        key: z.string(), workflow: CanonicalWorkflowSchema, run: runData.shape.run, events: z.array(RunEventSchema),
      })) });
    const result = schema.safeParse(await this.read(`procurement/workflows/${encodeURIComponent(workflowId)}/${version}/communication-project`));
    if (!result.success) return fail("INVALID_API_DATA", "The project communication response is invalid.");
    return result.data;
  }
  async request<K extends Operation>(operation: K, payload: Payloads[K], idempotencyKey?: string): Promise<z.infer<(typeof responseSchemas)[K]>> {
    if (containsSecret(payload)) return fail("SENSITIVE_DATA_DETECTED", "Remove secret material before submitting.");
    const destination = route(operation, payload);
    let path = destination[0];
    const method = destination[1];
    const requestId = crypto.randomUUID();
    const options: RequestInit = { method };
    if (method !== "GET") {
      options.headers = { "Content-Type": "application/json" };
      options.body = JSON.stringify(ApiRequestSchema.parse({ request_id: requestId, operation, idempotency_key: idempotencyKey ?? await retryKey(operation, payload), payload }));
    } else {
      path += `${path.includes("?") ? "&" : "?"}request_id=${encodeURIComponent(requestId)}`;
    }
    const result = responseSchemas[operation].safeParse(operation === "plan_workflow" && this.planningJobsAvailable
      ? await this.planJob(options) : await this.read(path, options));
    if (!result.success) throw new ApiError({error_code:"INVALID_API_DATA",message:"The returned data does not match the accepted contract.",request_id:requestId,retryable:false},undefined,method!=="GET"?{outcome:"unknown"}:{});
    if ("registry_review" in result.data && result.data.registry_review && "workflow" in result.data) {
      const review = result.data.registry_review as RegistryReview;
      const workflow = result.data.workflow as CanonicalWorkflow;
      if (review.workflow_id !== workflow.workflow_id || review.workflow_version !== workflow.version)
        return fail("REVISION_MISMATCH", "The registry review belongs to a different workflow revision.", requestId);
      const allowed = new Set(workflow.agents.map((agent) => agent.agent_id));
      if (review.items.some((item) => !allowed.has(item.agent_id)) || (review.ready && (review.reason_codes.length > 0 || review.items.some((item) => item.authorization_state !== "authorized"))))
        return fail("INVALID_REGISTRY_REVIEW", "The registry review contains inconsistent authorization data.", requestId);
    }
    if (operation !== "plan_workflow" && "workflow" in result.data && "workflow_id" in payload) {
      const document = result.data.workflow as CanonicalWorkflow;
      if (document.workflow_id !== payload.workflow_id || ("workflow_version" in payload && payload.workflow_version && document.version !== payload.workflow_version)) return fail("REVISION_MISMATCH", "The API returned a different workflow revision.", requestId);
    }
    if ((operation === "get_run" || operation === "execute_workflow") && "run" in result.data) {
      const run = result.data.run as RunRecord;
      if (("run_id" in payload && run.run_id !== payload.run_id) || ("workflow_id" in payload && (run.workflow_id !== payload.workflow_id || run.workflow_version !== payload.workflow_version))) return fail("RUN_MISMATCH", "The API returned a different run reference.", requestId);
    }
    if (operation === "decide_approval" && "approval_id" in result.data && "approval_id" in payload) {
      if (result.data.approval_id !== payload.approval_id || result.data.workflow_id !== payload.workflow_id || result.data.workflow_version !== payload.workflow_version) return fail("APPROVAL_MISMATCH", "The API returned an unmatched approval reference.", requestId);
    }
    try {
      if (operation === "plan_workflow" && "workflow" in result.data) assertWorkflowReferences(result.data.workflow as CanonicalWorkflow);
    } catch (error) { return fail("INVALID_WORKFLOW", error instanceof Error ? error.message : "The workflow graph is invalid.", requestId); }
    return result.data as z.infer<(typeof responseSchemas)[K]>;
  }

  private async planJob(options: RequestInit) {
    let job = planningJobSchema.parse(await this.read("planning-jobs", options));
    this.reportPlanning(job);
    const until = Date.now() + 45 * 60_000;
    while (job.state === "queued" || job.state === "running") {
      if (Date.now() > until) return fail("PLANNING_PENDING", `Planning is still pending. Job reference: ${job.job_id}. Check its status before starting another request.`);
      await new Promise((resolve) => setTimeout(resolve, 1500));
      try { job = planningJobSchema.parse(await this.read(`planning-jobs/${encodeURIComponent(job.job_id)}`)); }
      catch (error) {
        if (error instanceof ApiError) throw new ApiError({ ...error.error,
          message: `${error.message} Planning job: ${job.job_id}. Reconnect and check its status before starting another request.`,
          details: { ...error.error.details, planning_job_id: job.job_id } }, error.correlationId);
        return fail("INVALID_API_DATA", "The planning status response is invalid.");
      }
      this.reportPlanning(job);
    }
    // A confirmed terminal failure/cancellation permits the next explicit user retry
    // to create a new job. Unknown transport outcomes keep the existing retry key.
    if (job.state === "failed" || job.state === "cancelled") {
      const request = JSON.parse(String(options.body)) as { payload: unknown };
      await retryKey("plan_workflow", request.payload, true);
    }
    if (job.state === "cancelled") return fail("PLANNING_CANCELLED", "Workflow generation was cancelled. Your prompt was preserved.");
    if (!job.result) return fail("INVALID_API_DATA", "The planning job has no confirmed result.");
    if (job.result.status >= 400) {
      const data = job.result.data;
      const error = SafeErrorSchema.safeParse(data && !Array.isArray(data) ? data["error"] : null);
      if (!error.success) return fail("INVALID_API_ERROR", "The planning job returned an invalid error.");
      throw new ApiError(error.data);
    }
    return job.result.data;
  }

  async runs(filters: {limit?:number;cursor?:string|undefined;workflow_id?:string;status?:string;from_date?:string;to_date?:string;pending_only?:boolean} = {}) {
    const schema = CollectionSchema.extend({ items: z.array(runData.shape.run), ...metadata });
    const result = schema.safeParse(await this.read(`runs${queryString(filters)}`));
    if (!result.success) return fail("INVALID_API_DATA", "The run collection response is invalid.");
    return result.data;
  }

  async eventPage(runId:string, afterSequence=0, limit=100) {
    const parsed=eventsData.safeParse(await this.read(`runs/${encodeURIComponent(runId)}/events${queryString({after_sequence:afterSequence,limit})}`));
    if(!parsed.success)return fail("INVALID_API_DATA","The run event response is invalid.");
    return parsed.data;
  }

  async releaseState(workflowId: string) {
    const schema = z.object({ workflow_id: z.string(), release: z.object({ release_id: z.string(), workflow_version: z.number().int().positive(), state: z.enum(["preparing", "active", "failed", "disabled", "deleting"]), trigger_binding_count: z.number().int().nonnegative() }).nullable(), ...metadata });
    const result = schema.safeParse(await this.read(`workflows/${encodeURIComponent(workflowId)}/release-state`));
    if (!result.success || result.data.workflow_id !== workflowId) return fail("INVALID_API_DATA", "The release state response is invalid.");
    return result.data;
  }

  async workflowsPage(cursor: string | null = null) {
    const result = workflowsData.safeParse(await this.read("workflows" + (cursor ? `?cursor=${encodeURIComponent(cursor)}` : "")));
    if (!result.success) return fail("INVALID_API_DATA", "The workflow page is invalid.");
    return result.data;
  }

  async overview(afterSequence?: number, cursor: string | null = null) {
    const path = afterSequence === undefined ? "workflow-overview" + (cursor ? `?cursor=${encodeURIComponent(cursor)}` : "") : `workflow-overview/events?after_sequence=${afterSequence}`;
    const result = overviewCollectionSchema.safeParse(await this.read(path));
    if (!result.success) return fail("INVALID_API_DATA", "The workflow overview response is invalid.");
    return result.data;
  }

  async pollTrigger(bindingId: string, changes: Record<string, unknown>[], cursor: string) {
    return this.read(`trigger-bindings/${encodeURIComponent(bindingId)}/poll`, {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ request_id: crypto.randomUUID(), operation: "poll_trigger", idempotency_key: await retryKey("poll_trigger", { bindingId, cursor }), payload: { changes, cursor } }),
    });
  }

  private async lifecycle(operation: string, path: string, payload: Record<string, unknown>, method = "POST") {
    if (containsSecret(payload)) return fail("SENSITIVE_DATA_DETECTED", "Remove secret material before submitting.");
    const body = JSON.stringify({ request_id: crypto.randomUUID(), operation, idempotency_key: await retryKey(operation, payload), payload });
    return this.read(path, { method, headers: { "Content-Type": "application/json" }, body });
  }

  async activateRelease(payload: { workflow_id: string; workflow_version: number; expected_release_id: string | null; triggers?: unknown[] }) {
    const parsed = activationSchema.safeParse(await this.lifecycle("activate_release", `workflows/${encodeURIComponent(payload.workflow_id)}/releases`, { ...payload, triggers: payload.triggers ?? [] }));
    if (!parsed.success) return fail("INVALID_API_DATA", "The release activation response is invalid.");
    return parsed.data;
  }

  async disableRelease(workflowId: string, expectedReleaseId: string | null) {
    const parsed = lifecycleResultSchema.safeParse(await this.lifecycle("disable_release", `workflows/${encodeURIComponent(workflowId)}/disable`, { workflow_id: workflowId, expected_release_id: expectedReleaseId }));
    if (!parsed.success) return fail("INVALID_API_DATA", "The release disable response is invalid.");
    return parsed.data;
  }

  async deleteWorkflow(workflowId: string, expectedReleaseId: string | null) {
    const parsed = lifecycleResultSchema.safeParse(await this.lifecycle("delete_workflow", `workflows/${encodeURIComponent(workflowId)}`, { workflow_id: workflowId, expected_release_id: expectedReleaseId, confirmed: true }, "DELETE"));
    if (!parsed.success) return fail("INVALID_API_DATA", "The workflow deletion response is invalid.");
    return parsed.data;
  }
}
export const api = new WorkflowClient();
