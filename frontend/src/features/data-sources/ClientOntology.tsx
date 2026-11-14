"use client";
import { DisplayTime } from "@/lib/display-preferences";
import "@xyflow/react/dist/style.css";
import { useEffect, useMemo, useRef, useState } from "react";
import dagre from "@dagrejs/dagre";
import {
  ReactFlow,
  ReactFlowProvider,
  Background,
  Controls,
  Handle,
  Position,
  MarkerType,
  type NodeProps,
  type Node,
} from "@xyflow/react";
import { Network, Layers3, Search, ChevronRight } from "lucide-react";
import { api } from "@/api/client";
import { InputError } from "@/api/feedback";
import { useBackend } from "@/api/state";
import type { BusinessOntologyState } from "@/api/business-ontology";
import type { KnowledgeSnapshot } from "@/api/knowledge-map";
import { ApiFeedback } from "@/features/workflows/ApiFeedback";
const label = (s: string) => s.replaceAll("_", " ").replace(/([a-z])([A-Z])/g, "$1 $2");
type ConceptNode = Node<{ label: string; area: string; count?: number }, "concept">;
function Card({ data, selected }: NodeProps<ConceptNode>) {
  return (
    <div
      className={`w-[230px] rounded-xl border bg-background p-4 shadow-sm ${selected ? "border-primary ring-2 ring-primary/20" : "border-border"}`}
    >
      <Handle position={Position.Left} type="target" />
      <p className="text-[10px] uppercase tracking-wider text-muted-foreground">{data.area}</p>
      <p className="mt-2 text-sm font-semibold">{data.label}</p>
      {data.count !== undefined && (
        <p className="mt-2 text-xs text-primary">{data.count} concepts · Expand →</p>
      )}
      <Handle position={Position.Right} type="source" />
    </div>
  );
}
const nodeTypes = { concept: Card };
function Saved({ value }: { value: unknown }) {
  return (
    <pre className="mt-2 max-h-72 overflow-auto whitespace-pre-wrap break-words text-xs">
      {JSON.stringify(value, null, 2)}
    </pre>
  );
}
export default function ClientOntology() {
  const subject = useBackend((s) => s.session?.auth.subject);
  return <Workspace key={JSON.stringify(subject)} />;
}
function Workspace() {
  const [loaded, setLoaded] = useState<{
    ontology: BusinessOntologyState;
    snapshot: KnowledgeSnapshot;
  } | null>(null);
  const [error, setError] = useState<Error>();
  const [retry, setRetry] = useState(0);
  const [version,setVersion]=useState("");
  const [query, setQuery] = useState("");
  const canvasRef = useRef<HTMLDivElement>(null);
  const [columns, setColumns] = useState(3);
  useEffect(() => {
    const element = canvasRef.current;
    if (!element) return;
    const resize = () => setColumns(element.clientWidth < 600 ? 1 : 3);
    resize();
    const observer = new ResizeObserver(resize);
    observer.observe(element);
    return () => observer.disconnect();
  }, [loaded]);
  const [expanded, setExpanded] = useState<string[]>([]);
  const [selected, setSelected] = useState<string | null>(null);
  useEffect(() => {
    let live = true;
    setError(undefined);
    async function read() {
      try {
        const ontology = await api.businessOntology();
        if (!live) return;
        if (!ontology.current_version_id)
          throw new InputError(
            "No saved ontology is available. Create or review it in Business Ontology.",
          );
        const selectedVersion=version||ontology.current_version_id;
        if(version&&!ontology.versions.some(v=>v.version_id===version))throw new InputError("This ontology version is unavailable in the authenticated workspace.");
        const snapshot = await api.knowledgeSnapshot(selectedVersion);
        if (snapshot.version_id !== selectedVersion)
          throw new InputError("Ontology version changed. Refresh to try again.");
        if (live) setLoaded({ ontology, snapshot });
      } catch (e) {
        if (live) setError(e instanceof Error ? e : new Error("Ontology unavailable."));
      }
    }
    void read();
    return () => {
      live = false;
    };
  }, [retry,version]);
  const areas = useMemo(
    () => (loaded ? [...new Set(loaded.snapshot.modules?.map(m=>m.id)??loaded.snapshot.concepts.map((c) => c.module_id))] : []),
    [loaded],
  );
  const areaLabel = (id: string) =>
    loaded?.snapshot.modules?.find(m=>m.id===id)?.label ?? loaded?.ontology.modules.find((m) => m.id === id)?.label ?? label(id);
  const graph = useMemo(() => {
    if (!loaded) return { nodes: [] as ConceptNode[], edges: [] };
    const { snapshot } = loaded;
    const search = query.trim().toLowerCase();
    const visible = snapshot.concepts.filter((c) =>
      search
        ? `${c.label} ${c.definition} ${c.module_id}`.toLowerCase().includes(search)
        : expanded.includes(c.module_id),
    );
    const ids = new Set(visible.map((c) => c.id));
    const nodes: ConceptNode[] = visible.map((c) => ({
      id: c.id,
      type: "concept",
      position: { x: 0, y: 0 },
      data: {
        label: c.label,
        area:
          loaded.ontology.modules.find((m) => m.id === c.module_id)?.label ?? label(c.module_id),
      },
    }));
    if (!search && expanded.length === 0)
      for (const area of areas)
        if (!expanded.includes(area))
          nodes.push({
            id: "area:" + area,
            type: "concept",
            position: { x: 0, y: 0 },
            data: {
              label: loaded.ontology.modules.find((m) => m.id === area)?.label ?? label(area),
              area: "Business area",
              count: snapshot.concepts.filter((c) => c.module_id === area).length,
            },
          });
    const edges = snapshot.relationships
      .filter((r) => ids.has(r.source) && ids.has(r.target))
      .map((r) => ({
        id: r.id,
        source: r.source,
        target: r.target,
        label: r.label || r.predicate,
        type: "smoothstep",
        markerEnd: { type: MarkerType.ArrowClosed },
        style: { stroke: "#64748b" },
        labelStyle: { fontSize: 11 },
      }));
    const connected = new Set(edges.flatMap((edge) => [edge.source, edge.target]));
    const linked = nodes.filter((node) => connected.has(node.id));
    const layout = new dagre.graphlib.Graph();
    layout.setGraph({ rankdir: "LR", nodesep: 44, ranksep: 120 });
    layout.setDefaultEdgeLabel(() => ({}));
    linked.forEach((node) => layout.setNode(node.id, { width: 230, height: 126 }));
    edges.forEach((edge) => layout.setEdge(edge.source, edge.target));
    if (linked.length) dagre.layout(layout);
    linked.forEach((node) => {
      const point = layout.node(node.id);
      node.position = { x: point.x - 115, y: point.y - 63 };
    });
    const gridTop = linked.length ? Math.max(...linked.map((node) => node.position.y)) + 186 : 0;
    nodes
      .filter((node) => !connected.has(node.id))
      .forEach((node, index) => {
        node.position = {
          x: (index % columns) * 290,
          y: gridTop + Math.floor(index / columns) * 156,
        };
      });
    return { nodes, edges };
  }, [loaded, query, expanded, areas, columns]);
  const concept = loaded?.snapshot.concepts.find((c) => c.id === selected);
  const connections =
    loaded?.snapshot.relationships.filter((r) => r.source === selected || r.target === selected) ??
    [];
  const mappings =
    loaded?.snapshot.source_mappings ?? loaded?.snapshot.knowledge?.source_mappings ?? [];
  const rules = loaded?.snapshot.rules.filter((r) => r.inputs.includes(selected ?? "")) ?? [];
  const records=(value:unknown):Record<string,unknown>[]=>Array.isArray(value)?value.filter((v):v is Record<string,unknown>=>!!v&&typeof v==='object'):[];
  const knowledge=loaded?.snapshot.knowledge;
  const extensionRules=records(knowledge?.['structured_rules']);
  const allRuleIds=new Set([...(loaded?.snapshot.rules.map(r=>r.id)??[]),...extensionRules.flatMap(r=>typeof r['id']==='string'?[r['id']]:[])]);
  const selectedMappings=mappings.filter(m=>m.concept_id===selected);
  const matchesBinding=(binding:unknown)=>!!binding&&typeof binding==='object'&&selectedMappings.some(m=>m.collection===(binding as Record<string,unknown>)['collection']&&m.source_role===(binding as Record<string,unknown>)['source_role']);
  const identities=records(knowledge?.['identity_rules']).filter(r=>matchesBinding(r['source'])||matchesBinding(r['target']));
  const states=records(knowledge?.['state_models']).filter(r=>r['concept_id']===selected);
  const dates=records(knowledge?.['temporal_models']).filter(r=>r['concept_id']===selected);
  const dependencies=records(knowledge?.['dependencies']).filter(r=>r['subject_id']===selected);
  const extension=knowledge?.['manifest'] as Record<string,unknown>|undefined;
  const savedVersion=loaded?.ontology.versions.find(v=>v.version_id===loaded.snapshot.version_id);
  const overview=[['Business concepts',new Set(loaded?.snapshot.concepts.map(c=>c.id)).size],['Relationships',new Set(loaded?.snapshot.relationships.map(r=>r.id)).size],['Business rules',allRuleIds.size],['Business areas',areas.length]] as const;

  return (
    <section className="min-w-0 space-y-4" aria-label="Complete client ontology">
      <header>
        <p className="flex items-center gap-2 text-xs uppercase tracking-widest text-primary">
          <Network size={16} />
          Your business, connected
        </p>
        <h2 className="mt-2 text-2xl font-semibold">
          {loaded?.ontology.workspace?.title ?? "Client ontology"}
        </h2>
        <p className="mt-2 text-sm text-muted-foreground">
          Explore saved business concepts, relationships, rules and data sources.
        </p>
      </header>
      <ApiFeedback error={error} onRetry={() => setRetry((n) => n + 1)} />
      {!loaded && !error && <p role="status">Loading your workspace ontology…</p>}
      {loaded && (
        <>
          <div aria-label="Ontology overview statistics" className="grid grid-cols-2 gap-3 lg:grid-cols-4">{overview.map(([name,count])=><section key={name} aria-label={name} className="rounded-xl border bg-background p-4"><p className="text-xs text-muted-foreground">{name}</p><p className="mt-2 text-2xl font-semibold">{count}</p></section>)}</div>
          <p className="text-xs text-muted-foreground">Counts use unique saved definition IDs in the selected version, including its knowledge-extension rules. Rules describe support; they are not proof of a passed execution.</p>
          <div aria-label="Ontology version and source status" className="flex flex-wrap items-center gap-3 rounded-xl border p-3 text-xs"><label>Ontology version <select aria-label="Selected ontology version" value={loaded.snapshot.version_id} onChange={e=>{setVersion(e.target.value);setSelected(null);setExpanded([]);setQuery('');}} className="rounded border bg-background p-1">{loaded.ontology.versions.map(v=><option key={v.version_id} value={v.version_id}>Revision {v.revision} · {v.kind}</option>)}</select></label><span>Saved: {(loaded.snapshot.created_at??savedVersion?.created_at)?<DisplayTime value={(loaded.snapshot.created_at??savedVersion?.created_at)!}/>: 'Saved date unavailable'}</span><span>{loaded.snapshot.version_id===loaded.ontology.current_version_id?'Current saved definitions':'Historical definitions; not live source records'}</span>{loaded.ontology.source_bindings.map(source=><span key={source.role}>{source.name??label(source.role)}: {label(source.status)} (current connection)</span>)}{!loaded.ontology.source_bindings.length&&<span>No saved source connections</span>}{extension&&<span>Knowledge extension: {String(extension['package_id']??'version unavailable')} · revision {String(extension['package_revision']??'unavailable')}</span>}</div>
          <div className="flex flex-wrap items-center gap-2 rounded-xl border p-3">
            <label className="relative min-w-0 flex-1">
              <Search className="absolute left-3 top-3 h-4 w-4 text-muted-foreground" />
              <input
                aria-label="Search complete ontology"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder="Search concepts and definitions"
                className="w-full min-w-48 rounded-lg border bg-background py-2 pl-9 pr-3 text-sm"
              />
            </label>
            <button
              className="rounded-lg border px-3 py-2 text-sm"
              onClick={() => setExpanded(areas)}
            >
              Expand all
            </button>
            <button
              className="rounded-lg border px-3 py-2 text-sm"
              onClick={() => {
                setExpanded([]);
                setSelected(null);
              }}
            >
              Group overview
            </button>
          </div>
          <div className="flex flex-wrap gap-2" aria-label="Ontology business areas">
            <button type="button" onClick={()=>{setExpanded([]);setSelected(null);setQuery('');}} className="rounded-xl border px-4 py-3 text-xs" aria-pressed={!expanded.length&&!query}>Complete ontology</button>
            {areas.map((area) => (
              <button
                key={area}
                aria-pressed={expanded.includes(area)}
                onClick={() =>
                  setExpanded((old) =>
                    old.length===1&&old[0]===area ? [] : [area],
                  )
                }
                className={`inline-flex items-center gap-2 rounded-xl border px-4 py-3 text-sm ${expanded.includes(area) ? "border-primary bg-primary/5 text-primary" : ""}`}
              >
                <Layers3 size={13} />
                {areaLabel(area)}
              </button>
            ))}
          </div>
          <p className="text-xs text-muted-foreground">
            Cards show concepts or expandable business areas. Lines show saved concept
            relationships. Source mappings and rule definitions are available in the details.
          </p>
          <div className="grid min-w-0 overflow-hidden rounded-2xl border lg:grid-cols-[1fr_340px]">
            <div
              ref={canvasRef}
              className="h-[580px] min-w-0 bg-background"
              aria-label="Complete ontology graph"
            >
              <ReactFlowProvider>
                <ReactFlow
                  key={JSON.stringify([loaded.snapshot.version_id, query, expanded, columns])}
                  nodes={graph.nodes.map((n) => ({ ...n, selected: n.id === selected }))}
                  edges={graph.edges}
                  nodeTypes={nodeTypes}
                  fitView
                  fitViewOptions={{
                    padding: 0.12,
                    minZoom: 0.55,
                    maxZoom: 1,
                    nodes: graph.nodes
                      .slice(0, columns === 1 ? 3 : 9)
                      .map((node) => ({ id: node.id })),
                  }}
                  minZoom={0.08}
                  nodesDraggable={false}
                  nodesConnectable={false}
                  onNodeClick={(_, node) => {
                    if (node.id.startsWith("area:"))
                      setExpanded((old) => [...old, node.id.slice(5)]);
                    else setSelected(node.id);
                  }}
                  proOptions={{ hideAttribution: true }}
                >
                  <Background gap={24} />
                  <Controls showInteractive={false} />
                </ReactFlow>
              </ReactFlowProvider>
              {graph.nodes.length === 0 && <p className="p-4 text-sm">No matching concepts.</p>}
            </div>
            <aside
              aria-label="Client ontology concept details"
              className="max-h-[580px] space-y-5 overflow-y-auto border-t bg-background p-5 lg:border-l lg:border-t-0"
            >
              {!concept ? (
                <>
                  <Layers3 className="h-8 w-8 text-primary" />
                  <h3 className="font-semibold">Explore a business area</h3>
                  <p className="text-sm text-muted-foreground">
                    Expand an area, then select a concept to inspect its saved meaning and
                    connections.
                  </p>
                </>
              ) : (
                <>
                  <p className="text-xs uppercase text-muted-foreground">
                    {areaLabel(concept.module_id)}
                  </p>
                  <h3 className="text-xl font-semibold">{concept.label}</h3>
                  <p className="text-sm leading-relaxed">{concept.definition}</p>
                  <p className="text-xs text-muted-foreground">
                    Saved definition: {concept.status}
                  </p>
                  <section>
                    <h4 className="text-sm font-semibold">Connected concepts</h4>
                    {connections.map((r) => {
                      const other = loaded.snapshot.concepts.find(
                        (c) => c.id === (r.source === concept.id ? r.target : r.source),
                      );
                      return other ? (
                        <button
                          key={r.id}
                          className="mt-2 flex w-full items-center justify-between rounded-lg border p-3 text-left text-xs"
                          onClick={() => {
                            setExpanded((old) => [...new Set([...old, other.module_id])]);
                            setSelected(other.id);
                          }}
                        >
                          <span>
                            {r.label || label(r.predicate)}
                            <strong className="mt-1 block">{other.label}</strong>
                          </span>
                          <ChevronRight size={14} />
                        </button>
                      ) : null;
                    })}
                    {!connections.length && (
                      <p className="mt-2 text-xs text-muted-foreground">No saved relationships.</p>
                    )}
                  </section>
                  <section aria-label="Concept source fields">
                    <h4 className="text-sm font-semibold">Source fields</h4>
                    {mappings
                      .filter((m) => m.concept_id === concept.id)
                      .map((m) => (
                        <div key={m.id} className="mt-2 rounded-lg border p-3 text-xs">
                          <p>
                            {m.collection} · {m.field_path}
                          </p>
                          <p className="mt-1 text-muted-foreground">
                            {loaded.ontology.source_bindings.find((s) => s.role === m.source_role)
                              ?.name ?? label(m.source_role)}
                          </p>
                        </div>
                      ))}
                    {!mappings.some((m) => m.concept_id === concept.id) && (
                      <p className="mt-2 text-xs text-muted-foreground">
                        No saved source-field mapping.
                      </p>
                    )}
                  </section>
                  <section>
                    <h4 className="text-sm font-semibold">Referenced business rules</h4>
                    {rules.map((r) => (
                      <details key={r.id} className="mt-2 rounded-lg border p-3 text-xs">
                        <summary>{r.label}</summary>
                        <p className="mt-2">{r.definition}</p>
                        <Saved value={r} />
                      </details>
                    ))}
                    {!rules.length && (
                      <p className="mt-2 text-xs text-muted-foreground">
                        No explicit rule reference found. Browse all rules below.
                      </p>
                    )}
                  </section>
                  <DefinitionDetails title="Knowledge-extension rule references" entries={extensionRules.filter(r=>dependencies.some(d=>Array.isArray(d['rules'])&&d['rules'].includes(r['id'])))}/>
                  <DefinitionDetails title="Identity definitions" entries={identities}/>
                  <DefinitionDetails title="State and status definitions" entries={states}/>
                  <DefinitionDetails title="Temporal definitions" entries={dates}/>
                  <DefinitionDetails title="Required evidence and rule dependencies" entries={dependencies}/>
                  <section><h4 className="text-sm font-semibold">Definition provenance</h4>{concept.evidence.length?concept.evidence.map((e,i)=><blockquote key={i} className="mt-2 border-l pl-3 text-xs">{e.quote}<p className="text-muted-foreground">Saved source: {e.source_id}</p></blockquote>):<p className="mt-2 text-xs text-muted-foreground">No source evidence reference is saved for this definition.</p>}<p className="mt-2 text-xs text-muted-foreground">These are saved definitions and source references, not evidence that this concept was used in a run.</p></section>
                  <details className="text-xs">
                    <summary>Technical details and raw provenance</summary>
                    <Saved
                      value={{
                        concept_id: concept.id,
                        mappings:selectedMappings,
                        relationships:connections,
                        properties: concept.properties,
                        evidence: concept.evidence,
                        unknowns: concept.unknowns,
                        version: loaded.snapshot.version_id,
                      }}
                    />
                  </details>
                </>
              )}
            </aside>
          </div>
          <details className="rounded-xl border p-4 text-sm">
            <summary className="cursor-pointer font-medium">
              All business rules ({loaded.snapshot.rules.length})
            </summary>
            {loaded.snapshot.rules.map((r) => (
              <details key={r.id} className="mt-3 rounded-lg border p-3">
                <summary>{r.label}</summary>
                <p className="mt-2 text-sm">{r.definition}</p>
                <Saved value={r} />
              </details>
            ))}
            {!loaded.snapshot.rules.length && (
              <p className="mt-3 text-muted-foreground">No business rules saved in this version.</p>
            )}
          </details>
          <details className="rounded-xl border p-4 text-sm">
            <summary className="cursor-pointer font-medium">
              Source connections and saved definitions
            </summary>
            <Saved
              value={{
                connections: loaded.ontology.source_bindings,
                source_mappings: mappings,
                knowledge: loaded.snapshot.knowledge,
                version: loaded.snapshot.version_id,
              }}
            />
          </details>
        </>
      )}
    </section>
  );
}

function DefinitionDetails({title,entries}:{title:string;entries:Record<string,unknown>[]}) {
 return <section><h4 className="text-sm font-semibold">{title}</h4>{entries.length?entries.map((entry,i)=><div key={i} className="mt-2 rounded-lg border p-3 text-xs">{['label','meaning','kind','semantic_kind','attribute','comparison','precision','unknown_behavior'].map(key=>typeof entry[key]==='string'?<p key={key}>{key.replaceAll('_',' ')}: {String(entry[key]).replaceAll('_',' ')}</p>:null)}{Array.isArray(entry['values'])&&<ul>{(entry['values'] as {raw:string;meaning:string}[]).map((v,j)=><li key={j}>{v.raw}: {v.meaning}</li>)}</ul>}<details className="mt-2"><summary>Technical definition</summary><Saved value={entry}/></details></div>):<p className="mt-2 text-xs text-muted-foreground">No explicit saved definition is linked to this concept.</p>}</section>;
}
