"use client";
import { displayText } from "@/lib/display-text";

import { useId, useState } from "react";
import type { SelectionPreview } from "@/api/data-queries";

export default function SelectedSources({ preview }: { preview: SelectionPreview }) {
  const [selected, setSelected] = useState(preview.sources[0]?.dataset_id ?? "");
  const id = useId();
  const source = preview.sources.find((item) => item.dataset_id === selected) ?? preview.sources[0];
  if (!source) return null;
  const fieldLabels = new Map(
    preview.sources.flatMap((item) =>
      item.fields.map((field) => [field.field_id, field.label] as const),
    ),
  );
  const labels = new Map(preview.sources.map((item) => [item.dataset_id, item.label]));
  const indexes = new Map(preview.sources.map((item, index) => [item.dataset_id, index]));
  const sourceIds = new Set([source.dataset_id, ...source.fields.map((field) => field.field_id)]);
  const outside = Math.max(0, preview.catalog_dataset_count - preview.sources.length);
  return (
    <section aria-label="Selected sources" className="min-w-0 space-y-4 rounded-xl border p-3">
      <h4 className="font-semibold">Selected sources ({preview.sources.length})</h4>
      <p className="text-xs text-muted-foreground">
        Plan usage below is derived from validated fields and joins. {outside} catalog datasets are
        outside this plan; no business-data read is planned for them.
      </p>
      <svg
        role="img"
        aria-label="Selected graph subset"
        viewBox={`0 0 640 ${preview.sources.length * 100 + 20}`}
        className="w-full"
        style={{ maxHeight: 420 }}
      >
        <title>Highlighted datasets and equality joins in this read plan</title>
        {preview.relationships.map((edge, index) => {
          const start = indexes.get(edge.source_dataset_id);
          const end = indexes.get(edge.target_dataset_id);
          if (start === undefined || end === undefined) return null;
          const x = 500 + index * 40;
          return (
            <path
              key={edge.relationship_id}
              d={`M 440 ${start * 100 + 55} H ${x} V ${end * 100 + 55} H 440`}
              fill="none"
              className="stroke-primary"
              strokeWidth="3"
            >
              <title>{displayText(`${labels.get(edge.source_dataset_id)} equals ${labels.get(edge.target_dataset_id)}; ${edge.status}`)}</title>
            </path>
          );
        })}
        {preview.sources.map((item, index) => (
          <g
            key={item.dataset_id}
            role="button"
            tabIndex={0}
            aria-label={displayText(`Inspect selected source: ${item.label}`)}
            aria-pressed={item.dataset_id === source.dataset_id}
            onClick={() => setSelected(item.dataset_id)}
            onKeyDown={(event) => {
              if (event.key === "Enter" || event.key === " ") {
                event.preventDefault();
                setSelected(item.dataset_id);
              }
            }}
            className="cursor-pointer"
          >
            <title>{displayText(item.label)}</title>
            <rect
              x="10"
              y={index * 100 + 20}
              width="430"
              height="70"
              rx="10"
              className={
                item.dataset_id === source.dataset_id
                  ? "fill-primary/20 stroke-primary"
                  : "fill-muted stroke-primary"
              }
              strokeWidth={item.dataset_id === source.dataset_id ? 3 : 1}
            />
            <text x="24" y={index * 100 + 48} className="fill-foreground" fontSize="16">
              {displayText(item.label.length > 46 ? item.label.slice(0, 43) + "…" : item.label)}
            </text>
            <text x="24" y={index * 100 + 72} className="fill-foreground" fontSize="14">
              {item.engine} · {item.fields.length} required fields · selected
            </text>
          </g>
        ))}
      </svg>
      <label className="block text-sm" htmlFor={id}>
        Inspect selected dataset
      </label>
      <select
        id={id}
        className="w-full min-w-0 rounded border bg-background p-2 text-sm"
        value={source.dataset_id}
        onChange={(event) => setSelected(event.target.value)}
      >
        {preview.sources.map((item) => (
          <option key={item.dataset_id} value={item.dataset_id}>
            {displayText(item.label)}
          </option>
        ))}
      </select>
      <section
        aria-label="Selected source details"
        className="min-w-0 space-y-2 break-words text-sm"
      >
        <p className="font-medium">{displayText(source.label)}</p>
        <ul className="list-disc space-y-1 pl-5 text-xs">
          {source.reasons.map((reason) => (
            <li key={reason}>{displayText(reason)}</li>
          ))}
        </ul>
        <details open>
          <summary className="cursor-pointer text-xs font-medium">
            Required fields ({source.fields.length})
          </summary>
          <ul className="mt-2 max-h-64 space-y-2 overflow-auto text-xs">
            {source.fields.map((field) => (
              <li key={field.field_id}>
                <span className="break-all">{displayText(field.label)}</span> · {field.types.join(", ")} ·{" "}
                {field.purposes.join(", ")}
              </li>
            ))}
          </ul>
        </details>
        {preview.business_mappings
          .filter((mapping) => sourceIds.has(mapping.node_id))
          .map((mapping) => (
            <p key={mapping.node_id} className="text-xs">
              Confirmed concept: {displayText(mapping.entity_name)} · {mapping.role} ·{" "}
              {displayText(fieldLabels.get(mapping.node_id) ?? source.label)}
            </p>
          ))}
      </section>
      <section aria-label="Selected linking fields" className="space-y-2 break-words text-xs">
        <p className="font-medium">Linking relationships ({preview.relationships.length})</p>
        {preview.relationships.length === 0 && (
          <p>Single dataset; no relationship join is planned.</p>
        )}
        {preview.relationships.map((edge) => (
          <div key={edge.relationship_id} className="rounded border p-2">
            <p>
              {displayText(labels.get(edge.source_dataset_id))} → {displayText(labels.get(edge.target_dataset_id))} ·{" "}
              {edge.status}
            </p>
            {edge.field_pairs.map((pair, index) => (
              <p key={index} className="mt-1 break-all">
                {displayText(fieldLabels.get(pair.source_field_id))} = {displayText(fieldLabels.get(pair.target_field_id))}
              </p>
            ))}
          </div>
        ))}
        <p>
          Links show execution order. Acceptance and business mappings do not prove matching values
          or grant permissions; runtime key checks still apply.
        </p>
      </section>
      {!!preview.warnings.length && (
        <details className="text-xs">
          <summary className="cursor-pointer">Metadata coverage warnings</summary>
          <ul className="mt-2 space-y-1">
            {preview.warnings.map((warning, index) => (
              <li key={index}>{displayText(warning)}</li>
            ))}
          </ul>
        </details>
      )}
    </section>
  );
}
