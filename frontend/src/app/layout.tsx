import { AppearanceSync } from "@/lib/appearance";
import type { ReactNode } from "react";
import { Toaster } from "@/components/ui/sonner";
import "../styles.css";
export const metadata = {
  title: "PraxilonAI — The Agentic AI Operating System",
  description: "Design coordinated agent workflows in a visual workspace.",
  icons: { icon: [{ url: "/mesh-icon.svg?v=20261022", type: "image/svg+xml" }, { url: "/favicon.ico?v=mesh-20261022", sizes: "any" }], apple: "/mesh-icon.png" },
};
export default function RootLayout({ children }: { children: ReactNode }) {
  return <html lang="en" suppressHydrationWarning><head>
    <link rel="preconnect" href="https://fonts.googleapis.com" />
    <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
    <link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&family=Space+Grotesk:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap" />
    <script dangerouslySetInnerHTML={{__html:"try{var t=localStorage.getItem('praxi-appearance-v1')||'system';var d=t==='dark'||(t==='system'&&matchMedia('(prefers-color-scheme: dark)').matches);document.documentElement.classList.toggle('dark',d);document.documentElement.dataset.appearance=t;document.documentElement.style.colorScheme=d?'dark':'light'}catch(e){}"}}/>
  </head><body><AppearanceSync/>{children}<Toaster position="bottom-right" /></body></html>;
}
