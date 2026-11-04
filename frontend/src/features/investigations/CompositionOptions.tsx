'use client';
import {useEffect,useState} from 'react';
import {api} from '@/api/client';
import {useBackend} from '@/api/state';
import {InputError} from '@/api/feedback';
import type {ToolRecord} from '@/api/client';
import {GoogleAccountSelect} from '@/features/workflows/GoogleWorkflowConnection';
type Schema={type?:string;properties?:Record<string,Schema>;required?:string[];enum?:unknown[];description?:string};
export type CompositionOptionsValue={google:string;tool:string;values:Record<string,string>;destination:string;engineer:string;packageId:string;packageRevision:number};
export const emptyCompositionOptions:CompositionOptionsValue={google:'',tool:'',values:{},destination:'',engineer:'',packageId:'',packageRevision:1};
const supported=new Set(['mail_search','mail_message','mail_thread','mail_draft','calendar_list','calendar_create','calendar_update','calendar_cancel','read_spreadsheet','update_spreadsheet','discover_spreadsheet','create_spreadsheet','create_spreadsheet_report','create_spreadsheet_tabs','upsert_spreadsheet_record']);
const label=(s:string)=>s.replaceAll('_',' ').replace(/\b\w/g,c=>c.toUpperCase());
export function parseOperationInputs(schema:Schema,values:Record<string,string>,path=''):Record<string,unknown>{
 const result:Record<string,unknown>={};
 for(const [name,field] of Object.entries(schema.properties??{})){
  const key=path?path+'.'+name:name;const raw=values[key];let value:unknown;
  if(field.type==='object'&&field.properties){const child=parseOperationInputs(field,values,key);if(Object.keys(child).length)value=child;}
  else if(raw!==undefined&&raw!==''){
   if(field.type==='boolean')value=raw==='true';
   else if(field.type==='number'||field.type==='integer'){value=Number(raw);if(!Number.isFinite(value)||field.type==='integer'&&!Number.isInteger(value))throw new InputError(`Enter a valid number for ${label(key)}.`);}
   else if(field.type==='array'||field.type==='object'){try{value=JSON.parse(raw);}catch{throw new InputError(`Enter valid JSON for ${label(key)}.`);}if(field.type==='array'&&!Array.isArray(value)||field.type==='object'&&(!value||Array.isArray(value)||typeof value!=='object'))throw new InputError(`Check the format of ${label(key)}.`);}
   else value=raw;
  }
  if(value===undefined&&schema.required?.includes(name))throw new InputError(`Provide ${label(key)} for the selected action.`);
  if(value!==undefined)result[name]=value;
 }
 return result;
}
export function restoreCompositionOptions(context:Record<string,unknown>,tools:ToolRecord[]):CompositionOptionsValue {
 const resources=(context['resources']??{}) as Record<string,unknown>;const operations=(resources['operation_inputs']??{}) as Record<string,Record<string,unknown>>;
 const selected=tools.find(t=>Object.hasOwn(operations,'tool.'+t.tool_id));const values:Record<string,string>={};
 function fields(schema:Schema,input:Record<string,unknown>,path=''){for(const [name,field] of Object.entries(schema.properties??{})){const key=path?path+'.'+name:name;const value=input[name];if(value===undefined)continue;if(field.type==='object'&&field.properties&&value&&typeof value==='object'&&!Array.isArray(value))fields(field,value as Record<string,unknown>,key);else values[key]=typeof value==='object'?JSON.stringify(value):String(value);}}
 if(selected)fields(selected.definition.input_schema as Schema,operations['tool.'+selected.tool_id]??{});
 return {...emptyCompositionOptions,google:typeof context['google_connection_id']==='string'?context['google_connection_id']:'',packageId:typeof context['client_package_id']==='string'?context['client_package_id']:'',packageRevision:typeof context['client_package_revision']==='number'?context['client_package_revision']:1,tool:selected?.tool_id??'',values,destination:typeof resources['destination']==='string'?resources['destination']:'',engineer:typeof resources['engineer_id']==='string'?resources['engineer_id']:''};
}
export function compositionActionInputs(value:CompositionOptionsValue,tools:ToolRecord[]) {
 const body:Record<string,unknown>={};if(value.packageId){body['client_package_id']=value.packageId;body['client_package_revision']=value.packageRevision;}if(value.google)body['google_connection_id']=value.google;
 if(!value.tool)return body;
 const tool=tools.find(t=>t.tool_id===value.tool&&supported.has(t.definition.capability)&&t.definition.availability==='enabled');
 if(!tool)throw new InputError('The selected action is no longer available. Refresh the tool list.');
 const inputs=parseOperationInputs(tool.definition.input_schema as Schema,value.values);const cid='tool.'+tool.tool_id;
 if((tool.definition.allowed_destinations??[]).length&&!value.destination)throw new InputError('Select the authorized destination for this action.');
 if(tool.definition.capability==='calendar_create'&&!value.engineer.trim())throw new InputError('Provide the engineer reference for this inspection request.');
 body['operations']=[{capability_id:cid,inputs}];body['resources']={operation_inputs:{[cid]:inputs},...(value.destination?{destination:value.destination}:{}),...(value.engineer.trim()?{engineer_id:value.engineer.trim()}:{})};return body;
}
function Fields({schema,value,onChange,path=''}:{schema:Schema;value:CompositionOptionsValue;onChange:(v:CompositionOptionsValue)=>void;path?:string}){
 return <div className="space-y-3">{Object.entries(schema.properties??{}).map(([name,field])=>{const key=path?path+'.'+name:name;const title=label(name)+(schema.required?.includes(name)?' *':'');const update=(raw:string)=>onChange({...value,values:{...value.values,[key]:raw}});return field.type==='object'&&field.properties?<fieldset key={key} className="rounded-lg border p-3"><legend className="px-1 text-xs font-medium">{title}</legend><Fields schema={field} value={value} onChange={onChange} path={key}/></fieldset>:<label key={key} className="block text-xs">{title}{field.enum||field.type==='boolean'?<select aria-label={key} value={value.values[key]??''} onChange={e=>update(e.target.value)} className="mt-1 w-full rounded-lg border bg-background p-2 text-sm"><option value="">Choose…</option>{(field.enum??[true,false]).map(v=><option key={String(v)} value={String(v)}>{String(v)}</option>)}</select>:field.type==='array'||field.type==='object'?<textarea aria-label={key} value={value.values[key]??''} onChange={e=>update(e.target.value)} placeholder={field.type==='array'?'[]':'{}'} rows={3} className="mt-1 w-full rounded-lg border bg-background p-2 text-sm"/>:<input aria-label={key} value={value.values[key]??''} onChange={e=>update(e.target.value)} className="mt-1 w-full rounded-lg border bg-background p-2 text-sm"/>}{field.description&&<span className="mt-1 block text-muted-foreground">{field.description}</span>}</label>;})}</div>;
}
export function CompositionOptions({value,onChange}:{value:CompositionOptionsValue;onChange:(v:CompositionOptionsValue)=>void}){
 const enabled=useBackend(s=>s.session?.dynamic_composition_available===true);const [packages,setPackages]=useState<{package_id:string;revision:number;client_id:string;domain:string}[]>([]);const [packageError,setPackageError]=useState<string|null>(null);
 useEffect(()=>{if(!enabled)return;let active=true;api.clientPackages().then(result=>{if(active)setPackages(result.items);}).catch(()=>{if(active)setPackageError('Client knowledge choices could not be loaded. Existing company context remains selected.');});return()=>{active=false;};},[enabled]);
 const tools=useBackend(s=>s.tools);const available=value.packageId?[]:tools.filter(t=>supported.has(t.definition.capability)&&t.definition.availability==='enabled');const tool=available.find(t=>t.tool_id===value.tool);
 if(!enabled)return null;
 return <section className="mt-3 space-y-3 rounded-lg border p-3 text-foreground"><h3 className="text-sm font-medium">Business context and connected tools</h3>{packages.length>0&&<label className="block text-xs">Client knowledge<select aria-label="Client knowledge" value={value.packageId?`${value.packageId}:${value.packageRevision}`:''} onChange={e=>{const selected=packages.find(p=>`${p.package_id}:${p.revision}`===e.target.value);onChange({...value,packageId:selected?.package_id??'',packageRevision:selected?.revision??1,tool:'',values:{}});}} className="mt-1 w-full rounded-lg border bg-background p-2 text-sm"><option value="">Existing company sources</option>{packages.map(p=><option key={`${p.package_id}:${p.revision}`} value={`${p.package_id}:${p.revision}`}>{p.client_id} · {p.domain} · revision {p.revision}</option>)}</select></label>}{packageError&&<p role="status" className="text-xs text-muted-foreground">{packageError}</p>}<GoogleAccountSelect value={value.google} onChange={google=>onChange({...value,google})}/><label className="block text-xs">Optional connected action<select aria-label="Optional connected action" value={value.tool} onChange={e=>onChange({...value,tool:e.target.value,values:{},destination:''})} className="mt-1 w-full rounded-lg border bg-background p-2 text-sm"><option value="">No additional action</option>{available.map(t=><option key={t.tool_id} value={t.tool_id}>{label(t.definition.capability)}</option>)}</select></label>{tool&&<><p className="text-xs text-muted-foreground">{tool.definition.description}</p><Fields schema={tool.definition.input_schema as Schema} value={value} onChange={onChange}/>{(tool.definition.allowed_destinations??[]).length>0&&<label className="block text-xs">Authorized destination<select aria-label="Authorized destination" value={value.destination} onChange={e=>onChange({...value,destination:e.target.value})} className="mt-1 w-full rounded-lg border bg-background p-2 text-sm"><option value="">Choose…</option>{(tool.definition.allowed_destinations??[]).map(d=><option key={d} value={d}>{label(d)}</option>)}</select></label>}{tool.definition.capability==='calendar_create'&&<label className="block text-xs">Engineer reference<input aria-label="Engineer reference" value={value.engineer} onChange={e=>onChange({...value,engineer:e.target.value})} className="mt-1 w-full rounded-lg border bg-background p-2 text-sm"/></label>}<p className="text-xs text-muted-foreground">The planner must include this selected action. Execution still requires current tool access and any action approval.</p></>}</section>;
}
