import { Suspense } from "react";
import Screen from "@/screens/app.workflows.index";
export const metadata = { title: "Workflows \u2014 PraxilonAI" };
export default function Page() { return <Suspense fallback={<p className="p-6">Loading…</p>}><Screen /></Suspense>; }
