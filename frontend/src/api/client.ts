import { z } from "zod";
import { assertWorkflowReferences } from "./control";
import {
  ApiResponseSchema, ApiRequestSchema, AuthContextSchema, CanonicalWorkflowSchema, CanonicalToolSchema,
  SafeErrorSchema, RunEventSchema, RunStatusSchema, CollectionSchema,
  type CanonicalWorkflow, type Operation, type SafeError,
} from "./contracts.generated";

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
  status: z.enum(["pending", "approved", "rejected", "timed_out", "unmatched"]), action_digest: z.string().optional(),
  allowed_decisions: z.array(z.enum(["approved", "rejected"])).default([]) });
const runData = z.object({ run: z.object({ run_id: z.string(), workflow_id: z.string(), workflow_version: z.number().int().positive(), status: RunStatusSchema,
  approvals: z.array(approvalRecordSchema).default([]) }).passthrough(), ...metadata });
const eventsData = CollectionSchema.extend({ items: z.array(RunEventSchema), ...metadata });
const approvalData = approvalRecordSchema.extend(metadata);
const sessionData = z.object({ auth: AuthContextSchema, mode: z.string(), planning_available: z.boolean(), runtime_available: z.boolean(), approval_service_available: z.boolean(), ...metadata });
export const workflowOverviewSchema = z.object({ workflow_id: z.string(), name: z.string(), draft_version: z.number().int().positive().nullable(),
  published_version: z.number().int().positive().nullable(), release_id: z.string().nullable(),
  activation_state: z.enum(["preparing", "active", "failed", "disabled", "deleting"]).nullable(),
  active_run_count: z.number().int().nonnegative(), latest_run_id: z.string().nullable(),
  latest_run_status: RunStatusSchema.nullable(), pending_approval_count: z.number().int().nonnegative(), updated_at: z.string() }).strict();
const overviewCollectionSchema = z.object({ items: z.array(workflowOverviewSchema), next_sequence: z.number().int().nonnegative(), has_more: z.boolean(), ...metadata });
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
export type Session = z.infer<typeof sessionData>;
export type ToolRecord = z.infer<typeof toolsData>["items"][number];
export type RegistryReview = z.infer<typeof registryReviewSchema>;
export type ApprovalRecord = z.infer<typeof approvalRecordSchema>;
export type RunRecord = z.infer<typeof runData>["run"];

export class ApiError extends Error {
  constructor(public readonly error: SafeError, public readonly correlationId?: string) { super(error.message); }
}
function fail(code: string, message: string, requestId = "req_client", retryable = false): never {
  throw new ApiError({ error_code: code, message, request_id: requestId, retryable });
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

async function retryKey(operation: string, payload: unknown): Promise<string> {
  // Store only a digest and retry key, never workflow documents, prompts or credentials.
  const digest = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(JSON.stringify({ operation, payload })));
  const slot = "mesh-api-retry-v1:" + Array.from(new Uint8Array(digest), (n) => n.toString(16).padStart(2, "0")).join("");
  try {
    const existing = localStorage.getItem(slot);
    if (existing) return existing;
    const key = crypto.randomUUID();
    localStorage.setItem(slot, key);
    return key;
  } catch { return crypto.randomUUID(); }
}

export class WorkflowClient {
  private sessionRecovery: Promise<boolean> | null = null;
  private sessionGeneration = 0;
  constructor(private readonly transport: typeof fetch = (...args) => fetch(...args), private readonly base = "/api/backend/") {}
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
    const generation = this.sessionGeneration;
    let response: Response;
    try { response = await this.transport(this.base + path, { credentials: "same-origin", cache: "no-store", ...options }); }
    catch { return fail("API_UNAVAILABLE", "The workflow API is unavailable. Retry when it is connected.", "req_client", true); }
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
      if (recoverSession && path !== "session" && response.status === 401 && error.data.error_code === "AUTHENTICATION_REQUIRED") {
        if (generation !== this.sessionGeneration || await this.renewLocalSession()) return this.read(path, options, false);
      }
      const correlation = data && !Array.isArray(data) && typeof data["correlation_id"] === "string" ? data["correlation_id"] : undefined;
      throw new ApiError(error.data, correlation);
    }
    return data;
  }
  async session(): Promise<Session> {
    const result = sessionData.safeParse(await this.read("session"));
    if (!result.success) return fail("INVALID_SESSION", "The session response is invalid.");
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
    const result = responseSchemas[operation].safeParse(await this.read(path, options));
    if (!result.success) return fail("INVALID_API_DATA", "The returned data does not match the accepted contract.", requestId);
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

  async runs() {
    const schema = CollectionSchema.extend({ items: z.array(runData.shape.run), ...metadata });
    const result = schema.safeParse(await this.read("runs"));
    if (!result.success) return fail("INVALID_API_DATA", "The run collection response is invalid.");
    return result.data;
  }

  async overview(afterSequence?: number) {
    const path = afterSequence === undefined ? "workflow-overview" : `workflow-overview/events?after_sequence=${afterSequence}`;
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
