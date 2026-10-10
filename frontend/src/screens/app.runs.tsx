import { PageHeader } from "@/features/runs/RunTrace";
import { ServerRunView } from "@/features/runs/ServerRunView";
export default function Screen() { return <div className="mx-auto max-w-5xl p-6 md:p-10"><PageHeader title="Runs" sub="Server run status and event history for an exact workflow revision." /><ServerRunView /></div>; }
