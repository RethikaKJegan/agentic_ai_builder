"use client";
import { useState, type FormEvent } from "react";
import Link from "next/link";
import { ArrowRight, Loader2, LockKeyhole } from "lucide-react";
import { LogoMark } from "@/components/mesh/Logo";

export default function Login() {
  const [email, setEmail] = useState("engineering@bellcorpstudio.com");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (busy) return;
    setBusy(true); setError("");
    try {
      const response = await fetch("/api/workspace-auth/login", {
        method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ email, password }),
      });
      const data = await response.json() as { error?: string };
      if (!response.ok) throw new Error(data.error || "Sign-in failed. Please try again.");
      // A full navigation discards any cached workspace state from an earlier session.
      window.location.assign("/app");
    } catch (failure) {
      setError(failure instanceof Error ? failure.message : "Unable to sign in. Please try again.");
      setBusy(false);
    }
  }
  return <main className="relative flex min-h-svh items-center justify-center overflow-hidden bg-atmosphere px-4 py-12">
    <div aria-hidden className="pointer-events-none absolute inset-0 bg-grid opacity-30" />
    <div className="relative w-full max-w-md">
      <Link href="/" className="mb-8 flex items-center justify-center gap-2 font-display text-xl font-semibold"><LogoMark className="h-7 w-7" />PraxilonAI</Link>
      <section className="rounded-2xl border border-border bg-background/90 p-6 shadow-soft backdrop-blur-xl sm:p-9" aria-labelledby="login-title">
        <div className="mb-6 flex h-11 w-11 items-center justify-center rounded-xl bg-primary/10 text-primary"><LockKeyhole className="h-5 w-5" /></div>
        <h1 id="login-title" className="font-display text-2xl font-semibold tracking-tight">Welcome back</h1>
        <p className="mt-2 text-sm text-muted-foreground">Sign in to your workspace to continue.</p>
        <form onSubmit={event => void submit(event)} className="mt-7 space-y-5">
          <div><label htmlFor="email" className="mb-2 block text-sm font-medium">Email</label><input id="email" name="email" type="email" autoComplete="username" required value={email} onChange={e => setEmail(e.target.value)} className="h-11 w-full rounded-lg border border-border bg-background px-3 text-sm outline-none focus-visible:ring-2 focus-visible:ring-primary" /></div>
          <div><label htmlFor="password" className="mb-2 block text-sm font-medium">Password</label><input id="password" name="password" type="password" autoComplete="current-password" required maxLength={128} value={password} onChange={e => setPassword(e.target.value)} className="h-11 w-full rounded-lg border border-border bg-background px-3 text-sm outline-none focus-visible:ring-2 focus-visible:ring-primary" /></div>
          {error && <p role="alert" className="rounded-lg border border-destructive/30 bg-destructive/10 p-3 text-sm text-destructive">{error}</p>}
          <button disabled={busy} type="submit" className="flex h-11 w-full items-center justify-center gap-2 rounded-lg bg-foreground text-sm font-medium text-background transition-colors hover:bg-primary disabled:opacity-60">{busy ? <><Loader2 className="h-4 w-4 animate-spin" />Signing in…</> : <>Sign in <ArrowRight className="h-4 w-4" /></>}</button>
        </form>
      </section>
      <Link href="/" className="mt-6 block text-center text-sm text-muted-foreground hover:text-foreground">Back to home</Link>
    </div>
  </main>;
}
