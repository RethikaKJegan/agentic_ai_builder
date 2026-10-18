"use client";
import { useRef,useState } from "react";
import { Dialog,DialogContent,DialogDescription,DialogHeader,DialogTitle } from "@/components/ui/dialog";
import { api } from "@/api/client";
import { useBackend } from "@/api/state";
import { useMesh } from "@/domain/store";
import type { Workflow } from "@/domain/types";
import { ApiFeedback } from "./ApiFeedback";
import { toast } from "sonner";

export function RenameWorkflowDialog({workflow,onClose}:{workflow:Workflow;onClose:()=>void}) {
  const [name,setName]=useState(workflow.name);
  const [busy,setBusy]=useState(false);
  const [error,setError]=useState<Error|null>(null);
  const pending=useRef(false);
  const canEdit=useBackend(state=>state.can("workflow.edit"));
  const allowed=!workflow.serverVersion || canEdit;
  async function save() {
    if(pending.current || !allowed || !name.trim() || name.trim().length>200)return;
    pending.current=true;setBusy(true);setError(null);
    try {
      const title=workflow.serverVersion?(await api.renameWorkflow(workflow.id,name.trim(),workflow.name)).name:name.trim();
      useMesh.setState(state=>({workflows:state.workflows.map(item=>item.id===workflow.id?{
        ...item,name:title,...(item.serverVersion && item.canonical?{canonical:{...item.canonical,name:title}}:{})}:item)}));
      if(workflow.serverVersion)void useBackend.getState().refreshOverview();
      toast("Workflow renamed");onClose();
    } catch(caught){setError(caught instanceof Error?caught:new Error("The workflow could not be renamed."));}
    finally{pending.current=false;setBusy(false);}
  }
  return <Dialog open onOpenChange={open=>{if(!open&&!pending.current)onClose();}}>
    <DialogContent className="w-[calc(100vw-2rem)] sm:max-w-md" onEscapeKeyDown={event=>{if(busy)event.preventDefault();}} onPointerDownOutside={event=>{if(busy)event.preventDefault();}}>
      <DialogHeader><DialogTitle>Rename workflow</DialogTitle><DialogDescription>Choose a name to identify this workflow.</DialogDescription></DialogHeader>
      <form className="space-y-4" onSubmit={event=>{event.preventDefault();void save();}}>
        <label className="block text-sm">Workflow name<input autoFocus aria-label="Workflow name" maxLength={200} value={name} disabled={busy} onChange={event=>setName(event.target.value)} className="mt-2 w-full rounded-lg border bg-background px-3 py-2" /></label>
        <ApiFeedback error={error}/>
        <div className="flex justify-end gap-2"><button type="button" disabled={busy} onClick={onClose} className="rounded-lg border px-3 py-2 text-sm">Cancel</button><button type="submit" disabled={busy||!allowed||!name.trim()} className="rounded-lg bg-primary px-3 py-2 text-sm text-primary-foreground disabled:opacity-40">{busy?"Saving…":"Save name"}</button></div>
      </form>
    </DialogContent>
  </Dialog>;
}
