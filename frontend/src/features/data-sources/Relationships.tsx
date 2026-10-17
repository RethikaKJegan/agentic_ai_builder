"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { GitBranch, RefreshCw } from "lucide-react";
import { api } from "@/api/client";
import { type RelationshipNode, type RelationshipView } from "@/api/data-relationships";
import RelationshipMap from "./RelationshipMap";
import { ApiFeedback } from "@/features/workflows/ApiFeedback";

const button = "rounded-lg border px-3 py-2 text-sm font-medium disabled:opacity-40";
const input = "w-full rounded-lg border bg-background px-3 py-2 text-sm";
const asError = (value: unknown) => value instanceof Error ? value : new Error("Relationship operation could not be confirmed. Reload before retrying.");

function Description({ node, disabled, save }: {node: RelationshipNode; disabled: boolean; save: (description: string) => void}) {
  const [text, setText] = useState(node.description);
  return <form className="mt-3 space-y-2" onSubmit={event => {event.preventDefault(); save(text);}}>
    <label className="block text-sm font-medium" htmlFor="business-description">Business description</label>
    <textarea id="business-description" className={input} rows={3} maxLength={1000} value={text} onChange={event => setText(event.target.value)} disabled={disabled} placeholder="Add your business meaning for this dataset or field."/>
    <p className="text-xs text-muted-foreground">Manually supplied context. Descriptions are never executed as instructions.</p>
    <button className={button} disabled={disabled || text === node.description}>Save description</button>
  </form>;
}

