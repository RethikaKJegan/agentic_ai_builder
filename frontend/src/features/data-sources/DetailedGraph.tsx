"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { api } from "@/api/client";
import type { DetailedView, DetailedNode, EntityMapping } from "@/api/data-relationships";
import { ApiFeedback } from "@/features/workflows/ApiFeedback";

const control = "rounded-lg border bg-background px-3 py-2 text-sm disabled:opacity-40";

function EntitySources({
  mappings,
  sourceLabel,
  select,
}: {
  mappings: EntityMapping[];
  sourceLabel: (id: string) => string;
  select: (id: string) => void;
}) {
  const [limit, setLimit] = useState(100);
  return (
    <section aria-label="Entity source mappings" className="mt-3 space-y-2">
      <p className="text-xs text-muted-foreground">
        Showing {Math.min(limit, mappings.length)} of {mappings.length} source mappings
      </p>
      {mappings.slice(0, limit).map((mapping) => (
        <button
          key={mapping.node_id}
          className="block break-all text-left text-sm text-primary underline"
          onClick={() => select(mapping.node_id)}
        >
          {sourceLabel(mapping.node_id)} · {mapping.role} · {mapping.status}
        </button>
      ))}
      {mappings.length > limit && (
        <button className={control} onClick={() => setLimit((value) => value + 100)}>
          Show more entity sources
        </button>
      )}
    </section>
  );
}

function MappingEditor({
  node,
  mapping,
  disabled,
  save,
}: {
  node: DetailedNode;
  mapping: EntityMapping | undefined;
  disabled: boolean;
  save: (
    name: string,
    role: EntityMapping["role"],
    status: "suggested" | "confirmed" | "rejected",
  ) => void;
}) {
  const [name, setName] = useState(mapping?.entity_name ?? "");
  const [role, setRole] = useState<EntityMapping["role"]>(
    mapping?.role ?? (node.kind === "dataset" ? "represents" : "attribute"),
  );
  return (
    <form
      className="space-y-3 rounded-xl border p-4"
      onSubmit={(e) => {
        e.preventDefault();
        save(name, role, "confirmed");
      }}
    >
      <h4 className="font-medium">Business mapping</h4>
      <p className="text-sm">
        Review status: <strong>{mapping?.status ?? "not mapped"}</strong>
      </p>
      {mapping?.reviewed_at && (
        <p className="text-xs">Last review {new Date(mapping.reviewed_at).toLocaleString()}</p>
      )}
      <label className="block text-sm">
        Entity name
        <input
          required
          maxLength={80}
          disabled={disabled}
          className={`${control} mt-1 w-full`}
          value={name}
          onChange={(e) => setName(e.target.value)}
        />
      </label>
      <label className="block text-sm">
        Mapping role
        <select
          className={`${control} mt-1 w-full`}
          disabled={disabled || node.kind === "dataset"}
          value={role}
          onChange={(e) => setRole(e.target.value as EntityMapping["role"])}
        >
          {(node.kind === "dataset"
            ? ["represents"]
            : ["identifier", "reference", "attribute"]
          ).map((r) => (
            <option key={r}>{r}</option>
          ))}
        </select>
      </label>
      <p className="text-xs text-muted-foreground">
        A dataset represents an entity. A field identifies, references or describes it. Confirmation
        never grants a database join or tool permission.
      </p>
      {mapping?.evidence.map((s) => (
        <p key={s} className="text-xs text-muted-foreground">
          {s}
        </p>
      ))}
      <div className="flex flex-wrap gap-2">
        <button className={control} disabled={disabled || !name.trim()}>
          Confirm mapping
        </button>
        <button
          type="button"
          className={control}
          disabled={disabled || !name.trim()}
          onClick={() => save(name, role, "rejected")}
        >
          Reject mapping
        </button>
        <button
          type="button"
          className={control}
          disabled={disabled || !mapping}
          onClick={() => save(name || mapping?.entity_name || "", role, "suggested")}
        >
          Reset mapping review
        </button>
      </div>
    </form>
  );
}

