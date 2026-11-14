"use client";
import { useEffect, useRef, useState } from "react";
import { api, type GoogleConnection } from "@/api/client";
import { useBackend } from "@/api/state";
import { useMesh } from "@/domain/store";
import type { Workflow } from "@/domain/types";
import { toCanonical } from "@/api/mapping";
import { editSnapshot, acceptConfirmed } from "./workflow-state";
import { ApiFeedback } from "./ApiFeedback";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
} from "@/components/ui/select";
import { Loader2 } from "lucide-react";

const connectionLabel: Record<string, string> = {
  connected: "Connected",
  verification_failed: "Verification failed",
  reconnect_required: "Reauthorization required",
  disconnected: "Disconnected",
};
function GoogleMark() {
  return (
    <svg aria-hidden="true" viewBox="0 0 24 24" className="h-5 w-5 shrink-0">
      <path
        fill="#4285F4"
        d="M22 12.2c0-.7-.1-1.4-.2-2.1H12v4h5.6a4.8 4.8 0 0 1-2.1 3.1v2.6h3.4c2-1.8 3.1-4.4 3.1-7.6Z"
      />
      <path
        fill="#34A853"
        d="M12 22c2.8 0 5.2-.9 6.9-2.5l-3.4-2.6c-.9.6-2.1 1-3.5 1-2.7 0-5-1.8-5.8-4.3H2.7v2.7A10.4 10.4 0 0 0 12 22Z"
      />
      <path fill="#FBBC05" d="M6.2 13.6a6.2 6.2 0 0 1 0-3.2V7.7H2.7a10 10 0 0 0 0 8.6l3.5-2.7Z" />
      <path
        fill="#EA4335"
        d="M12 6.1c1.6 0 3 .6 4.1 1.6l3.1-3A10 10 0 0 0 2.7 7.7l3.5 2.7A6.1 6.1 0 0 1 12 6.1Z"
      />
    </svg>
  );
}
export function GoogleAccountSelect({
  value,
  onChange,
  disabled = false,
}: {
  value: string;
  onChange: (id: string) => void;
  disabled?: boolean;
}) {
  const session = useBackend((s) => s.session);
  const connected = useBackend((s) => s.status === "connected");
  const scope = JSON.stringify(session?.auth.subject);
  const [items, setItems] = useState<GoogleConnection[]>([]);
  const [error, setError] = useState<Error>();
  const [loading, setLoading] = useState(true);
  const [retry, setRetry] = useState(0);
  useEffect(() => {
    let live = true;
    setItems([]);
    setError(undefined);
    setLoading(true);
    if (connected)
      api
        .googleConnections()
        .then((data) => {
          if (live) setItems(data.items);
        })
        .catch((e) => {
          if (live) setError(e instanceof Error ? e : new Error("Accounts could not be loaded."));
        })
        .finally(() => {
          if (live) setLoading(false);
        });
    else setLoading(false);
    return () => {
      live = false;
    };
  }, [connected, scope, retry]);
  const selected = items.find((item) => item.connection_id === value);
  return (
    <div className="space-y-2">
      <p className="text-xs font-medium">Google account</p>
      <Select
        value={value || "none"}
        disabled={disabled || !connected || loading || !!error}
        onValueChange={(id) => onChange(id === "none" ? "" : id)}
      >
        <SelectTrigger
          aria-label="Workflow Google account"
          className="h-auto min-h-12 rounded-xl bg-background px-3 py-2"
        >
          <div className="flex min-w-0 items-center gap-3">
            <span aria-hidden="true" data-google-icon><GoogleMark /></span>
            {loading ? (
              <span className="inline-flex items-center gap-2 text-sm">
                <Loader2 className="h-4 w-4 animate-spin" />
                Loading accounts…
              </span>
            ) : (
              <span className="min-w-0 truncate text-sm">{selected?.account_email ?? (value ? "Selected connection unavailable" : "Choose a Google account")}</span>
            )}
          </div>
        </SelectTrigger>
        <SelectContent>
          <SelectItem value="none">Choose a Google account</SelectItem>
          {value && !selected && (
            <SelectItem value={value} disabled>
              Selected connection unavailable
            </SelectItem>
          )}
          {items.map((item) => (
            <SelectItem
              key={item.connection_id}
              value={item.connection_id}
              disabled={item.status !== "connected"}
            >
              <span className="inline-flex items-center gap-3">
                <span aria-hidden="true" data-google-icon><GoogleMark /></span>
                <span className="text-sm">
                  {item.account_email}
                  <span className="ml-2 text-xs text-muted-foreground">
                    {connectionLabel[item.status] ?? item.status}
                  </span>
                </span>
              </span>
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
      {!loading && !error && items.length === 0 && (
        <p className="text-xs text-muted-foreground">
          No Google accounts connected. Add one in Integrations.
        </p>
      )}
      {selected && selected.status !== "connected" && (
        <p role="status" className="text-xs">
          {connectionLabel[selected.status]}. Check this account in Integrations before running.
        </p>
      )}
      <ApiFeedback error={error} onRetry={() => setRetry((n) => n + 1)} />
    </div>
  );
}

export function GoogleWorkflowConnection({ workflow }: { workflow: Workflow }) {
  const backend = useBackend();
  const current =
    typeof workflow.canonical?.metadata["google_connection_id"] === "string"
      ? workflow.canonical.metadata["google_connection_id"]
      : "";
  const [selected, setSelected] = useState(current);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<Error>();
  const pending = useRef(false);
  useEffect(() => {
    setSelected(current);
  }, [current]);
  const save = async () => {
    if (pending.current) return;
    pending.current = true;
    setBusy(true);
    setError(undefined);
    try {
      const state = useMesh.getState();
      const latest = state.workflows.find((w) => w.id === workflow.id) ?? workflow;
      const snapshot = editSnapshot(latest, state.agents);
      const document = toCanonical(latest, state.agents);
      if (selected) document.metadata["google_connection_id"] = selected;
      else delete document.metadata["google_connection_id"];
      const result = await api.request("save_workflow_version", {
        workflow_id: document.workflow_id,
        workflow_version: document.version,
        base_version: latest.serverVersion ?? 0,
        workflow: document,
      });
      acceptConfirmed(result.workflow, snapshot);
      await backend.refreshOverview();
    } catch (e) {
      setError(e instanceof Error ? e : new Error("Google binding could not be saved."));
    } finally {
      pending.current = false;
      setBusy(false);
    }
  };
  return (
    <section className="space-y-3 rounded-xl border p-4" aria-label="Workflow Google binding">
      <h2 className="text-sm font-semibold">Google connection for this revision</h2>
      <GoogleAccountSelect
        value={selected}
        onChange={setSelected}
        disabled={busy || !backend.can("workflow.edit") || !backend.can("tools.assign")}
      />
      <p className="text-xs text-muted-foreground">
        Saving creates a draft revision. Run, review and publish it through the normal workflow
        controls. Existing runs keep their original account.
      </p>
      <button
        disabled={
          busy ||
          selected === current ||
          !backend.can("workflow.edit") ||
          !backend.can("tools.assign")
        }
        onClick={() => void save()}
        className="rounded-lg bg-primary px-3 py-2 text-xs text-primary-foreground disabled:opacity-40"
      >
        {busy ? "Saving…" : "Save account binding"}
      </button>
      <ApiFeedback error={error} />
    </section>
  );
}
