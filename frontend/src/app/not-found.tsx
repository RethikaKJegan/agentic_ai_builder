import Link from "next/link";
export default function NotFound() { return <main className="flex min-h-screen flex-col items-center justify-center gap-4"><h1 className="text-4xl">Page not found</h1><Link href="/app" className="text-primary">Back to workspace</Link></main>; }
