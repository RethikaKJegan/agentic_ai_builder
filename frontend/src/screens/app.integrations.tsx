"use client";
import { DatabaseConnectionsSummary } from "@/features/data-sources/DataIntelligence";
import { useBackend } from "@/api/state";
import { GoogleToolChecks } from "@/features/workflows/GoogleToolChecks";
import { GoogleConnections } from "@/features/workflows/GoogleConnections";
import { ApiFeedback } from "@/features/workflows/ApiFeedback";

export default function Integrations() {
  const backend = useBackend();
  return <div className="mx-auto max-w-5xl px-6 py-10">
    <h1 className="text-3xl font-semibold">Integrations</h1>
    <p className="mt-2 text-sm text-muted-foreground">Add a Google account and choose access to Gmail, Sheets and Calendar. Manage each account’s permissions below.</p>
    <GoogleConnections />
    <GoogleToolChecks />
    <DatabaseConnectionsSummary />
    <ApiFeedback error={backend.error} />
    {backend.status !== "connected" && <p role="status" className="mt-4 text-sm text-muted-foreground">Connect to the backend to manage your integrations.</p>}
  </div>;
}
