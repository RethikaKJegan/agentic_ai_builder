import { Suspense } from "react";
import Screen from "@/screens/app.runs";
export const metadata = { title: "Run history \u2014 MESH" };
export default function Page() { return <Suspense fallback={<p className="p-6">Loading…</p>}><Screen /></Suspense>; }
