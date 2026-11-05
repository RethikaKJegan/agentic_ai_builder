"use client";
import { ApiError } from "@/api/client";

type Field = { type?: string; format?: string; properties?: Record<string, Field>; enum?: unknown[]; items?: Field };
export function requiredBusinessInputs(error: Error | null): Record<string, Field> {
  if (!(error instanceof ApiError) || error.error.error_code !== "ACTION_INPUT_REQUIRED") return {};
  const fields = error.error.details?.['required_inputs'];
  return fields && typeof fields === "object" && !Array.isArray(fields) ? fields as Record<string, Field> : {};
}
const label = (key: string) => ({to:"Email recipient",recipient:"Email recipient",calendar_id:"Calendar",assessment_date:"Assessment date"}[key] ?? key.replaceAll('_',' ').replace(/\b\w/g,c=>c.toUpperCase()));
export function BusinessInputs({error,values,onChange}:{error:Error|null;values:Record<string,unknown>;onChange:(v:Record<string,unknown>)=>void}) {
  const fields=requiredBusinessInputs(error);
  if(!Object.keys(fields).length)return null;
  function render(name:string,schema:Field,path:string[]=[]) {
    const parts=[...path,name];let value:unknown=values;
    for(const p of parts)value=value && typeof value==='object'?(value as Record<string,unknown>)[p]:undefined;
    const update=(next:unknown)=>{const result=structuredClone(values);let cursor=result;for(const p of path){cursor[p]??={};cursor=cursor[p] as Record<string,unknown>;}cursor[name]=next;onChange(result);};
    if(schema.type==='object'&&schema.properties)return <fieldset key={name} className="space-y-2 rounded-lg border p-3"><legend>{label(name)}</legend>{Object.entries(schema.properties).map(([k,s])=>render(k,s,parts))}</fieldset>;
    return <label key={name} className="block text-sm">{label(name)}{schema.enum||schema.type==='boolean'?<select aria-label={label(name)} value={value===undefined?'':String(value)} onChange={e=>update(schema.type==='boolean'?e.target.value==='true':e.target.value)} className="mt-1 w-full rounded-lg border bg-background p-2"><option value="">Choose…</option>{(schema.enum??[true,false]).map(v=><option key={String(v)} value={String(v)}>{String(v)}</option>)}</select>:schema.type==='array'?<textarea aria-label={label(name)} value={Array.isArray(value)?value.join('\n'):''} placeholder="One value per line" onChange={e=>update(e.target.value.split('\n').filter(Boolean))} className="mt-1 w-full rounded-lg border bg-background p-2"/>:<input aria-label={label(name)} type={schema.type==='number'||schema.type==='integer'?'number':schema.format==='email'||/recipient|^to$/.test(name)?'email':schema.format==='date'?'date':'text'} value={value===undefined?'':String(value)} onChange={e=>update(schema.type==='number'||schema.type==='integer'?Number(e.target.value):e.target.value)} className="mt-1 w-full rounded-lg border bg-background p-2"/>}</label>;
  }
  return <section aria-label="Information needed" className="space-y-3 rounded-lg border p-4"><p className="text-sm">A little more information is needed for your request.</p>{Object.entries(fields).map(([k,s])=>render(k,s))}</section>;
}