export default function DetailedGraph({
  canManage,
  onChanged,
  onStatus,
  refreshToken = 0,
}: {
  canManage: boolean;
  onChanged: () => void;
  onStatus?: (status: Pick<DetailedView, "build_status" | "last_error" | "stale">) => void;
  refreshToken?: number;
}) {
  const [view, setView] = useState<DetailedView>();
  const [error, setError] = useState<Error>();
  const [selected, setSelected] = useState("");
  const [business, setBusiness] = useState(false);
  const [search, setSearch] = useState("");
  const [connection, setConnection] = useState("");
  const [status, setStatus] = useState("all");
  const [edgeFilter, setEdgeFilter] = useState("all");
  const [expanded, setExpanded] = useState<Set<string>>(new Set());
  const [limit, setLimit] = useState(100);
  const [busy, setBusy] = useState(false);
  const [notice, setNotice] = useState("");
  const lock = useRef(false);
  const epoch = useRef(0);
  const reload = useRef<() => void>(() => {});
  useEffect(() => {
    let disposed = false;
    let timer: ReturnType<typeof setTimeout>;
    const load = async () => {
      if (lock.current) {
        timer = setTimeout(() => void load(), 1000);
        return;
      }
      const sequence = ++epoch.current;
      let delay = 6000;
      try {
        const value = await api.detailedGraph();
        if (!disposed && sequence === epoch.current) {
          setView(value);
          setError(undefined);
          onStatus?.(value);
          if (value.build_status === "queued" || value.build_status === "running") delay = 1000;
        }
      } catch (e) {
        if (!disposed && sequence === epoch.current)
          setError(e instanceof Error ? e : new Error("Detailed graph could not be loaded."));
      } finally {
        if (!disposed)
          timer = setTimeout(() => {
            if (!lock.current) void load();
            else timer = setTimeout(() => void load(), 1000);
          }, delay);
      }
    };
    reload.current = () => {
      clearTimeout(timer);
      void load();
    };
    void load();
    return () => {
      disposed = true;
      clearTimeout(timer);
    };
  }, [onStatus, refreshToken]);
  const graph = view?.graph;
  const { nodes, children } = useMemo(() => {
    const nodes = new Map(graph?.nodes.map((n) => [n.node_id, n]));
    const children = new Map<string, DetailedNode[]>();
    for (const node of graph?.nodes ?? []) {
      const parent = node.parent_id ?? "";
      const siblings = children.get(parent) ?? [];
      siblings.push(node);
      children.set(parent, siblings);
    }
    return { nodes, children };
  }, [graph]);
  const mappings = useMemo(() => new Map(graph?.mappings.map((m) => [m.node_id, m])), [graph]);
  const node = nodes.get(selected);
  const mapping = mappings.get(selected);
  const sourceLabel = (id: string) => {
    const path: string[] = [];
    const visited = new Set<string>();
    let item = nodes.get(id);
    while (item && !visited.has(item.node_id)) {
      visited.add(item.node_id);
      path.unshift(
        item.kind === "dataset" && typeof item.metadata["name"] === "string"
          ? item.metadata["name"]
          : item.label,
      );
      item = item.parent_id ? nodes.get(item.parent_id) : undefined;
    }
    return path.length ? path.join(" / ") : id;
  };
  const disabled = !canManage || busy || !view || view.stale;
  const matches = (n: DetailedNode) =>
    (!connection || n.connection_id === connection) &&
    (n.label + " " + n.kind + " " + (mappings.get(n.node_id)?.entity_name ?? ""))
      .toLowerCase()
      .includes(search.toLowerCase());
  const visibleMappings = (graph?.mappings ?? []).filter(
    (m) =>
      (status === "all" || m.status === status) &&
      (!connection || nodes.get(m.node_id)?.connection_id === connection) &&
      `${m.entity_name} ${nodes.get(m.node_id)?.label ?? ""} ${m.role}`
        .toLowerCase()
        .includes(search.toLowerCase()),
  );
  const visibleNodes = (graph?.nodes ?? []).filter((n) => n.kind !== "entity" && matches(n));
  const scope = new Set<string>();
  const pending = selected ? [selected] : [];
  if (node?.kind === "entity")
    pending.push(
      ...(graph?.mappings.filter((m) => m.entity_id === selected).map((m) => m.node_id) ?? []),
    );
  while (pending.length) {
    const id = pending.pop()!;
    if (scope.has(id)) continue;
    scope.add(id);
    pending.push(...(children.get(id) ?? []).map((n) => n.node_id));
  }
  const related = (graph?.relationships ?? []).filter(
    (e) =>
      (edgeFilter === "all" ||
        (edgeFilter === "needs_review"
          ? e.review_stale
          : !e.review_stale && e.status === edgeFilter)) &&
      (!connection ||
        nodes.get(e.source_dataset_id)?.connection_id === connection ||
        nodes.get(e.target_dataset_id)?.connection_id === connection) &&
      (!selected ||
        scope.has(e.source_dataset_id) ||
        scope.has(e.target_dataset_id) ||
        e.field_pairs.some((p) => scope.has(p.source_field_id) || scope.has(p.target_field_id))) &&
      `${nodes.get(e.source_dataset_id)?.label} ${nodes.get(e.target_dataset_id)?.label} ${e.field_pairs.map((p) => nodes.get(p.source_field_id)?.label + " " + nodes.get(p.target_field_id)?.label).join(" ")}`
        .toLowerCase()
        .includes(search.toLowerCase()),
  );
  async function save(
    name: string,
    role: EntityMapping["role"],
    status: "suggested" | "confirmed" | "rejected",
  ) {
    if (disabled || lock.current || !graph) return;
    lock.current = true;
    epoch.current++;
    setBusy(true);
    setError(undefined);
    try {
      setView(
        await api.detailedGraph(selected, {
          revision: graph.revision,
          entity_name: name,
          role,
          status,
        }),
      );
      setNotice("Business mapping review saved. Existing query plans require fresh review.");
      onChanged();
    } catch (e) {
      setError(
        e instanceof Error
          ? e
          : new Error("Mapping review could not be confirmed. Reload before retrying."),
      );
    } finally {
      lock.current = false;
      setBusy(false);
    }
  }
  async function reviewRelationship(id: string, status: "accepted" | "rejected" | "proposed") {
    if (disabled || lock.current || !graph) return;
    lock.current = true;
    epoch.current++;
    setBusy(true);
    setError(undefined);
    try {
      await api.relationships("review", id, { revision: graph.revision, status });
      setView(await api.detailedGraph());
      setNotice("Relationship review saved. Runtime key and permission checks still apply.");
      onChanged();
    } catch (error) {
      setError(
        error instanceof Error
          ? error
          : new Error("Reload the graph before repeating this review."),
      );
    } finally {
      lock.current = false;
      setBusy(false);
    }
  }
  function tree(n: DetailedNode, depth: number): React.ReactNode {
    const kids = children.get(n.node_id) ?? [];
    const open = expanded.has(n.node_id);
    return (
      <li key={n.node_id} className="min-w-0">
        <div className="flex items-start gap-1">
          {!!kids.length && (
            <button
              type="button"
              className="shrink-0 rounded border px-2 py-1 text-xs"
              aria-expanded={open}
              aria-label={`${open ? "Collapse" : "Expand"} ${n.label}`}
              onClick={() =>
                setExpanded((s) => {
                  const next = new Set(s);
                  if (next.has(n.node_id)) next.delete(n.node_id);
                  else next.add(n.node_id);
                  return next;
                })
              }
            >
              {open ? "−" : "+"}
            </button>
          )}
          <button
            type="button"
            aria-pressed={selected === n.node_id}
            className="min-w-0 break-all rounded px-2 py-1 text-left text-sm hover:bg-muted"
            onClick={() => setSelected(n.node_id)}
          >
            {n.label} <span className="text-xs text-muted-foreground">({n.kind})</span>
          </button>
        </div>
        {open && depth < 8 && (
          <ul className="ml-3 border-l pl-2">
            {kids.slice(0, limit).map((c) => tree(c, depth + 1))}
            {kids.length > limit && (
              <li>
                <button className={control} onClick={() => setLimit((l) => l + 100)}>
                  Show more children
                </button>
              </li>
            )}
          </ul>
        )}
      </li>
    );
  }
  return (
    <section aria-label="Detailed knowledge graph" className="min-w-0 space-y-4">
      <ApiFeedback error={error} onRetry={() => reload.current()} />
      {notice && (
        <p role="status" className="text-sm">
          {notice}
        </p>
      )}
      {!view && !error && <p role="status">Loading detailed graph…</p>}
      {view?.last_error && <p role="alert">{view.last_error}</p>}
      {view?.stale && (
        <p role="status" className="rounded border p-3">
          This detailed graph is historical. Rebuild relationships before reviewing mappings.
        </p>
      )}
      {view && !graph && <p>Build relationships from successful metadata snapshots first.</p>}
      {graph && (
        <>
          <p className="text-sm">
            Detailed graph v2 · revision {graph.revision} · {graph.nodes.length} nodes ·{" "}
            {graph.mappings.length} business mappings
          </p>
          <div className="flex flex-wrap gap-2" role="group" aria-label="Detailed graph view">
            <button className={control} aria-pressed={!business} onClick={() => setBusiness(false)}>
              Technical structure
            </button>
            <button className={control} aria-pressed={business} onClick={() => setBusiness(true)}>
              Business entities
            </button>
            <button
              className={control}
              onClick={() => {
                setSelected("");
                setSearch("");
                setConnection("");
                setStatus("all");
                setEdgeFilter("all");
                setExpanded(new Set());
                setLimit(100);
              }}
            >
              Reset explorer
            </button>
          </div>
          <div className="flex flex-wrap gap-3">
            <label className="min-w-0 flex-1 text-sm">
              Find graph items
              <input
                className={`${control} mt-1 w-full`}
                value={search}
                onChange={(e) => {
                  setSearch(e.target.value);
                  setLimit(100);
                }}
              />
            </label>
            <label className="min-w-0 text-sm">
              Graph connection
              <select
                className={`${control} mt-1 block max-w-full`}
                value={connection}
                onChange={(e) => setConnection(e.target.value)}
              >
                <option value="">All connections</option>
                {graph.nodes
                  .filter((n) => n.kind === "connection")
                  .map((n) => (
                    <option key={n.node_id} value={n.node_id}>
                      {n.label}
                    </option>
                  ))}
              </select>
            </label>
            {business && (
              <label className="text-sm">
                Mapping status
                <select
                  className={`${control} mt-1 block`}
                  value={status}
                  onChange={(e) => setStatus(e.target.value)}
                >
                  {["all", "suggested", "confirmed", "rejected", "needs_review"].map((s) => (
                    <option key={s}>{s}</option>
                  ))}
                </select>
              </label>
            )}
          </div>
          <div className="grid min-w-0 gap-4 lg:grid-cols-[minmax(240px,1fr)_minmax(0,2fr)]">
            <nav
              aria-label="Knowledge graph explorer"
              className="min-w-0 max-h-[600px] space-y-2 overflow-auto rounded-xl border p-3"
            >
              {business ? (
                <>
                  <p className="text-xs">
                    Naming suggestions require review. Select a mapping to inspect its source.
                  </p>
                  {visibleMappings.slice(0, limit).map((m) => (
                    <button
                      key={m.node_id}
                      data-testid={`mapping-${m.node_id}`}
                      className="block w-full break-words rounded border p-3 text-left text-sm"
                      onClick={() => setSelected(m.node_id)}
                    >
                      {m.entity_name} · {m.role}
                      <span className="block text-xs">
                        {sourceLabel(m.node_id)} · {m.status}
                      </span>
                    </button>
                  ))}
                  {!visibleMappings.length && <p>No business mappings match.</p>}
                  {visibleMappings.length > limit && (
                    <button className={control} onClick={() => setLimit((l) => l + 100)}>
                      Show more mappings
                    </button>
                  )}
                </>
              ) : search || connection ? (
                <>
                  <p className="text-xs">{visibleNodes.length} matching graph items</p>
                  {visibleNodes.slice(0, limit).map((n) => (
                    <button
                      key={n.node_id}
                      className="block break-all p-2 text-left text-sm"
                      onClick={() => setSelected(n.node_id)}
                    >
                      {n.label} ({n.kind})
                    </button>
                  ))}
                  {visibleNodes.length > limit && (
                    <button className={control} onClick={() => setLimit((l) => l + 100)}>
                      Show more items
                    </button>
                  )}
                </>
              ) : (
                <ul>
                  {(children.get("") ?? [])
                    .filter((n) => n.kind === "connection")
                    .map((n) => tree(n, 0))}
                </ul>
              )}
            </nav>
            <div className="min-w-0 space-y-4">
              {node ? (
                <>
                  <section className="rounded-xl border p-4">
                    <h3 className="break-all text-lg font-semibold">{node.label}</h3>
                    <p className="text-xs">
                      {node.kind} · {node.discovery_method}
                    </p>
                    <p className="mt-2 break-all text-xs">Stable ID: {node.node_id}</p>
                    {node.parent_id && (
                      <button
                        className="mt-2 text-sm text-primary underline"
                        onClick={() => setSelected(node.parent_id!)}
                      >
                        Parent: {nodes.get(node.parent_id)?.label}
                      </button>
                    )}
                    {node.description && <p className="mt-2 text-sm">{node.description}</p>}
                    <details className="mt-3">
                      <summary className="cursor-pointer text-sm">
                        Discovered metadata and constraints
                      </summary>
                      <pre className="mt-2 max-h-80 overflow-auto whitespace-pre-wrap break-all text-xs">
                        {JSON.stringify(node.metadata, null, 2)}
                      </pre>
                    </details>
                    {mapping && (
                      <button
                        className="mt-3 block text-sm text-primary underline"
                        onClick={() => setSelected(mapping.entity_id)}
                      >
                        Inspect entity: {mapping.entity_name}
                      </button>
                    )}
                    {node.kind === "entity" && (
                      <EntitySources
                        key={node.node_id}
                        mappings={graph.mappings.filter((m) => m.entity_id === node.node_id)}
                        sourceLabel={sourceLabel}
                        select={setSelected}
                      />
                    )}
                    {(node.kind === "dataset" || node.kind === "field") && (
                      <button
                        className="mt-3 text-sm text-primary underline"
                        onClick={() => {
                          setSelected("");
                          setSearch("");
                          setConnection(node.connection_id);
                        }}
                      >
                        Focus this connection
                      </button>
                    )}
                  </section>
                  {(node.kind === "dataset" || node.kind === "field") && (
                    <MappingEditor
                      key={`${node.node_id}:${mapping?.evidence_hash}:${mapping?.status}:${mapping?.entity_name}:${mapping?.role}`}
                      node={node}
                      mapping={mapping}
                      disabled={disabled}
                      save={(...args) => void save(...args)}
                    />
                  )}
                </>
              ) : (
                <p className="rounded-xl border p-4 text-sm">
                  Expand the technical hierarchy or select a business mapping. Suggestions never
                  prove business meaning, data overlap or execution permissions.
                </p>
              )}
              <section aria-label="Qualified relationships" className="space-y-3">
                <h3 className="font-medium">Relationship evidence ({related.length})</h3>
                <label className="block text-sm">
                  Evidence review status
                  <select
                    className={`${control} ml-2 max-w-full`}
                    value={edgeFilter}
                    onChange={(e) => setEdgeFilter(e.target.value)}
                  >
                    {["all", "declared", "proposed", "accepted", "rejected", "needs_review"].map(
                      (s) => (
                        <option key={s}>{s}</option>
                      ),
                    )}
                  </select>
                </label>
                {related.slice(0, 100).map((e) => (
                  <details key={e.relationship_id} className="rounded-xl border p-3">
                    <summary className="cursor-pointer break-words text-sm">
                      {nodes.get(e.source_dataset_id)?.label} {e.kind === "declared" ? "→" : "↔"}{" "}
                      {nodes.get(e.target_dataset_id)?.label} ·{" "}
                      {e.review_stale ? "needs review" : e.status}
                    </summary>
                    <p className="mt-2 text-xs">
                      Evidence strength: {e.qualification.confidence}. Direction:{" "}
                      {e.qualification.direction}. Value overlap: {e.qualification.value_overlap}.
                    </p>
                    <p className="mt-2 text-xs">{e.qualification.cardinality}</p>
                    <p className="mt-2 text-xs">{e.qualification.target_key_evidence}</p>
                    <p className="mt-2 text-xs">{e.qualification.review_basis}</p>
                    {e.field_pairs.map((p, i) => (
                      <p key={i} className="mt-2 break-all text-xs">
                        <button
                          className="text-left text-primary underline"
                          onClick={() => setSelected(p.source_field_id)}
                        >
                          {sourceLabel(p.source_field_id)}
                        </button>
                        {e.kind === "declared" ? " → " : " ↔ "}
                        <button
                          className="text-left text-primary underline"
                          onClick={() => setSelected(p.target_field_id)}
                        >
                          {sourceLabel(p.target_field_id)}
                        </button>
                      </p>
                    ))}
                    <ul className="mt-2 space-y-2">
                      {e.evidence.map((s, i) => (
                        <li key={i} className="break-all text-xs">
                          {s}
                        </li>
                      ))}
                    </ul>
                    {e.kind === "suggested" && (
                      <div className="mt-3 flex flex-wrap gap-2">
                        {(
                          [
                            ["accepted", "Accept relationship"],
                            ["rejected", "Reject relationship"],
                            ["proposed", "Reset relationship review"],
                          ] as const
                        ).map(([status, label]) => (
                          <button
                            key={status}
                            className={control}
                            disabled={disabled || (!e.review_stale && e.status === status)}
                            onClick={() => void reviewRelationship(e.relationship_id, status)}
                          >
                            {label}
                          </button>
                        ))}
                      </div>
                    )}
                  </details>
                ))}
                {related.length > 100 && (
                  <p className="text-xs">
                    Select a dataset or linking field to narrow the first 100 displayed
                    relationships.
                  </p>
                )}
              </section>
            </div>
          </div>
          <details className="rounded border p-3">
            <summary className="cursor-pointer text-sm">Coverage and interpretation limits</summary>
            {graph.warnings.map((s) => (
              <p key={s} className="mt-2 text-xs">
                {s}
              </p>
            ))}
            <p className="mt-2 text-xs">
              Metadata snapshots only. No new business-row scan or model call. Generic IDs,
              mixed/array types and unsupported key types do not establish reference suggestions.
            </p>
          </details>
        </>
      )}
    </section>
  );
}
