"use client";
import {useCallback,useState} from "react";
import {api} from "@/api/client";
import type {RelationshipView} from "@/api/data-relationships";
import DetailedGraph from "./DetailedGraph";
import StructuralRelationships from "./StructuralRelationships";
import BusinessOntology from "./BusinessOntology";
import {ApiFeedback} from "@/features/workflows/ApiFeedback";

export default function Relationships({canManage}:{canManage:boolean}) {
 const [inspection,setInspection]=useState<""|"links"|"mappings">("");
 const [status,setStatus]=useState<Pick<RelationshipView,"stale"|"build_status"|"last_error">>();
 const [busy,setBusy]=useState(false),[refresh,setRefresh]=useState(0),[error,setError]=useState<Error>();
 const receive=useCallback((next:Pick<RelationshipView,"stale"|"build_status"|"last_error">)=>setStatus(next),[]);
 const rebuild=async()=>{if(busy)return;setBusy(true);setError(undefined);try{await api.relationships("build");setRefresh(x=>x+1);}catch(e){setError(e instanceof Error?e:new Error("Semantic Intelligence rebuild could not be requested."));}finally{setBusy(false);}};
 return <section aria-label="Semantic Intelligence workspace" className="space-y-4"><div className="flex flex-wrap items-start justify-between gap-3"><div><h2 className="text-lg font-semibold">Semantic Intelligence</h2><p className="mt-1 max-w-3xl text-sm text-muted-foreground">View one connection or all connections together. Agents use this Semantic Intelligence to select relevant data before creating workflows.</p></div><button className="rounded-lg border px-3 py-2 text-sm disabled:opacity-40" disabled={!canManage||busy||status?.build_status==="queued"||status?.build_status==="running"} onClick={()=>void rebuild()}>{busy||status?.build_status==="queued"||status?.build_status==="running"?"Updating metadata graph…":"Regenerate Semantic Intelligence"}</button></div><ApiFeedback error={error}/><BusinessOntology canManage={canManage} onStatus={receive} refreshToken={refresh}/><details onToggle={event=>{if(!event.currentTarget.open)setInspection("");}}><summary className="cursor-pointer text-sm">Review source links and mappings</summary><div className="my-3 flex gap-2"><button className="rounded-lg border p-2 text-sm" onClick={()=>setInspection("links")}>Source relationships</button><button className="rounded-lg border p-2 text-sm" onClick={()=>setInspection("mappings")}>Source mappings</button></div>{inspection==="links"&&<StructuralRelationships canManage={canManage}/>} {inspection==="mappings"&&<DetailedGraph canManage={canManage} onStatus={receive} onChanged={()=>setRefresh(x=>x+1)} refreshToken={refresh}/>}</details></section>;
}
