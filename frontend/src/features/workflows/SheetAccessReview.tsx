interface SheetTarget {
  spreadsheet_id: string;
  range: string;
  identity_column: string;
  writable_columns: string[];
  allow_create: boolean;
}

function isTarget(value: unknown): value is SheetTarget {
  if (!value || typeof value !== "object") return false;
  const item = value as Record<string, unknown>;
  return typeof item["spreadsheet_id"] === "string" && typeof item["range"] === "string" &&
    typeof item["identity_column"] === "string" && Array.isArray(item["writable_columns"]) &&
    item["writable_columns"].every((column) => typeof column === "string") && typeof item["allow_create"] === "boolean";
}

export function SheetAccessReview({ targets }: { targets: unknown }) {
  if (targets === undefined) return null;
  const valid = Array.isArray(targets) && targets.length > 0 && targets.every(isTarget);
  return <details className="relative text-sm">
    <summary aria-label="Sheet write access" className="flex h-8 cursor-pointer items-center whitespace-nowrap rounded-lg border border-border px-2.5"><span className="sm:hidden">Sheets</span><span className="hidden sm:inline">Sheet write access</span></summary>
    <div className="fixed right-4 top-24 z-40 max-h-[60vh] w-[min(28rem,calc(100vw-2rem))] overflow-y-auto rounded-xl border border-border bg-background p-4 shadow-lg">
      <p className="mb-3 text-xs text-muted-foreground">Review these destinations before approving and publishing. Writes require an authorized run and Google account access.</p>
      {!valid ? <p role="alert">Sheet access is incomplete. Correct the setup prompt and regenerate before publishing.</p> :
        (targets as SheetTarget[]).map((target, index) => <div key={index} className="border-t border-border py-3 first:border-0">
          <a href={`https://docs.google.com/spreadsheets/d/${encodeURIComponent(target.spreadsheet_id)}/edit`} target="_blank" rel="noreferrer" className="break-all text-primary">{target.spreadsheet_id}</a>
          <p className="mt-1 break-all font-medium">{target.range}</p>
          <p className="mt-1 text-xs">Match records by: {target.identity_column}</p>
          <p className="mt-1 break-words text-xs">Writable columns: {target.writable_columns.join(", ")}</p>
          <p className="mt-1 text-xs">{target.allow_create ? "Can create missing records" : "Existing records only"}</p>
        </div>)}
    </div>
  </details>;
}
