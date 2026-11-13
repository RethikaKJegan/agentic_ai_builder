"use client";
import { useState } from "react";
import { PageHeader } from "@/features/runs/RunTrace";
import { ServerRunView } from "@/features/runs/ServerRunView";
import { RunMonitoring } from "@/features/runs/RunMonitoring";
import { ReplyCases } from "@/features/runs/ReplyCases";
export default function Screen() {
  const [status, setStatus] = useState("");
  return (
    <div className="mx-auto max-w-7xl p-6 md:p-10">
      <PageHeader
        title="Runs"
        sub="Server run status and event history for an exact workflow revision."
      />
      <RunMonitoring onStatus={setStatus}>
        <ServerRunView summaryStatus={status} />
        <ReplyCases />
      </RunMonitoring>
    </div>
  );
}
