/** Format UI copy only. Never use this value for requests, IDs or persisted data. */
export function displayText<T>(value: T, engine?: string): T {
  if (typeof value !== "string" || !/knowledge graph|northwind/i.test(value)) return value;
  const source = engine ?? (/mongo(?:db)?|atlas/i.test(value) ? "mongodb" : /postgres|supabase/i.test(value) ? "postgresql" : undefined);
  const replacement = source === "mongodb" ? "MongoDB" : source === "postgresql" ? "Postgres" : /northwind(?=[./]|$)/i.test(value) ? "Postgres" : "";
  return value.replace(/knowledge graph/gi, "Semantic Intelligence")
    .replace(/northwind[ _-]+(?:supabase|atlas|postgres(?:ql)?|mongo(?:db)?)/gi, replacement)
    .replace(/northwind/gi, replacement)
    .replace(/\b(MongoDB|Postgres)(?:[ _-]+\1)+\b/gi, "$1") as T;
}

export function connectionDisplayName(name: string, engine: string): string {
  return /northwind/i.test(name) ? (engine === "mongodb" ? "MongoDB" : "Postgres") : displayText(name, engine);
}
