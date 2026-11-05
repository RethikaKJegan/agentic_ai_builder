"use client";
import { useRef, useState } from "react";
import { ApiError } from "@/api/client";
import { useBackend } from "@/api/state";

// Persist only scoped request digests/keys. Never persist prompts, payloads or tokens.
export async function commandKey(scope: string, operation: string, body: unknown): Promise<string> {
  const digest = await crypto.subtle.digest(
    "SHA-256",
    new TextEncoder().encode(JSON.stringify([scope, operation, body])),
  );
  const slot =
    "mesh-orchestration-v1:" +
    Array.from(new Uint8Array(digest), (n) => n.toString(16).padStart(2, "0")).join("");
  try {
    const previous = sessionStorage.getItem(slot);
    if (previous) return previous;
    const key = crypto.randomUUID();
    sessionStorage.setItem(slot, key);
    return key;
  } catch {
    return crypto.randomUUID();
  }
}
export function useOrchestrationCommand() {
  const session = useBackend((s) => s.session);
  const scope = session
    ? session.auth.subject.workspace_id + ":" + session.auth.subject.subject_id
    : "";
  const lock = useRef(false);
  const keys = useRef(new Map<string, string>());
  const pending = useRef<{
    operation: string;
    body: Record<string, unknown>;
    send: (body: Record<string, unknown>) => Promise<void>;
  } | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<Error | null>(null);
  const [unknown, setUnknown] = useState(false);
  async function act(
    operation: string,
    body: Record<string, unknown>,
    send: (body: Record<string, unknown>) => Promise<void>,
  ) {
    if (lock.current || !scope) return;
    pending.current = { operation, body, send };
    lock.current = true;
    setBusy(true);
    setError(null);
    try {
      const slot = JSON.stringify([scope, operation, body]);
      const request_key = keys.current.get(slot) ?? (await commandKey(scope, operation, body));
      keys.current.set(slot, request_key);
      await send({ ...body, request_key });
      pending.current = null;
      setUnknown(false);
    } catch (e) {
      setError(e instanceof Error ? e : new Error("The response could not be confirmed."));
      setUnknown(!(e instanceof ApiError && e.context.outcome === "rejected"));
    } finally {
      lock.current = false;
      setBusy(false);
    }
  }
  const retry = () => {
    const saved = pending.current;
    if (saved) void act(saved.operation, saved.body, saved.send);
  };
  return { act, busy, error, unknown, setError, retry };
}
