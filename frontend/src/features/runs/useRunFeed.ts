"use client";
import { useEffect, useState } from "react";
import { api, type RunRecord } from "@/api/client";
import { assertRunTransition, reconcileEvents } from "@/api/control";
import type { RunEvent } from "@/api/contracts.generated";

export const terminalRun = (status: string) => ["completed", "failed", "blocked", "rejected", "cancelled"].includes(status);
// Concurrent consumers share only in-flight reads. No response cache or authority.
const pending=new Map<string,Promise<unknown>>();
export function sharedRead<T>(key:string,read:()=>Promise<T>):Promise<T>{
  const existing=pending.get(key);if(existing)return existing as Promise<T>;
  const task=read().finally(()=>pending.delete(key));pending.set(key,task);return task;
}
export function useRunFeed(runId:string,enabled:boolean,attempt=0){
  const [record,setRecord]=useState<{run:RunRecord;events:RunEvent[];hasMore:boolean}|null>(null);
  const [error,setError]=useState<Error|null>(null);
  const [loading,setLoading]=useState(false);
  const [refreshCount,setRefreshCount]=useState(0);
  useEffect(()=>{
    if(!enabled || !runId)return;
    let disposed=false;let timer:ReturnType<typeof setTimeout>;
    // Each effect owns one serialized sequence. Its last fully confirmed result
    // is retained on errors, and stale effects cannot commit to a new selection.
    let previous:typeof record=null;
    let failures=0;
    const load=async()=>{
      setLoading(true);let done=false;let more=false;
      try{
        const result=await sharedRead(`run:${runId}`,()=>api.request("get_run",{run_id:runId}));
        if(result.run.run_id!==runId)throw new Error("The runtime returned a different run.");
        if(previous){
          if(previous.run.workflow_id!==result.run.workflow_id || previous.run.workflow_version!==result.run.workflow_version)throw new Error("Run revision changed.");
          assertRunTransition(previous.run.status,result.run.status);
        }
        const after=previous?.events.reduce((max,event)=>Math.max(max,Number(event.details?.["recorded_sequence"])||0),0)??0;
        const page=await sharedRead(`events:${runId}:${after}`,()=>after?api.eventPage(runId,after):api.request("list_run_events",{run_id:runId}));
        const events=reconcileEvents(previous?.events??[],page.items,result.run);
        more=page.has_more;done=terminalRun(result.run.status) && !more;
        previous={run:result.run,events,hasMore:more};failures=0;
        if(!disposed){setRecord(previous);setError(null);}
      }catch(caught){failures++;if(!disposed)setError(caught instanceof Error?caught:new Error("Run updates are interrupted."));}
      finally{if(!disposed){setLoading(false);if(!done)timer=setTimeout(()=>void load(),failures?Math.min(30000,3000*2**Math.min(failures-1,4)):more?250:3000);}}
    };
    void load();
    return()=>{disposed=true;clearTimeout(timer);};
  },[runId,enabled,attempt,refreshCount]);
  const current=enabled && record?.run.run_id===runId?record:null;
  return {run:current?.run??null,events:current?.events??[],hasMore:current?.hasMore??false,error,loading,refresh:()=>setRefreshCount(n=>n+1)};
}
