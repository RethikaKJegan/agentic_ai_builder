'use client';
import {InputError} from '@/api/feedback';
import type {ToolRecord} from '@/api/client';
import {GoogleAccountSelect} from '@/features/workflows/GoogleWorkflowConnection';
type Schema={type?:string;properties?:Record<string,Schema>;required?:string[];enum?:unknown[];description?:string};
export type CompositionOptionsValue={google:string;tool:string;values:Record<string,string>;destination:string;engineer:string;packageId:string;packageRevision:number};
export const emptyCompositionOptions:CompositionOptionsValue={google:'',tool:'',values:{},destination:'',engineer:'',packageId:'',packageRevision:1};

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
 const tool=tools.find(t=>t.tool_id===value.tool&&t.definition.availability==='enabled');
 if(!tool)throw new InputError('The selected action is no longer available. Refresh the tool list.');
 const inputs=parseOperationInputs(tool.definition.input_schema as Schema,value.values);const cid='tool.'+tool.tool_id;
 if((tool.definition.allowed_destinations??[]).length&&!value.destination)throw new InputError('Select the authorized destination for this action.');
 if(tool.definition.capability==='calendar_create'&&!value.engineer.trim())throw new InputError('Provide the engineer reference for this inspection request.');
 body['operations']=[{capability_id:cid,inputs}];body['resources']={operation_inputs:{[cid]:inputs},...(value.destination?{destination:value.destination}:{}),...(value.engineer.trim()?{engineer_id:value.engineer.trim()}:{})};return body;
}
export function CompositionOptions({value,onChange}:{value:CompositionOptionsValue;onChange:(v:CompositionOptionsValue)=>void}){
 return <section className="mt-3 space-y-3 rounded-lg border p-3 text-foreground" aria-label="Connected account"><GoogleAccountSelect value={value.google} onChange={google=>onChange({...value,google})}/><p className="text-xs text-muted-foreground">Describe the result you want. Available tools and their inputs are selected from the workspace Registry.</p></section>;
}
