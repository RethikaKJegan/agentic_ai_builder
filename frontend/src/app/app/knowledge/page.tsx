import { Suspense } from "react";
import Screen from "@/screens/app.knowledge";
export const metadata = { title: "Knowledge \u2014 PraxilonAI" };
export default function Page() { return <Suspense fallback={<p className="p-6">Loading…</p>}><Screen /></Suspense>; }
