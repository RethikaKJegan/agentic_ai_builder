"use client";
import { KnowledgeSelectionMap } from "./KnowledgeSelectionMap";
import type { KnowledgePreview } from "@/api/knowledge-graph";

export function KnowledgeSourcePreview({view,selected,onSelect,disabled=false}:{view:KnowledgePreview;selected?:string[];onSelect?:(ids:string[])=>void;disabled?:boolean}) {
  const chosen=selected??view.source_ids;
  const labels=new Map(view.candidates.map(s=>[s.dataset_id,s.label]));
  return <section aria-label="Knowledge graph source preview" className="mt-5 min-w-0 space-y-3 rounded-xl border border-border bg-canvas p-4 text-sm">
    <h2 className="font-semibold">Knowledge graph context</h2>
    <p>Searched saved metadata across {view.coverage.connections} connections and {view.coverage.datasets} datasets. {view.source_ids.length} sources selected for planning; up to four are supported.</p>
    <p className="text-xs text-muted-foreground">Metadata indexed {new Date(view.indexed_at).toLocaleString()}. This preview reads no business records. Tool availability still requires Registry authorization and any required approval.</p>
    {view.requires_selection&&<p role="status" className="rounded-lg border border-amber-300 p-3">Choose the intended sources, then refresh the preview before generating.</p>}
    <div className="grid min-w-0 gap-3 sm:grid-cols-2">{view.candidates.map(source=><article key={source.dataset_id} className={`min-w-0 rounded-lg border p-3 ${chosen.includes(source.dataset_id)?"border-primary bg-primary/5":"border-border"}`}>
      <label className="flex items-start gap-2 font-medium"><input type="checkbox" checked={chosen.includes(source.dataset_id)} disabled={!onSelect||disabled||(!chosen.includes(source.dataset_id)&&chosen.length>=4)} onChange={e=>onSelect?.(e.target.checked?[...chosen,source.dataset_id]:chosen.filter(id=>id!==source.dataset_id))}/><span className="break-words">{source.label}</span></label>
      <p className="mt-1 text-xs text-muted-foreground">{source.engine} · {source.operations.join(", ")} · relevance {source.score}</p>
      <ul className="mt-2 list-inside list-disc text-xs">{source.reasons.map(reason=><li key={reason}>{reason}</li>)}</ul>
      <details className="mt-2 text-xs"><summary className="cursor-pointer">Fields (up to 64)</summary><p className="mt-1 break-words">{source.fields.join(", ")}</p></details>
    </article>)}</div>
    {!view.source_ids.length&&<p>No database source was selected. Use dataset names or confirmed business concepts if this workflow needs database records.</p>}
    <KnowledgeSelectionMap view={view}/>
    {!!view.semantic_relationships?.length&&<div aria-label="Semantic planning evidence" className="space-y-1">{view.semantic_relationships.map(e=><p key={e.relationship_id} className="text-xs">{labels.get(e.reversed?e.target_dataset_id:e.source_dataset_id)} → <strong>{e.predicate}</strong> → {labels.get(e.reversed?e.source_dataset_id:e.target_dataset_id)} · {e.status}</p>)}</div>}
    <div aria-label="Selected relationship paths" className="space-y-2"><h3 className="font-medium">Selected relationship paths</h3>{view.relationships.map(edge=><p key={edge.relationship_id} className="rounded-lg border border-primary/30 p-2 break-words">{labels.get(edge.source_dataset_id)??edge.source_dataset_id} <span className="font-semibold">→ technical link →</span> {labels.get(edge.target_dataset_id)??edge.target_dataset_id} · {edge.status}<span className="mt-1 block text-xs text-muted-foreground">{edge.field_pairs.map(p=>`${p.source_field_id} → ${p.target_field_id}`).join("; ")}</span></p>)}{!view.relationships.length&&<p className="text-xs text-muted-foreground">No executable relationship path in this selection.</p>}</div>
    <details><summary className="cursor-pointer font-medium">Available configured tools and capabilities ({view.tools.length})</summary><ul className="mt-2 space-y-2">{view.tools.map(tool=><li key={tool.tool_id} className="break-words text-xs"><strong>{tool.tool_id}</strong> · {tool.capability}{tool.approval_required?" · approval required":""}<p className="text-muted-foreground">{tool.description}</p></li>)}</ul></details>
    {view.warnings.map(warning=><p key={warning} className="rounded-lg border border-amber-300 p-2 text-xs">{warning}</p>)}
  </section>;
}
