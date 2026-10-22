import type { SemanticEdge, SemanticView } from "@/api/semantic-kg";

type Entity = SemanticView["entities"][number];
type Source = Entity["sources"][number];
export type SemanticCanvasNode = Entity & { kind: "entity" | "connection" | "workspace" };
export type SemanticCanvasEdge = {
  relationship_id: string;
  source_entity_id: string;
  target_entity_id: string;
  predicate: string;
  status: string;
  kind: "business" | "ownership" | "provenance";
  evidence: string[];
  original?: SemanticEdge;
};
export type SemanticCanvas = { entities: SemanticCanvasNode[]; relationships: SemanticCanvasEdge[]; resolvedIdentifiers: number };
const strings = (v: unknown): string[] => Array.isArray(v) ? v.filter((s): s is string => typeof s === "string") : [];
const record = (v: unknown): Record<string, unknown> => v && typeof v === "object" ? v as Record<string, unknown> : {};

/** Prepare the existing canvas only. Never edit the API evidence or saved mappings. */
export function semanticCanvas(view: SemanticView, options: { connection?: string; search?: string; status?: string } = {}): SemanticCanvas {
  const scoped = view.entities.map(e => ({ ...e, sources: e.sources.filter(s => !options.connection || s.connection_id === options.connection) })).filter(e => e.sources.length);
  const datasets = view.datasets.filter(d => !options.connection || d.connection_id === options.connection);
  const byDataset = new Map<string, Entity>();
  const datasetSource = new Map<string, Source>();
  const byField = new Map<string, typeof datasets[number]>();
  const physical = new Map<string, string>();
  for (const e of scoped) for (const s of e.sources) if (s.kind === "dataset") {
    byDataset.set(s.node_id, e); datasetSource.set(s.node_id, s);
    physical.set(JSON.stringify([s.connection_id, s.metadata["schema"] ?? null, s.metadata["name"]]), s.node_id);
  }
  for (const d of datasets) for (const f of d.fields) byField.set(f.field_id, d);
  const aliases = new Map<string, string>();
  // A foreign key's target, not a similar-looking field name, supplies identity.
  for (const e of scoped) {
    if (e.sources.some(s => s.kind === "dataset")) continue;
    const targets = new Set<string>(); let complete = true;
    for (const s of e.sources) {
      const d = byField.get(s.node_id); const owner = d && byDataset.get(d.dataset_id);
      if (!d || !owner) { complete = false; break; }
      const f = d.fields.find(f => f.field_id === s.node_id);
      const metadata = datasetSource.get(d.dataset_id)?.metadata;
      const constraints = metadata?.["constraints"];
      const resolved = new Set<string>();
      if (Array.isArray(constraints)) for (const raw of constraints) {
        const c = record(raw); const columns = strings(c["columns"]);
        if (!f || columns.length !== 1 || !columns.includes(f.name)) continue;
        if (c["kind"] === "primary_key") resolved.add(owner.entity_id);
        if (c["kind"] === "foreign_key") {
          const targetId = physical.get(JSON.stringify([s.connection_id, c["referenced_schema"] ?? null, c["referenced_table"]]));
          const target = targetId && byDataset.get(targetId);
          if (target) resolved.add(target.entity_id);
        }
      }
      if (f?.name === "_id" && metadata?.["schema"] == null) resolved.add(owner.entity_id);
      if (resolved.size !== 1) { complete = false; break; }
      targets.add([...resolved][0]!);
    }
    if (complete && targets.size === 1) aliases.set(e.entity_id, [...targets][0]!);
  }
  const entities = new Map<string, SemanticCanvasNode>();
  for (const e of scoped) if (!aliases.has(e.entity_id)) entities.set(e.entity_id, { ...e, sources: [...e.sources], kind: "entity" });
  for (const e of scoped) {
    const id = aliases.get(e.entity_id); const target = id && entities.get(id);
    if (target) target.sources.push(...e.sources.filter(s => !target.sources.some(t => t.node_id === s.node_id)));
  }
  const links: SemanticCanvasEdge[] = [];
  const datasetIds = new Set(datasets.map(d => d.dataset_id));
  for (const original of view.relationships) {
    if (!datasetIds.has(original.source_dataset_id) || !datasetIds.has(original.target_dataset_id)) continue;
    if (options.status && options.status !== "all" && original.status !== options.status) continue;
    let source = aliases.get(original.source_entity_id) ?? original.source_entity_id;
    let target = aliases.get(original.target_entity_id) ?? original.target_entity_id;
    if (!entities.has(source) || !entities.has(target)) continue;
    const established = original.status === "confirmed" || original.status === "inferred";
    let predicate = established ? original.predicate : null;
    // Exact inverse of an existing semantic statement; no new supply claim is inferred.
    if (established && predicate?.toLowerCase() === "is supplied by") {
      [source, target] = [target, source]; predicate = "supplies";
    }
    links.push({ relationship_id: original.relationship_id, source_entity_id: source, target_entity_id: target,
      predicate: predicate ?? (original.technical_status === "declared" ? "references" : "has a possible link to"),
      status: original.status, kind: "business", evidence: [...original.evidence], original });
  }
  // Keep unresolved field concepts visible and connect them by actual field ownership.
  for (const e of scoped) if (!aliases.has(e.entity_id) && !e.sources.some(s => s.kind === "dataset")) {
    for (const source of e.sources) {
      const d = byField.get(source.node_id); const owner = d && byDataset.get(d.dataset_id);
      if (!owner || owner.entity_id === e.entity_id) continue;
      const id = `ownership:${owner.entity_id}:${e.entity_id}`;
      if (!links.some(l => l.relationship_id === id)) links.push({ relationship_id: id, source_entity_id: owner.entity_id,
        target_entity_id: e.entity_id, predicate: "has field concept", status: "metadata", kind: "ownership",
        evidence: [`Field ${source.label} belongs to dataset ${datasetSource.get(d!.dataset_id)?.label ?? d!.label}.`, "Field ownership does not establish a business relationship or executable join."] });
    }
  }
  const query = options.search?.trim().toLowerCase();
  if (query) {
    const matched = new Set([...entities.values()].filter(e => `${e.label} ${e.sources.map(s => s.label).join(" ")}`.toLowerCase().includes(query)).map(e => e.entity_id));
    for (const l of links) if (l.predicate.toLowerCase().includes(query)) { matched.add(l.source_entity_id); matched.add(l.target_entity_id); }
    for (const id of entities.keys()) if (!matched.has(id)) entities.delete(id);
  }
  const visible = links.filter(l => entities.has(l.source_entity_id) && entities.has(l.target_entity_id));
  if (!entities.size) return { entities: [], relationships: [], resolvedIdentifiers: aliases.size };
  const addMembership = (id: string, from: string, to: string, predicate: string, evidence: string[]) => {
    visible.push({ relationship_id: id, source_entity_id: from, target_entity_id: to, predicate, status: "source membership", kind: "provenance", evidence });
  };
  const workspaceId = "membership:workspace";
  const sourceIds = new Map<string, string>();
  for (const e of entities.values()) for (const s of e.sources) if (!sourceIds.has(s.connection_id)) sourceIds.set(s.connection_id, `membership:connection:${s.connection_id}`);
  // Find actual components before adding membership; attach just one evidenced anchor per component.
  const adjacency = new Map([...entities.keys()].map(id => [id, new Set<string>()]));
  for (const l of visible) if (l.status !== "rejected") { adjacency.get(l.source_entity_id)!.add(l.target_entity_id); adjacency.get(l.target_entity_id)!.add(l.source_entity_id); }
  const seen = new Set<string>(); const anchors: SemanticCanvasNode[] = [];
  for (const first of entities.keys()) {
    if (seen.has(first)) continue;
    const stack = [first], component: SemanticCanvasNode[] = [];
    while (stack.length) { const id = stack.pop()!; if (seen.has(id)) continue; seen.add(id); component.push(entities.get(id)!); for (const next of adjacency.get(id)!) if (!seen.has(next)) stack.push(next); }
    component.sort((a,b) => Number(b.sources.some(s => s.kind === "dataset")) - Number(a.sources.some(s => s.kind === "dataset")) || a.label.localeCompare(b.label));
    anchors.push(component[0]!);
  }
  const scopedSources = [...entities.values()].flatMap(e => e.sources);
  entities.set(workspaceId, { entity_id: workspaceId, label: "Connected workspace", sources: [], kind: "workspace" });
  for (const [cid, id] of sourceIds) {
    const sources = scopedSources.filter(s => s.connection_id === cid);
    entities.set(id, { entity_id: id, label: sources[0]!.label.split(" / ")[0]!, sources: [...new Map(sources.map(s => [s.node_id,s])).values()], kind: "connection" });
    addMembership(`membership:workspace:${cid}`, workspaceId, id, "includes source", [`These mappings share the current workspace and connection ID ${cid}.`, "Source membership is not a business relationship or join permission."]);
  }
  for (const anchor of anchors) {
    const source = anchor.sources.find(s => s.kind === "dataset") ?? anchor.sources[0]!;
    addMembership(`membership:component:${anchor.entity_id}`, sourceIds.get(source.connection_id)!, anchor.entity_id, "provides data for", [`Source mapping: ${source.label}`, `Connection: ${source.connection_id}; node: ${source.node_id}.`, "This links source provenance only; it does not assert a business relationship between disconnected datasets."]);
  }
  return { entities: [...entities.values()], relationships: visible, resolvedIdentifiers: aliases.size };
}
