import {Suspense} from 'react';
import InvestigationWorkspace from '@/features/investigations/InvestigationWorkspace';
export const metadata={title:'Investigation workflow — PraxilonAI'};
export default function Page() {return <Suspense fallback={<p className="p-6 text-sm text-muted-foreground">Loading investigation…</p>}><InvestigationWorkspace/></Suspense>;}
