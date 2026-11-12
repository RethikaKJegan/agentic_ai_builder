/** Render-only formatting. Never submit these copies as workflow/payload authority. */
export function compactDemoText(value:string):string {
  return value
    .replace(/MODELED SUBWAY DEMONSTRATION — generated records and illustrative policies; not actual Subway operations or official company policy\./gi,'')
    .replace(/These records come from the MODELED SUBWAY DEMONSTRATION[^\n]*?(?:illustrative policies\.|$)/gi,'')
    .replace(/They are not actual Subway operations, official company policy, or operational company evidence\./gi,'')
    .replace(/generated records and illustrative policies; not actual Subway operations or official company policy\.?/gi,'')
    .replace(/MODELED SUBWAY DEMONSTRATION/gi,'')
    .replace(/(?:This is|These are)\s+Demo data\.?\s*/gi,'')
    .replace(/The result provides descriptive measures only and does not establish policy or operational outcomes\./gi,'')
    .replace(/\bDemo\s+Supplier\s+(\d+)\b/gi,'Supplier $1')
    .replace(/\bDemo\s+data\b\s*(?:[·:—–-]\s*)?/gi,'')
    .replace(/\bDemo(?:nstration)?\s+/gi,'')
    .replace(/\blimitations?\b/gi,'Notes')
    .replace(/(^|\n)\s*Notes:\s*(?=\n|$)/g,'$1')
    .replace(/[ \t]+\n/g,'\n').replace(/\n{3,}/g,'\n\n').trim();
}
export function subwayDisplay<T>(value:T,workspace:string|undefined):T {
  if(workspace!=='client-subway')return value;
  function visit(v:unknown):unknown {
    if(typeof v==='string')return compactDemoText(v);
    if(Array.isArray(v))return v.map(visit);
    if(v&&typeof v==='object')return Object.fromEntries(Object.entries(v).map(([k,x])=>[k,k==='resolved_payload'?x:visit(x)]));
    return v;
  }
  return visit(value) as T;
}
/** Opaque references are abbreviated only after serialization, never in graph/contract data. */
export function subwayDisplayText(value:string,workspace:string|undefined):string {
  return workspace==='client-subway'?compactDemoText(value)
    .replace(/(^|[^a-z0-9])demo(?:nstration)?(?=[^a-z0-9]|$)/gi,'$1dataset')
    .replace(/\bdemo(?:nstration)?\b/gi,'')
    .replace(/limitations/gi,'notes'):value;
}
export function subwayDisplayJson(value:unknown,workspace:string|undefined):string|undefined {
  // Parse strings before formatting: escaped newlines must not absorb following JSON fields.
  const shown=subwayDisplay(value,workspace);
  return subwayDisplayText(JSON.stringify(shown,null,2)??'',workspace);
}
