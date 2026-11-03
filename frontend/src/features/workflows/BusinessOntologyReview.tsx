"use client";

import { useRef } from "react";
import { z } from "zod";
import type { CanonicalWorkflow } from "@/api/contracts.generated";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog";
import { displayText } from "@/lib/display-text";

const citation = z.object({ source_id: z.string(), title: z.string(), source_kind: z.string(), source_sha256: z.string(), quote: z.string() });
const reference = z.object({ ref: z.string(), kind: z.string(), label: z.string(), definition: z.string(), evidence: z.array(citation), interpretation_basis: z.string().optional() });
const traceSchema = z.object({
  retrieval_version: z.literal("simpson-business-planning-v1"),
  state: z.enum(["incorporated", "no_match", "not_configured", "no_definitions", "not_authorized"]),
  version_id: z.string().nullable(), revision: z.number().nullable(), definition_sha256: z.string().nullable(),
  references: z.array(reference), contributions: z.array(z.object({ node_id: z.string(), node_name: z.string(), refs: z.array(z.string()), application: z.string() })),
  trace_sha256: z.string(), truncated: z.boolean(),
});

function businessLabel(value: string) {
  return displayText(value.replace(/([a-z0-9])([A-Z])/g, "$1 $2").replace(/_/g, " "));
}
function explanation(value: string) {
  return displayText(value.replace(/\bmaster\b/gi, "coordinator")
    .replace(/engine-instance/gi, "individual engine")
    .replace(/\bsynthesis\b/gi, "final summary")
    .replace(/\bsynthesize\b/gi, "summarize"));
}

