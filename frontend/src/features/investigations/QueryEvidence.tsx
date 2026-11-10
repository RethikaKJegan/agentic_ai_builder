import { z } from 'zod';

const evidence = z.object({
  query_id: z.string(),
  coverage: z.object({complete_scan:z.boolean(),aggregate_complete:z.boolean(),returned_rows:z.number(),total_result_rows:z.number(),has_more:z.boolean()}),
  result: z.object({matched_rows:z.number(),executed_at:z.string(),warnings:z.array(z.string()),columns:z.array(z.object({key:z.string(),label:z.string()})),rows:z.array(z.record(z.unknown()))}),
});
const waiting = z.object({state:z.literal('waiting_for_query'),query_job:z.object({progress:z.object({stage:z.string()})})});

export function QueryEvidence({instance}:{instance:unknown}) {
  const pending=waiting.safeParse(instance);
  if(pending.success)return <p role="status" className="text-sm">Query in progress: {pending.data.query_job.progress.stage}</p>;
  const saved=z.object({state:z.literal('completed'),verified_receipt:z.literal(true),output:evidence}).safeParse(instance);
  if(!saved.success)return null;
  const {result,coverage,query_id}=saved.data.output;
  return <section aria-label="Verified query results" className="min-w-0 space-y-3 rounded-lg border p-4">
    <h3 className="font-medium">Verified query results</h3>
    <p className="text-sm">{result.matched_rows} matching records. Showing {coverage.returned_rows} of {coverage.total_result_rows} result rows.</p>
    <p className="text-sm">{coverage.complete_scan?'All relevant source records were queried.':'Source coverage is incomplete.'} {coverage.aggregate_complete?'Statistics cover all matching records.':''} {coverage.has_more?'Additional result rows are available; the display limit does not change calculated totals.':''}</p>
    <div className="max-h-80 overflow-auto"><table className="w-full text-left text-sm"><thead><tr>{result.columns.map(c=><th key={c.key} className="p-2">{c.label}</th>)}</tr></thead><tbody>{result.rows.map((row,i)=><tr key={i}>{result.columns.map(c=><td key={c.key} className="break-words border-t p-2">{row[c.key]===null||row[c.key]===undefined?'—':String(row[c.key])}</td>)}</tr>)}</tbody></table></div>
    {result.warnings.map((warning,i)=><p key={i} className="text-sm text-muted-foreground">{warning}</p>)}
    <p className="break-all text-xs text-muted-foreground">Query {query_id} · Executed {result.executed_at}</p>
  </section>;
}
