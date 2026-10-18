import { displayText } from "@/lib/display-text";
import type { api } from '@/api/client';
import { CheckCircle2, Package, Send, FileText, AlertCircle } from 'lucide-react';
type Status=Awaited<ReturnType<typeof api.procurementStatus>>;
export function ProcurementOverview({status}:{status:Status}) {
  const metrics=[['BOQ items',status.record_counts['boq_item']??0,Package],['RFQs',status.record_counts['rfq']??0,Send],['Quotations',status.record_counts['quotation']??0,FileText],['Orders',status.record_counts['purchase_order']??0,CheckCircle2]] as const;
  const next=status.phase==='COMPLETED'?'All required orders are closed.':status.phase==='STOPPED'?'Review the failed action below. Do not resend confirmed emails.':status.phase.includes('FULFILMENT')?'Supplier updates and buyer confirmations advance each order.':status.phase.includes('QUOTE')||status.phase==='RFQS_SENT'?'Waiting for qualifying supplier replies in their RFQ threads.':status.phase==='PO_RELEASED'?'Purchase orders are released. Check fulfilment monitoring below.':'The coordinator is preparing the next recorded project action.';
  const failed=Object.entries(status.actions).filter(([,a])=>['failed','blocked','rejected'].includes(a.state));
  const sent=Object.entries(status.actions).filter(([key,a])=>/^(send_|award_send|po_send)/.test(key)&&a.state==='completed').length;
  return <div className="space-y-5"><div className="rounded-2xl border bg-primary/[.03] p-5"><p className="text-[10px] font-semibold uppercase tracking-widest text-muted-foreground">Current project stage</p><h3 className="mt-2 text-xl font-semibold capitalize">{status.phase.replaceAll('_',' ').toLowerCase()}</h3><p className="mt-2 text-sm leading-6 text-muted-foreground">{next}</p></div><div className="grid grid-cols-2 gap-3 sm:grid-cols-4">{metrics.map(([label,count,Icon])=><div key={label} className="rounded-xl border bg-background p-4"><Icon className="mb-3 h-4 w-4 text-primary"/><p className="text-2xl font-semibold">{count}</p><p className="mt-1 text-xs text-muted-foreground">{displayText(label)}</p></div>)}</div>
    {!!status.issues.length&&<div className="rounded-xl border border-amber-200 bg-amber-50 p-4 text-sm text-amber-950"><p className="mb-2 flex items-center gap-2 font-medium"><AlertCircle className="h-4 w-4"/>Needs attention</p>{status.issues.map(i=><p key={i}>{i.replaceAll('_',' ')}</p>)}</div>}
    {!!failed.length&&<details className="rounded-xl border p-4"><summary className="cursor-pointer text-sm font-medium">Recorded failures · {failed.length}</summary><p className="mt-2 text-xs text-muted-foreground">Historical failures remain visible after recovery. A failed tracking update does not mean a confirmed email failed.</p>{failed.map(([key,a])=><p key={key} className="mt-2 break-all text-xs">{key.replaceAll('_',' ')} · {a.state} · {a.run_id}</p>)}</details>}
    <p className="text-xs text-muted-foreground">{sent} completed send actions recorded. Provider submission receipts do not guarantee inbox placement.</p>
  </div>;
}
export function PurchaseOrderProgress({status}:{status:string}) {
  const stages=['RELEASED','ACCEPTED','PACKED','DISPATCHED','DELIVERED','CLOSED'];
  const normalized=status.startsWith('PARTIALLY_')?status.slice(10):status;
  const current=stages.indexOf(normalized);
  return <ol aria-label="Order progress" className="my-4 grid grid-cols-3 gap-2 sm:grid-cols-6">{stages.map((s,i)=><li key={s} className={`rounded-lg px-2 py-2 text-center text-[10px] ${i<=current?'bg-emerald-50 text-emerald-800':'bg-muted text-muted-foreground'}`}>{s==='CLOSED'?'Buyer confirmed / closed':s.toLowerCase()}</li>)}</ol>;
}

export function ProcurementVendors({status}:{status:Status}) {
  const vendors=status.records?.filter(r=>r.record_type==='vendor')??[];
  const quotes=status.records?.filter(r=>r.record_type==='quotation')??[];
  return <div className="space-y-3">{vendors.map(v=>{const own=quotes.filter(q=>q.data['vendor_id']===v.record_id);return <article key={v.record_id} className="rounded-xl border bg-background p-4"><div className="flex flex-wrap justify-between gap-2"><h4 className="font-medium">{displayText(String(v.data['name']??v.record_id))}</h4><span className="text-[10px] text-muted-foreground">{String(v.data['status']??'')}</span></div><p className="mt-1 text-xs text-muted-foreground">{String(v.data['email']??'No contact recorded')}</p>{own.length?own.map(q=><div key={q.record_id} className="mt-3 rounded-lg bg-muted/60 p-3"><p className="text-xs font-medium">{String(q.data['status']??'').replaceAll('_',' ')}</p><p className="mt-1 text-[11px] text-muted-foreground">{String(q.data['rfq_id']??'')}</p><details className="mt-2 text-xs"><summary className="cursor-pointer text-primary">Quotation details</summary><pre className="mt-2 max-h-64 overflow-auto whitespace-pre-wrap break-words text-[11px]">{displayText(JSON.stringify({items:q.data['items'],financials:q.data['financials'],delivery:q.data['delivery_date'],valid_until:q.data['valid_until'],issues:q.data['unresolved_issue_ids']},null,2))}</pre></details></div>):<p className="mt-3 text-xs text-muted-foreground">No quotation record from this supplier yet.</p>}</article>;})}</div>;
}