export function BusinessOntologyReview({ document }: { document?: CanonicalWorkflow | undefined }) {
  const raw = document?.metadata["business_ontology"];
  if (!raw) return null;
  const parsed = traceSchema.safeParse(raw);
  if (!parsed.success) return <p role="status">Business Ontology evidence could not be read. No incorporation claim is shown.</p>;
  const trace = parsed.data;
  const refs = new Map(trace.references.map(r => [r.ref, r]));
  function download() {
    const url = URL.createObjectURL(new Blob([JSON.stringify(raw, null, 2)], { type: "application/json" }));
    const link = window.document.createElement("a");
    link.href = url;
    link.download = `${document!.workflow_id}-business-ontology-evidence.json`;
    link.click();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  }
  return <section aria-label="Business Ontology contribution" className="min-w-0 space-y-3 rounded-xl border border-primary/30 p-4">
    <h3 className="font-semibold">{trace.state === "incorporated" ? "Business Ontology used in this proposal" : "Business Ontology lookup"}</h3>
    {trace.state === "incorporated" ? <>
      <p>Your saved business knowledge helped shape this workflow. Below, see the meaning it used and how the proposed work applies it.</p>
      <p className="text-xs text-muted-foreground">Business knowledge version {trace.revision} · {new Set(trace.contributions.flatMap(c => c.refs)).size} knowledge references used · {trace.contributions.length} coordinating or action {trace.contributions.length === 1 ? "step" : "steps"} linked</p>
      <div className="space-y-4">{trace.contributions.map(c => {
        const node = document?.nodes.find(n => n.node_id === c.node_id);
        const owner = document?.agents?.find(a => a.agent_id === node?.agent_id);
        const supporting = owner ? document?.agents?.filter(a => a.parent_agent_id === owner.agent_id) ?? [] : [];
        return <article key={c.node_id} className="min-w-0 space-y-4 rounded-lg border p-4">
          <div className="space-y-1"><p className="text-xs font-medium text-muted-foreground">Workflow step</p><h4 className="break-words font-semibold">{displayText(node?.label ?? c.node_name)}</h4></div>
          {!node && <p role="status">This step has since been removed from the draft.</p>}
          <div className="space-y-2"><h5 className="font-medium">How the workflow applies it</h5><p className="break-words">{explanation(c.application)}</p></div>
          {supporting.length > 0 && <details className="text-sm"><summary className="cursor-pointer font-medium">Planned responsibilities ({supporting.length})</summary><ul className="mt-2 space-y-2">{supporting.map(a => <li key={a.agent_id}><strong>{displayText(a.role)}</strong><p>{displayText(a.goal)}</p></li>)}</ul></details>}
          <div className="space-y-2"><h5 className="font-medium">Business knowledge used</h5>
          {c.refs.map(id => {
            const r = refs.get(id);
            if (!r) return <p key={id}>Reference unavailable.</p>;
            return <div key={id} className="min-w-0 space-y-2 rounded-lg bg-muted/40 p-3">
              <h6 className="break-words font-medium">{businessLabel(r.label)}</h6>
              <p className="whitespace-pre-wrap break-words text-sm">{displayText(r.definition)}</p>
              {r.interpretation_basis === "descriptive_implementation" && <p className="text-xs">Describes supplied application behavior; not verified written policy.</p>}
              <details className="min-w-0 text-xs"><summary className="cursor-pointer">View supporting sources ({r.evidence.length})</summary>
              {r.evidence.map((e, i) => <figure key={`${e.source_id}-${i}`} className="mt-2 space-y-2 rounded border bg-background p-3">
                <figcaption className="break-words font-medium">{displayText(e.title)} · {e.source_kind === "application_code" ? "Application reference" : e.source_kind === "blueprint" ? "Business blueprint" : e.source_kind}</figcaption>
                <blockquote className="whitespace-pre-wrap break-words">{displayText(e.quote)}</blockquote>
                <details className="text-muted-foreground"><summary className="cursor-pointer">Technical source details</summary><p className="mt-2 break-all">Source: {e.source_id}<br />SHA-256: {e.source_sha256}</p></details>
              </figure>)}</details>
            </div>;
          })}</div>
        </article>;
      })}</div>
      <p className="text-xs text-muted-foreground">This explains the proposed design. Run results will show which records were read and what the investigation found.</p>
    </> : <p role="status">{trace.state === "not_authorized" ? "This session cannot read the Business Ontology. This proposal did not use it." : trace.state === "not_configured" ? "No Business Ontology is configured for this owner. This proposal did not use one." : trace.state === "no_definitions" ? "The Business Ontology has no saved definitions yet. This proposal did not use business definitions." : "The Business Ontology was searched automatically; no relevant definitions matched this request."}</p>}
    {trace.truncated && <p className="text-xs">The planner received a bounded selection of relevant evidence.</p>}
    <button type="button" className="rounded-lg border px-3 py-2 text-xs" onClick={download}>Download ontology evidence</button>
    <details className="text-xs"><summary className="cursor-pointer">Technical generation details</summary><p className="mt-2 break-all">Definition version: {trace.version_id ?? "None"}<br />Definition SHA-256: {trace.definition_sha256 ?? "None"}<br />Trace SHA-256: {trace.trace_sha256}</p></details>
  </section>;
}


export function BusinessOntologyEvidenceButton({ document }: { document?: CanonicalWorkflow | undefined }) {
  const titleRef = useRef<HTMLHeadingElement>(null);
  const parsed = traceSchema.safeParse(document?.metadata["business_ontology"]);
  if (!parsed.success) return null;
  const trace = parsed.data;
  return <div className="flex shrink-0 flex-wrap items-center justify-between gap-2 border-b bg-background px-4 py-2 text-xs" aria-label="Workflow ontology evidence summary">
    <span>{trace.state === "incorporated" ? `Built using your business knowledge · version ${trace.revision}` : "Business Ontology lookup recorded"}</span>
    <Dialog><DialogTrigger className="rounded-lg border px-3 py-2 hover:bg-muted">View ontology evidence</DialogTrigger>
      <DialogContent onOpenAutoFocus={event => { event.preventDefault(); titleRef.current?.focus(); }} className="max-h-[85dvh] overflow-y-auto sm:max-w-3xl"><DialogHeader><DialogTitle ref={titleRef} tabIndex={-1}>How Business Ontology shaped this workflow</DialogTitle></DialogHeader><BusinessOntologyReview document={document} /></DialogContent>
    </Dialog>
  </div>;
}
