"use client";
export default function ErrorPage({ reset }: { reset: () => void }) { return <main className="p-10"><h1 className="text-2xl">This page could not load</h1><button onClick={reset} className="mt-4 rounded-lg border px-4 py-2">Try again</button></main>; }
