import { Suspense } from "react";
import Screen from "@/screens/app.index";
export const metadata = { title: "Overview \u2014 MESH" };
export default function Page() { return <Suspense fallback={<p className="p-6">Loading…</p>}><Screen /></Suspense>; }
