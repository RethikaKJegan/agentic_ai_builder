import { displayText } from "@/lib/display-text";
import { friendlyLabel } from "@/domain/communication-diagram";

/** Render recorded values as readable fields without interpreting business meaning. */
export function ReadableEvidence({ value, depth = 0 }: { value: unknown; depth?: number }) {
  if (value === undefined) return <p className="text-xs text-muted-foreground">Not recorded.</p>;
  if (value === null) return <span className="text-muted-foreground">Not supplied</span>;
  if (typeof value !== "object")
    return (
      <p className="whitespace-pre-wrap break-words text-sm">
        {typeof value === "boolean" ? (value ? "Yes" : "No") : String(value)}
      </p>
    );
  if (depth >= 4)
    return (
      <details>
        <summary className="cursor-pointer text-xs">View nested information</summary>
        <pre className="overflow-auto whitespace-pre-wrap break-words text-xs">
          {displayText(JSON.stringify(value, null, 2))}
        </pre>
      </details>
    );
  if (Array.isArray(value))
    return value.length ? (
      <ol className="space-y-2">
        {value.slice(0, 30).map((item, i) => (
          <li key={i} className="rounded-md border border-border p-2">
            <ReadableEvidence value={item} depth={depth + 1} />
          </li>
        ))}
        {value.length > 30 && (
          <li className="text-xs text-muted-foreground">
            Showing 30 of {value.length} entries. All recorded entries are available in Technical
            details.
          </li>
        )}
      </ol>
    ) : (
      <p className="text-sm text-muted-foreground">No entries.</p>
    );
  return (
    <dl className="space-y-2">
      {Object.entries(value).map(([key, item]) => (
        <div key={key}>
          <dt className="text-xs font-medium capitalize text-muted-foreground">
            {displayText(friendlyLabel(key))}
          </dt>
          <dd className="mt-1 border-l-2 border-border pl-3">
            <ReadableEvidence value={item} depth={depth + 1} />
          </dd>
        </div>
      ))}
    </dl>
  );
}
