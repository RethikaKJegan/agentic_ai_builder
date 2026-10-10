import type { ReactNode } from "react";
import { Toaster } from "@/components/ui/sonner";
import "../styles.css";
export const metadata = {
  title: "MESH — The Agentic AI Operating System",
  description: "Design coordinated agent workflows in a visual workspace.",
};
export default function RootLayout({ children }: { children: ReactNode }) {
  return <html lang="en"><head>
    <link rel="preconnect" href="https://fonts.googleapis.com" />
    <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
    <link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&family=Space+Grotesk:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap" />
  </head><body>{children}<Toaster position="bottom-right" /></body></html>;
}
