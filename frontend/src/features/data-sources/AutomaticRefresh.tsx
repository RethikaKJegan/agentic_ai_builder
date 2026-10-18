"use client";
import { useCallback, useEffect, useRef, useState } from "react";
import { api } from "@/api/client";
import type { RefreshView } from "@/api/data-ontology";
import { ApiFeedback } from "@/features/workflows/ApiFeedback";

const control = "rounded-lg border bg-background px-3 py-2 text-sm disabled:opacity-40";
const date = (value: string | null) => (value ? new Date(value).toLocaleString() : "Not yet");
function Settings({
  item,
  disabled,
  save,
}: {
  item: RefreshView["items"][number];
  disabled: boolean;
  save: (enabled: boolean, interval: number) => void;
}) {
  const [enabled, setEnabled] = useState(item.enabled);
  const [interval, setIntervalValue] = useState(item.interval_seconds);
  return (
    <form
      className="flex flex-wrap items-end gap-3"
      onSubmit={(e) => {
        e.preventDefault();
        save(enabled, interval);
      }}
    >
      <label className="flex items-center gap-2 text-sm">
        <input
          type="checkbox"
          checked={enabled}
          disabled={disabled}
          onChange={(e) => setEnabled(e.target.checked)}
        />
        Automatic metadata refresh
      </label>
      <label className="text-sm">
        Interval (seconds)
        <input
          className={`${control} ml-2 w-28`}
          aria-label="Refresh interval seconds"
          type="number"
          min={60}
          max={86400}
          required
          value={interval}
          disabled={disabled}
          onChange={(e) => setIntervalValue(Number(e.target.value))}
        />
      </label>
      <button
        className={control}
        disabled={disabled || !Number.isInteger(interval) || interval < 60 || interval > 86400}
      >
        Save refresh settings
      </button>
    </form>
  );
}
export default function AutomaticRefresh({ canManage }: { canManage: boolean }) {
  const [view, setView] = useState<RefreshView>();
  const [selected, setSelected] = useState("");
  const [error, setError] = useState<Error>();
  const [busy, setBusy] = useState(false);
  const [notice, setNotice] = useState("");
  const serial = useRef(0);
  const lock = useRef(false);
  const load = useCallback(async () => {
    const id = ++serial.current;
    try {
      const v = await api.dataRefresh();
      if (id === serial.current) {
        setView(v);
        setError(undefined);
      }
    } catch (e) {
      if (id === serial.current)
        setError(e instanceof Error ? e : new Error("Refresh status unavailable."));
    }
  }, []);
  const invalidate = useCallback(() => {
    serial.current++;
  }, []);
  useEffect(() => {
    void load();
    const timer = setInterval(() => {
      if (!lock.current) void load();
    }, 4000);
    return () => {
      clearInterval(timer);
      invalidate();
    };
  }, [load, invalidate]);
  const item = view?.items.find((i) => i.connection_id === selected) ?? view?.items[0];
  async function save(enabled: boolean, interval: number) {
    if (!item || lock.current) return;
    lock.current = true;
    serial.current++;
    setBusy(true);
    setNotice("");
    try {
      setView(await api.dataRefresh(item.connection_id, { enabled, interval_seconds: interval }));
      setError(undefined);
      setNotice("Automatic refresh settings saved.");
    } catch (e) {
      setError(e instanceof Error ? e : new Error("Refresh settings could not be saved."));
    } finally {
      lock.current = false;
      setBusy(false);
    }
  }
  return (
    <section aria-label="Automatic metadata refresh" className="space-y-3 rounded-xl border p-4">
      <h3 className="font-semibold">Automatic metadata refresh</h3>
      <p className="text-xs text-muted-foreground">
        Checks discovered structure at the configured interval using the background worker. MongoDB
        samples documents to discover fields; document values are not stored in this catalog.
        Unchanged automatic checks preserve graph revisions.
      </p>
      <ApiFeedback error={error} onRetry={load} />
      {item ? (
        <>
          <label className="block text-sm">
            Refresh connection
            <select
              aria-label="Refresh connection"
              className={`${control} ml-2 max-w-full`}
              value={item.connection_id}
              onChange={(e) => {
                setSelected(e.target.value);
                setNotice("");
              }}
            >
              {view?.items.map((i) => (
                <option key={i.connection_id} value={i.connection_id}>
                  {i.name}
                </option>
              ))}
            </select>
          </label>
          <Settings
            key={item.connection_id}
            item={item}
            disabled={!canManage || busy || item.connection_status === "disconnected"}
            save={(e, i) => void save(e, i)}
          />
          <div className="grid gap-2 text-xs text-muted-foreground sm:grid-cols-2">
            <p>
              Profiling: {item.profiling_status} · Metadata revision {item.metadata_revision}
            </p>
            <p>
              Schedule: {item.enabled ? "Enabled" : "Paused"} · Next check:{" "}
              {item.next_check_at
                ? new Date(item.next_check_at * 1000).toLocaleString()
                : "Not scheduled"}
            </p>
            <p>Last attempted: {date(item.last_attempt_at)}</p>
            <p>Last successful: {date(item.last_success_at)}</p>
            <p>Last discovered change: {date(item.last_change_at)}</p>
          </div>
          {item.last_error_message && (
            <p role="alert" className="text-sm text-destructive">
              {item.last_error_message} Previous successful metadata is retained. Consecutive
              failures: {item.consecutive_failures}; retries use backoff.
            </p>
          )}
        </>
      ) : view ? (
        <p className="text-sm">Connect a database to configure automatic discovery.</p>
      ) : (
        <p role="status">Loading refresh status…</p>
      )}
      {notice && (
        <p role="status" className="text-sm">
          {notice}
        </p>
      )}
    </section>
  );
}
