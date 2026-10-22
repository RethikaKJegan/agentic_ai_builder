import { Suspense } from "react";
import Screen from "@/screens/index";
export const metadata = { title: "PraxilonAI \u2014 Describe the work. Deploy the intelligence." };
export default function Page() { return <Suspense fallback={<p className="p-6">Loading…</p>}><Screen /></Suspense>; }
