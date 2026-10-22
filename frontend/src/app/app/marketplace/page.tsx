import { Suspense } from "react";
import Screen from "@/screens/app.marketplace";
export const metadata = { title: "Marketplace \u2014 PraxilonAI" };
export default function Page() { return <Suspense fallback={<p className="p-6">Loading…</p>}><Screen /></Suspense>; }
