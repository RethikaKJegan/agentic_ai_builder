import { displayText } from "@/lib/display-text";
import { ApiError } from "@/api/client";
import { InputError, unsafeText, type FeedbackKind } from "@/api/feedback";
export function ApiFeedback({ error, correlationId, onRetry, retrying = false }: { error?: Error | null | undefined; correlationId?: string | undefined; onRetry?: (()=>void) | undefined; retrying?: boolean | undefined }) {
  const apiError=error instanceof ApiError?error:undefined;
  const code=apiError?.error.error_code;
  const kind:FeedbackKind=apiError?.context.outcome==="unknown"?"uncertain":code==="AUTHENTICATION_REQUIRED"?"unauthorized":code==="OPERATION_NOT_AUTHORIZED"||code==="ORIGIN_NOT_AUTHORIZED"?"forbidden":code?.includes("CONFLICT")?"conflict":apiError?.error.retryable?"retryable":"error";
  const message=apiError?.message??(error instanceof InputError&&!unsafeText(error.message)?error.message:"This action could not be confirmed. Keep your edits and use a safe read to check the current state.");
  const requirements=apiError&&Array.isArray(apiError.error.details?.["requirements"])?apiError.error.details["requirements"].filter((item):item is string=>typeof item==="string"&&!unsafeText(item)):[];
  return <>
    {error&&<div role="alert" data-feedback-state={kind} className="rounded-lg border border-destructive/30 bg-background px-3 py-2 text-sm text-destructive">
      <p>{displayText(message)}</p>
      {kind==="uncertain"&&<p className="mt-1">Outcome unknown. The server may have accepted this action. Check its current revision, operation or run before repeating it. No automatic mutation retry was submitted.</p>}
      {kind==="unauthorized"&&<p className="mt-1">Your session is unavailable. Reconnect the local workspace to recover it; production login remains separately configured.</p>}
      {kind==="forbidden"&&<p className="mt-1">Your account or origin lacks access. Contact your workspace administrator; repeating the action will not grant permission.</p>}
      {kind==="conflict"&&<p className="mt-1">The server state changed. Keep your working draft and compare or reload the latest revision before continuing.</p>}
      {apiError?.error.field&&<p className="mt-1" aria-label="Validation field">Field: {apiError.error.field}</p>}
      {error instanceof InputError&&error.field&&<p className="mt-1" aria-label="Validation field">Field: {error.field}</p>}
      {!!apiError?.error.related_errors?.length&&<ul aria-label="Field errors" className="mt-2 list-disc pl-5">{apiError.error.related_errors.map((item,index)=><li key={index}>{item.field?`${item.field}: `:""}{displayText(item.message)} · {item.error_code}</li>)}</ul>}
      {requirements.length>0&&<ul className="mt-2 list-disc space-y-1 pl-5" aria-label="Publication requirements">{requirements.map((item,index)=><li key={index}>{item}</li>)}</ul>}
      {apiError&&<p className="mt-1 font-mono text-[11px]">{code} · Request {apiError.error.request_id}{apiError.correlationId&&/^[\w-]{1,128}$/.test(apiError.correlationId)?` · Correlation ${apiError.correlationId}`:""}</p>}
      {onRetry&&kind!=="uncertain"&&kind!=="forbidden"&&<button type="button" disabled={retrying} onClick={onRetry} className="mt-2 rounded border px-3 py-1 text-sm disabled:opacity-40">{retrying?"Loading…":"Retry read"}</button>}
    </div>}
    {correlationId&&/^[\w-]{1,128}$/.test(correlationId)&&<p className="text-[11px] text-muted-foreground">Request reference: {correlationId}</p>}
  </>;
}
