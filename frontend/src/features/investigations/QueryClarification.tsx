"use client";
import type {ActionDocument} from '@/api/orchestration';
import type {CompositionView} from '@/api/compositions';

export function QueryClarification(_props:{doc:ActionDocument;view:CompositionView}) {
 return <section aria-label="Query execution limitation" className="space-y-3 rounded-lg border border-warning/50 p-4">
  <h3 className="font-semibold">Query blocked</h3>
  <p className="text-sm">This step did not query the source because required meaning or a supported query capability was unavailable. The workflow and its execution history are preserved.</p>
  <p className="text-sm text-muted-foreground">No additional answer is required here. New workflows use available context and supported operations; unresolved actions remain blocked rather than inventing inputs or claiming completion.</p>
 </section>;
}
