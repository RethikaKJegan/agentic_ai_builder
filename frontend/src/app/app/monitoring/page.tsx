import { Suspense } from "react";
import Screen from "@/screens/app.monitoring";
export const metadata = { title: "Monitoring \u2014 MESH" };
export default function Page() { return <Suspense fallback={<p className="p-6">Loading…</p>}><Screen /></Suspense>; }
