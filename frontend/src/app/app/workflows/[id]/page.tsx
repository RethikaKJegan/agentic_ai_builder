import { Suspense } from "react";
import Screen from "@/screens/app.workflows.$id";
export const metadata = { title: "Workflow editor \u2014 MESH" };
export default function Page() { return <Suspense fallback={<p className="p-6">Loading…</p>}><Screen /></Suspense>; }
