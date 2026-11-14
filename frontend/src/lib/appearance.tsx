"use client";
import { useEffect,useState } from 'react';
export type Appearance='light'|'dark'|'system';
export const APPEARANCE_KEY='praxi-appearance-v1';
export function applyAppearance(value:Appearance,persist=true) {
 if(!['light','dark','system'].includes(value))return;
 if(persist)localStorage.setItem(APPEARANCE_KEY,value);
 const dark=value==='dark'||(value==='system'&&window.matchMedia?.('(prefers-color-scheme: dark)').matches);
 document.documentElement.classList.toggle('dark',!!dark);document.documentElement.dataset['appearance']=value;document.documentElement.style.colorScheme=dark?'dark':'light';
 window.dispatchEvent(new Event('praxi-appearance-change'));
}
export function AppearanceSync() {
 useEffect(()=>{const sync=()=>{let value:Appearance='system';try{const saved=localStorage.getItem(APPEARANCE_KEY);if(saved==='light'||saved==='dark')value=saved;}catch{/* Browser storage may be unavailable; follow the system appearance. */}applyAppearance(value,false);};sync();const media=window.matchMedia?.('(prefers-color-scheme: dark)');media?.addEventListener('change',sync);window.addEventListener('storage',sync);return()=>{media?.removeEventListener('change',sync);window.removeEventListener('storage',sync);};},[]);return null;
}
export function AppearanceControls() {
 const [value,setValue]=useState<Appearance>('system');const [error,setError]=useState('');
 useEffect(()=>{const sync=()=>setValue((document.documentElement.dataset['appearance'] as Appearance)||'system');sync();window.addEventListener('praxi-appearance-change',sync);return()=>window.removeEventListener('praxi-appearance-change',sync);},[]);
 return <fieldset><legend className="text-sm font-medium">Appearance</legend><div className="mt-3 flex gap-2">{(['light','dark','system'] as const).map(mode=><button type="button" aria-pressed={mode===value} key={mode} className={`rounded-lg border px-4 py-2 text-sm capitalize ${mode===value?'border-primary text-primary':''}`} onClick={()=>{try{applyAppearance(mode);setValue(mode);setError('');}catch{setError('Appearance could not be saved in this browser.');}}}>{mode}</button>)}</div>{error&&<p role="alert">{error}</p>}</fieldset>;
}