export default function Relationships({canManage}: {canManage: boolean}) {
  const [view, setView] = useState<RelationshipView>();
  const [error, setError] = useState<Error>();
  const [busy, setBusy] = useState(false);
  const [selected, setSelected] = useState("");
  const [filter, setFilter] = useState("all");
  const [search, setSearch] = useState("");
  const [notice, setNotice] = useState("");
  const lock = useRef(false);
  const sequence = useRef(0);
  const load = useCallback(async () => {
    const request = ++sequence.current;
    try {const result = await api.relationships(); if(request === sequence.current) {setView(result); setError(undefined);}}
    catch (failure) {if(request === sequence.current) setError(asError(failure));}
  }, []);
  const invalidate = useCallback(() => {sequence.current++;}, []);
  useEffect(() => {void load(); const timer = setInterval(() => {if(!lock.current) void load();}, 4000); return () => {clearInterval(timer); invalidate();};}, [load, invalidate]);
  async function mutate(action: "build" | "review" | "annotation", id?: string, body?: object) {
    if(lock.current) return;
    lock.current = true; sequence.current++; setBusy(true); setError(undefined);
    try {setView(await api.relationships(action, id, body)); setNotice(action === "build" ? "Graph build requested. The worker will publish a new revision." : action === "annotation" ? "Description saved." : "Review saved.");}
    catch (failure) {setError(asError(failure));}
    finally {lock.current = false; setBusy(false);}
  }
  const graph = view?.graph;
  const nodes = new Map(graph?.nodes.map(node => [node.node_id, node]));
  const datasets = graph?.nodes.filter(node => node.kind === "dataset") ?? [];
  const selectedNode = nodes.get(selected);
  const label = (id: string) => nodes.get(id)?.label ?? id;
  const datasetLabel = (id: string) => {const node = nodes.get(id); return `${label(node?.connection_id ?? "")} / ${label(id)}`;};
  const edges = graph?.relationships.filter(edge => (filter === "all" || edge.status === filter) && (!selected || edge.source_dataset_id === selected || edge.target_dataset_id === selected || edge.field_pairs.some(pair => pair.source_field_id === selected || pair.target_field_id === selected)) && `${datasetLabel(edge.source_dataset_id)} ${datasetLabel(edge.target_dataset_id)} ${edge.field_pairs.map(pair => label(pair.source_field_id)+" "+label(pair.target_field_id)).join(" ")}`.toLowerCase().includes(search.toLowerCase())) ?? [];
  const disabled = busy || !canManage || !!view?.stale;
  return <section aria-label="Data relationships" className="space-y-4">
    <div className="flex flex-wrap items-start justify-between gap-3"><div><h2 className="flex items-center gap-2 text-lg font-semibold"><GitBranch className="h-5 w-5 text-primary"/> Relationships</h2><p className="mt-1 max-w-2xl text-sm text-muted-foreground">Explore declared foreign keys and review suggestions across your connected databases. Suggestions use metadata; values and cardinality have not been checked.</p></div><button className={button} disabled={!canManage || busy || view?.build_status === "queued" || view?.build_status === "running"} onClick={() => void mutate("build")}><RefreshCw className="mr-1 inline h-4 w-4"/>{view?.build_status === "queued" || view?.build_status === "running" ? "Building…" : "Build relationships"}</button></div>
    <ApiFeedback error={error} onRetry={load}/>{notice && <p role="status" className="text-sm">{notice}</p>}
    {!view && !error && <p role="status">Loading relationships…</p>}
    {view?.last_error && <p role="alert" className="rounded-lg border border-destructive p-3 text-sm">{view.last_error}</p>}
    {view?.stale && <p role="status" className="rounded-lg border border-amber-300 p-3 text-sm">Source metadata changed. This graph is historical; rebuild before reviewing or using its relationships.</p>}
    {view && !graph && <p className="rounded-xl border border-dashed p-6 text-sm text-muted-foreground">Build relationships from your successful metadata snapshots. No cloud business rows are read.</p>}
    {graph && <>
      <div className="rounded-xl bg-muted/40 p-4 text-sm"><p className="font-medium">Graph revision {graph.revision} · {datasets.length} datasets · {graph.relationships.length} relationships</p><p className="mt-1 text-xs text-muted-foreground">Built {new Date(graph.built_at).toLocaleString()} · Worker: {view.build_status}</p><details className="mt-2"><summary className="cursor-pointer text-xs">Source metadata revisions ({graph.sources.length})</summary><ul className="mt-2 space-y-1 text-xs">{graph.sources.map(source => <li key={source.connection_id}>{label(source.connection_id)} · revision {source.revision}</li>)}</ul></details></div>
      {graph.warnings.map(warning => <p key={warning} className="rounded-lg border border-amber-300 p-3 text-sm">{warning}</p>)}
      <RelationshipMap graph={graph} selected={selected} onSelect={setSelected}/>
      <div className="grid min-w-0 gap-4 lg:grid-cols-[260px_minmax(0,1fr)]">
        <aside className="min-w-0 space-y-2 rounded-xl border p-3"><label className="block text-sm font-medium" htmlFor="graph-dataset">Explore dataset</label><select id="graph-dataset" className={input} value={selectedNode?.kind === "field" ? selectedNode.parent_id ?? "" : selected} onChange={event => setSelected(event.target.value)}><option value="">All datasets</option>{datasets.map(node => <option key={node.node_id} value={node.node_id}>{datasetLabel(node.node_id)}</option>)}</select>
          {selectedNode && <><h3 className="break-all pt-3 font-medium">{selectedNode.label}</h3><p className="text-xs text-muted-foreground">{selectedNode.kind} · {selectedNode.types.join(", ") || selectedNode.discovery_method}</p><Description key={`${selectedNode.node_id}-${graph.revision}`} node={selectedNode} disabled={disabled} save={description => void mutate("annotation", selectedNode.node_id, {revision: graph.revision, description})}/></>}
          {selectedNode && <div className="max-h-72 space-y-1 overflow-auto pt-3"><p className="text-xs font-medium text-muted-foreground">Fields</p>{graph.nodes.filter(node => node.kind === "field" && node.parent_id === (selectedNode.kind === "field" ? selectedNode.parent_id : selected)).map(node => <button key={node.node_id} className="block w-full break-all rounded-lg p-2 text-left text-xs hover:bg-muted" onClick={() => setSelected(node.node_id)}>{node.label} · {node.types.join(", ")}</button>)}</div>}
        </aside>
        <div className="min-w-0 space-y-3"><div className="flex flex-wrap gap-2"><label className="min-w-48 flex-1"><span className="sr-only">Search relationships</span><input className={input} value={search} onChange={event => setSearch(event.target.value)} placeholder="Search datasets or fields…"/></label><label><span className="sr-only">Relationship status</span><select className={input} value={filter} onChange={event => setFilter(event.target.value)}>{["all", "declared", "proposed", "accepted", "rejected"].map(status => <option key={status} value={status}>{status === "all" ? "All statuses" : status}</option>)}</select></label></div>
          <p className="text-xs text-muted-foreground">{edges.length} matching relationships</p>
          {edges.slice(0,100).map(edge => <article key={edge.relationship_id} className="min-w-0 rounded-xl border p-4"><div className="flex flex-wrap justify-between gap-2"><p className="break-words text-sm font-semibold">{datasetLabel(edge.source_dataset_id)} {edge.kind === "declared" ? "→" : "↔"} {datasetLabel(edge.target_dataset_id)}</p><span className="rounded-full bg-muted px-2 py-1 text-xs">{edge.status}</span></div><ul className="mt-3 space-y-1">{edge.field_pairs.map((pair,index) => <li key={index} className="flex flex-wrap items-center gap-2 text-xs"><button className="break-all text-primary underline" onClick={() => setSelected(pair.source_field_id)}>{label(pair.source_field_id)}</button><span>{edge.kind === "declared" ? "references" : "matches name/type of"}</span><button className="break-all text-primary underline" onClick={() => setSelected(pair.target_field_id)}>{label(pair.target_field_id)}</button></li>)}</ul><details className="mt-3"><summary className="cursor-pointer text-xs font-medium">Evidence and limitations</summary><ul className="mt-2 space-y-2 text-xs text-muted-foreground">{edge.evidence.map((evidence,index) => <li className="break-all" key={index}>{evidence}</li>)}</ul></details>{edge.reviewed_at && <p className="mt-2 text-xs text-muted-foreground">Reviewed {new Date(edge.reviewed_at).toLocaleString()}</p>}{edge.kind === "suggested" && <div className="mt-3 flex flex-wrap gap-2">{([['accepted','Accept'],['rejected','Reject'],['proposed','Reset review']] as const).map(([status,title]) => <button key={status} className={button} disabled={disabled || edge.status === status} onClick={() => void mutate("review", edge.relationship_id, {revision:graph.revision,status})}>{title}</button>)}</div>}</article>)}
          {!edges.length && <p className="rounded-xl border border-dashed p-6 text-sm text-muted-foreground">No relationships match this selection. Only discovered foreign keys and compatible named identifiers across connections produce relationships.</p>}
          {edges.length > 100 && <p className="text-xs text-muted-foreground">Showing the first 100. Select a dataset or narrow your search to inspect more.</p>}
        </div>
      </div>
    </>}
  </section>;
}
