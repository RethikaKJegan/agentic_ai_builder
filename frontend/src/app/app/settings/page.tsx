import { Suspense } from "react";
import Screen from "@/screens/app.settings";
export const metadata = { title: "Settings \u2014 PraxilonAI" };
export default function Page() { return <Suspense fallback={<p className="p-6">Loading…</p>}><Screen /></Suspense>; }
