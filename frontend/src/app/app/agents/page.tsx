import { Suspense } from "react";
import Screen from "@/screens/app.agents";
export const metadata = { title: "Agents \u2014 MESH" };
export default function Page() { return <Suspense fallback={<p className="p-6">Loading…</p>}><Screen /></Suspense>; }
