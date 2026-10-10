import { ApiError } from "@/api/client";
export function ApiFeedback({ error, correlationId }: { error?: Error | null | undefined; correlationId?: string | undefined }) {
  return <>
    {error && <div role="alert" className="rounded-lg border border-destructive/30 bg-background px-3 py-2 text-sm text-destructive">
      {error.message}
      {error instanceof ApiError && <p className="mt-1 font-mono text-[11px]">{error.error.error_code}{error.error.field ? ` · ${error.error.field}` : ""} · {error.correlationId ?? error.error.request_id}</p>}
    </div>}
    {correlationId && <p className="text-[11px] text-muted-foreground">Request reference: {correlationId}</p>}
  </>;
}
