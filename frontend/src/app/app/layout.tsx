import { Suspense, type ReactNode } from "react";
import AppShell from "@/screens/app";
export default function Layout({ children }: { children: ReactNode }) {
  return <Suspense fallback={<p className="p-6">Loading workspace…</p>}><AppShell>{children}</AppShell></Suspense>;
}
