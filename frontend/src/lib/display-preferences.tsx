"use client";
import { create } from 'zustand';
import { useEffect } from 'react';
import { api } from '@/api/client';
import { useBackend } from '@/api/state';
export type DisplayPreferences={timezone:string;date_format:'locale'|'iso'|'day-first'|'month-first'};
const defaults:DisplayPreferences={timezone:'UTC',date_format:'locale'};
export const useDisplayPreferences=create<{value:DisplayPreferences;scope:string|null}>(()=>({value:defaults,scope:null}));
export function DisplayPreferencesSync() {
 const subject=useBackend(s=>s.session?.auth.subject);const status=useBackend(s=>s.status);const key=JSON.stringify(subject);
 useEffect(()=>{let live=true;useDisplayPreferences.setState({value:defaults,scope:key});if(status==='connected'&&subject)api.executionPreferences().then(r=>{if(live)useDisplayPreferences.setState({value:r.settings.display,scope:key});}).catch(()=>{});return()=>{live=false;};},[key,status,subject]);return null;
}
export function formatDisplayTimestamp(value:string|number,prefs:DisplayPreferences) {
 const date=new Date(value);if(!Number.isFinite(date.getTime()))return 'Date unavailable';
 const locale=prefs.date_format==='iso'?'sv-SE':prefs.date_format==='day-first'?'en-GB':prefs.date_format==='month-first'?'en-US':undefined;
 return new Intl.DateTimeFormat(locale,{timeZone:prefs.timezone,year:'numeric',month:'2-digit',day:'2-digit',hour:'2-digit',minute:'2-digit',timeZoneName:'short'}).format(date);
}
export function DisplayTime({value}:{value:string|number}) {const prefs=useDisplayPreferences(s=>s.value);const date=new Date(value);if(!Number.isFinite(date.getTime()))return <span>Date unavailable</span>;return <time dateTime={date.toISOString()}>{formatDisplayTimestamp(value,prefs)}</time>;}
