"use client";
import { displayText } from "@/lib/display-text";
import { Link } from "@/lib/navigation";
import { motion, useReducedMotion } from "motion/react";
import { useEffect, useState, type MouseEvent, type ReactNode } from "react";
import { ArrowRight, ArrowUpRight, Check, Clock, Coins, ShieldCheck, Sparkles } from "lucide-react";
import { Logo, LogoMark } from "@/components/mesh/Logo";
import { HeroNetwork } from "@/features/landing/HeroNetwork";
import { CinematicHero } from "@/features/landing/cinematic/CinematicHero";
import { NODE_META } from "@/features/builder/nodeMeta";
import { TEMPLATES } from "@/domain/templates";
import type { NodeKind } from "@/domain/types";



const ease = [0.22, 1, 0.36, 1] as const;

function Reveal({
  children,
  delay = 0,
  className,
}: {
  children: ReactNode;
  delay?: number;
  className?: string;
}) {
  return (
    <motion.div
      className={className}
      initial={{ opacity: 0, y: 24 }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true, margin: "-80px" }}
      transition={{ duration: 0.7, delay, ease }}
    >
      {children}
    </motion.div>
  );
}

function Nav() {
  const [scrolled, setScrolled] = useState(false);
  useEffect(() => {
    let raf = 0;
    const on = () => {
      cancelAnimationFrame(raf);
      raf = requestAnimationFrame(() => setScrolled(window.scrollY > 12));
    };
    on();
    window.addEventListener("scroll", on, { passive: true });
    return () => {
      window.removeEventListener("scroll", on);
      cancelAnimationFrame(raf);
    };
  }, []);
  const toTop = (e: MouseEvent) => {
    e.preventDefault();
    const reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    window.scrollTo({ top: 0, behavior: reduce ? "auto" : "smooth" });
  };
  return (
    <header
      className={`fixed inset-x-0 top-0 z-50 overflow-hidden backdrop-saturate-150 transition-[background-color,backdrop-filter,box-shadow] duration-500 ${
        scrolled
          ? "bg-background/80 shadow-soft backdrop-blur-2xl"
          : "bg-background/45 backdrop-blur-xl"
      }`}
    >
      <div
        aria-hidden
        className={`pointer-events-none absolute inset-0 header-glow transition-opacity duration-700 ${scrolled ? "opacity-100" : "opacity-0"}`}
      />
      <div
        aria-hidden
        className={`pointer-events-none absolute inset-x-0 bottom-0 h-px bg-gradient-to-r from-transparent via-primary/60 to-transparent transition-opacity duration-500 ${scrolled ? "opacity-100" : "opacity-40"}`}
      />
      <div
        className={`relative mx-auto grid max-w-7xl grid-cols-[1fr_auto_1fr] items-center px-4 transition-[height] duration-500 sm:px-6 ${scrolled ? "h-14" : "h-16"}`}
      >
        <span />
        <a
          href="/"
          onClick={toTop}
          aria-label="MESH — back to top"
          className="group relative flex items-center gap-2 rounded-lg px-2 py-1 transition-transform duration-300 [transition-timing-function:cubic-bezier(0.34,1.56,0.64,1)] hover:-translate-y-0.5 hover:scale-[1.03]"
        >
          <span
            aria-hidden
            className="absolute inset-0 -z-10 rounded-full bg-primary/0 blur-xl transition-colors duration-300 group-hover:bg-primary/20"
          />
          <LogoMark className="h-6 w-6 transition-[filter] duration-300 group-hover:drop-shadow-[0_0_8px_var(--primary)]" />
          <span className="font-display text-[17px] font-semibold tracking-tight">MESH</span>
        </a>
        <div className="flex justify-end">
          <Link
            to="/login"
            aria-label="Launch Workspace"
            className="inline-flex h-9 items-center gap-1.5 rounded-full bg-foreground px-3 text-sm font-medium text-background transition-colors hover:bg-primary sm:px-4"
          >
            <span className="sm:hidden">Launch</span>
            <span className="hidden sm:inline">Launch Workspace</span>{" "}
            <ArrowRight className="h-3.5 w-3.5" />
          </Link>
        </div>
      </div>
    </header>
  );
}

function Hero() {
  return (
    <section className="relative flex min-h-[100svh] items-center overflow-hidden bg-atmosphere pt-16">
      <div className="pointer-events-none absolute inset-0 bg-grid opacity-40 [mask-image:radial-gradient(70%_60%_at_50%_45%,black,transparent)]" />
      <div className="pointer-events-none absolute inset-0 opacity-90">
        <HeroNetwork />
      </div>
      <div className="pointer-events-none absolute inset-0 bg-gradient-to-b from-background/40 via-background/70 to-background" />
      <div className="relative mx-auto w-full max-w-7xl px-6">
        <motion.p
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ duration: 0.8 }}
          className="mb-8 inline-flex items-center gap-2 rounded-full border border-border-accent bg-background/80 px-3 py-1 text-xs font-medium text-primary-deep"
        >
          <span className="h-1.5 w-1.5 rounded-full bg-primary" /> Describe the work. Deploy the
          intelligence.
        </motion.p>
        <motion.h1
          initial={{ opacity: 0, y: 30 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 1, ease }}
          className="max-w-5xl text-5xl font-semibold leading-[0.98] sm:text-7xl lg:text-[96px]"
        >
          Your business runs on processes.{" "}
          <span className="text-primary">Now let intelligence run them.</span>
        </motion.h1>
        <motion.p
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.9, delay: 0.2, ease }}
          className="mt-8 max-w-xl text-lg leading-relaxed text-muted-foreground"
        >
          Turn any business process into a coordinated team of AI agents. Design visually, govern
          centrally, deploy confidently.
        </motion.p>
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.9, delay: 0.35, ease }}
          className="mt-10 flex flex-wrap gap-3"
        >
          <Link
            to="/login"
            className="group inline-flex h-12 items-center gap-2 rounded-full bg-primary px-6 font-medium text-primary-foreground shadow-lift transition-colors hover:bg-primary-deep"
          >
            Start building{" "}
            <ArrowRight className="h-4 w-4 transition-transform group-hover:translate-x-0.5" />
          </Link>
        </motion.div>
      </div>
    </section>
  );
}

function Chapter({
  n,
  title,
  body,
  children,
  id,
  flip,
}: {
  n: string;
  title: string;
  body: string;
  children: ReactNode;
  id?: string;
  flip?: boolean;
}) {
  return (
    <section
      id={id}
      className="mx-auto grid max-w-7xl scroll-mt-20 items-center gap-12 px-6 py-24 md:py-32 lg:grid-cols-12"
    >
      <Reveal className={`min-w-0 lg:col-span-5 ${flip ? "lg:order-2" : ""}`}>
        <p className="font-mono text-xs text-primary">{n}</p>
        <h2 className="mt-4 text-4xl font-semibold leading-[1.02] md:text-6xl">{displayText(title)}</h2>
        <p className="mt-6 max-w-md text-lg leading-relaxed text-muted-foreground">{body}</p>
      </Reveal>
      <Reveal delay={0.1} className="min-w-0 lg:col-span-7">
        {children}
      </Reveal>
    </section>
  );
}

function Frame({ children, label }: { children: ReactNode; label: string }) {
  return (
    <div className="overflow-hidden rounded-2xl border border-border bg-background shadow-lift">
      <div className="flex items-center gap-2 border-b border-border bg-canvas px-4 py-2.5">
        <span className="h-2.5 w-2.5 rounded-full bg-border" />
        <span className="h-2.5 w-2.5 rounded-full bg-border" />
        <span className="h-2.5 w-2.5 rounded-full bg-border" />
        <span className="ml-3 font-mono text-[11px] text-muted-foreground">{displayText(label)}</span>
        <span className="ml-auto rounded-full bg-muted px-2 py-0.5 text-[10px] font-medium uppercase tracking-wide text-muted-foreground">
          Preview
        </span>
      </div>
      {children}
    </div>
  );
}

function TypingComposer() {
  const text = TEMPLATES[0]!.examplePrompt;
  const reduce = useReducedMotion();
  const [n, setN] = useState(reduce ? text.length : 0);
  useEffect(() => {
    if (reduce) return;
    const iv = setInterval(() => setN((v) => (v >= text.length + 40 ? 0 : v + 1)), 35);
    return () => clearInterval(iv);
  }, [reduce, text.length]);
  return (
    <Frame label="workspace / new workflow">
      <div className="p-6 md:p-8">
        <p className="font-display text-2xl font-medium">What should we automate today?</p>
        <div className="mt-5 min-h-[120px] rounded-xl border border-border-accent bg-highlight/40 p-4 text-[15px] leading-relaxed">
          {displayText(text.slice(0, n))}
          <span className="ml-0.5 inline-block h-4 w-[2px] translate-y-0.5 animate-pulse bg-primary" />
        </div>
        <div className="mt-4 flex items-center justify-between">
          <span className="text-xs text-muted-foreground">
            Plain English. No framework knowledge needed.
          </span>
          <Link
            to="/login"
            
            className="inline-flex items-center gap-1.5 rounded-full bg-primary px-4 py-2 text-sm font-medium text-primary-foreground transition-colors hover:bg-primary-deep"
          >
            <Sparkles className="h-3.5 w-3.5" /> Open workspace
          </Link>
        </div>
      </div>
    </Frame>
  );
}

const FLOW: { kind: NodeKind; label: string; col: number; row: number }[] = [
  { kind: "trigger", label: "Complaint received", col: 0, row: 1 },
  { kind: "agent", label: "Complaint analysis", col: 1, row: 1 },
  { kind: "tool", label: "Customer lookup", col: 2, row: 0 },
  { kind: "tool", label: "Create ticket", col: 2, row: 2 },
  { kind: "condition", label: "Severity router", col: 3, row: 1 },
  { kind: "approval", label: "Manager approval", col: 4, row: 0 },
  { kind: "agent", label: "Response drafting", col: 4, row: 2 },
  { kind: "output", label: "Send response", col: 5, row: 1 },
];

function MiniGraph() {
  return (
    <Frame label="customer-complaint-resolution · draft">
      <div
        tabIndex={0}
        role="region"
        aria-label="Workflow preview"
        className="relative overflow-x-auto bg-canvas bg-grid p-6"
      >
        <div className="grid min-w-[720px] grid-cols-6 grid-rows-3 gap-x-4 gap-y-5">
          {FLOW.map((f, i) => {
            const M = NODE_META[f.kind];
            return (
              <motion.div
                key={f.label}
                initial={{ opacity: 0, scale: 0.9 }}
                whileInView={{ opacity: 1, scale: 1 }}
                viewport={{ once: true }}
                transition={{ delay: 0.15 + i * 0.09, duration: 0.5, ease }}
                style={{ gridColumn: f.col + 1, gridRow: f.row + 1 }}
                className="rounded-xl border border-border bg-background p-2.5 shadow-soft"
              >
                <div
                  className={`mb-1.5 inline-flex h-6 w-6 items-center justify-center rounded-md ${M.tone}`}
                >
                  <M.icon className="h-3.5 w-3.5" />
                </div>
                <p className="text-[11px] font-medium leading-tight">{displayText(f.label)}</p>
                <p className="mt-0.5 text-[10px] text-muted-foreground">{displayText(M.label)}</p>
              </motion.div>
            );
          })}
        </div>
      </div>
    </Frame>
  );
}

function InspectorMock() {
  return (
    <Frame label="agent · complaint analyst">
      <div className="grid md:grid-cols-[1fr_280px]">
        <div className="hidden bg-canvas bg-grid md:block" />
        <div className="border-l border-border p-5">
          <div className="flex gap-1 rounded-lg bg-muted p-1 text-[11px]">
            {["General", "Intelligence", "Tools", "Knowledge", "Safety"].map((t, i) => (
              <span
                key={t}
                className={`flex-1 rounded-md px-1.5 py-1 text-center ${i === 1 ? "bg-background font-medium shadow-soft" : "text-muted-foreground"}`}
              >
                {t}
              </span>
            ))}
          </div>
          <p className="mt-5 text-xs font-medium text-muted-foreground">Model</p>
          {[
            ["Claude Haiku 4.5", "Anthropic", "$", false],
            ["GPT-5", "OpenAI", "$$$", true],
            ["Gemini 2.5 Flash", "Google", "$", false],
          ].map(([m, p, c, sel]) => (
            <div
              key={m as string}
              className={`mt-2 flex items-center justify-between rounded-lg border p-2.5 text-xs ${sel ? "border-primary bg-highlight" : "border-border"}`}
            >
              <div>
                <p className="font-medium">{m}</p>
                <p className="text-muted-foreground">{p}</p>
              </div>
              <span className="font-mono text-muted-foreground">{c}</span>
            </div>
          ))}
          <p className="mt-5 text-xs font-medium text-muted-foreground">Temperature</p>
          <div className="mt-2 h-1.5 rounded-full bg-muted">
            <div className="h-full w-1/3 rounded-full bg-primary" />
          </div>
        </div>
      </div>
    </Frame>
  );
}

function ControlMock() {
  const rows = [
    ["PII redaction", "Organization", "Enforced"],
    ["Model allowlist", "Organization", "3 models"],
    ["Approval on refunds > $500", "Workflow", "Required"],
    ["Monthly token budget", "Workspace", "2.0M"],
    ["Prompt-injection detection", "Agent", "On"],
  ];
  return (
    <Frame label="governance · policies">
      <div className="divide-y divide-border">
        {rows.map(([p, s, v]) => (
          <div key={p} className="flex items-center justify-between px-5 py-3.5 text-sm">
            <div className="flex items-center gap-3">
              <ShieldCheck className="h-4 w-4 text-primary" />
              <span>{p}</span>
            </div>
            <div className="flex items-center gap-4">
              <span className="hidden text-xs text-muted-foreground sm:inline">{s}</span>
              <span className="rounded-full bg-highlight px-2.5 py-0.5 text-xs font-medium text-primary-deep">
                {v}
              </span>
            </div>
          </div>
        ))}
      </div>
    </Frame>
  );
}

function TraceMock() {
  const steps = [
    ["Complaint received", "40ms", "", "ok"],
    ["Complaint analysis", "1.2s", "Claude Haiku 4.5 · 912 tok", "ok"],
    ["Customer lookup", "310ms", "CRM", "ok"],
    ["Severity router", "22ms", "→ critical", "ok"],
    ["Manager approval", "—", "Approved by reviewer", "wait"],
    ["Response drafting", "1.6s", "Claude Sonnet 4.5 · 1,204 tok", "ok"],
  ];
  return (
    <Frame label="run · illustrative trace">
      <div className="p-5">
        <div className="mb-4 flex gap-6 text-xs text-muted-foreground">
          <span className="flex items-center gap-1.5">
            <Clock className="h-3.5 w-3.5" /> 3.4s
          </span>
          <span className="flex items-center gap-1.5">
            <Coins className="h-3.5 w-3.5" /> $0.0131 est.
          </span>
        </div>
        <ol className="relative space-y-3 border-l border-border-accent pl-5">
          {steps.map(([l, t, m, s]) => (
            <li key={l} className="relative text-sm">
              <span
                className={`absolute -left-[25px] top-1 h-2.5 w-2.5 rounded-full ${s === "wait" ? "bg-warning" : "bg-primary"}`}
              />
              <div className="flex justify-between">
                <span className="font-medium">{l}</span>
                <span className="font-mono text-xs text-muted-foreground">{t}</span>
              </div>
              {m && <p className="text-xs text-muted-foreground">{m}</p>}
            </li>
          ))}
        </ol>
      </div>
    </Frame>
  );
}

function MarketMock() {
  const items = [
    ["Workflow template", "Invoice review & approval", "Finance operations", "mk_wf_invoice"],
    ["Agent", "Contract clause reviewer", "Document processing", "mk_ag_contract"],
    ["Guardrail pack", "PII protection pack", "Governance", "mk_gr_pii"],
    ["Workflow template", "Lead research & qualification", "Sales", "mk_wf_lead"],
  ];
  return (
    <div className="grid gap-3 sm:grid-cols-2">
      {items.map(([k, n, c, id]) => (
        <Link
          key={n}
          to="/app/marketplace"
          search={{ asset: id! }}
          className="group block rounded-2xl border border-border bg-background p-5 transition-all hover:-translate-y-0.5 hover:border-border-accent hover:shadow-lift"
        >
          <p className="text-xs font-medium text-primary">{k}</p>
          <p className="mt-3 font-display text-lg font-medium">{n}</p>
          <div className="mt-6 flex items-center justify-between text-xs text-muted-foreground">
            <span>{c}</span>
            <ArrowUpRight className="h-4 w-4 transition-colors group-hover:text-primary" />
          </div>
        </Link>
      ))}
    </div>
  );
}

export default function Landing() {
  return (
    <div className="min-h-screen">
      <Nav />
      <CinematicHero />
      {/* Rollback: replace <CinematicHero /> with the original <Hero /> below. */}

      <div id="how" className="scroll-mt-20" />
      <Chapter
        id="product"
        n="01 — Describe it"
        title="Start with a sentence."
        body="Write the process the way you'd explain it to a new colleague. MESH reads intent, steps, exceptions and approvals."
      >
        <TypingComposer />
      </Chapter>
      <Chapter
        n="02 — Watch it take shape"
        title="A team of agents, drawn for you."
        body="Your description becomes an editable graph of agents, tools, routers and human checkpoints — every step visible, every connection explicit."
        flip
      >
        <MiniGraph />
      </Chapter>
      <Chapter
        n="03 — Make it yours"
        title="Every agent, fully yours."
        body="Choose models, write instructions, attach tools and knowledge. Common settings up front, depth when you need it."
      >
        <InspectorMock />
      </Chapter>
      <Chapter
        id="governance"
        n="04 — Stay in control"
        title="Guardrails that can't be quietly bypassed."
        body="Policies cascade from organization to agent. Approval gates, budgets and permissions are enforced, not suggested."
        flip
      >
        <ControlMock />
      </Chapter>
      <Chapter
        n="05 — Know what happened"
        title="Every decision, traced."
        body="Inspect each run step by step: which model answered, how long it took, what it cost, and where a human stepped in."
      >
        <TraceMock />
      </Chapter>
      <Chapter
        id="marketplace"
        n="06 — Start with an advantage"
        title="A curated library, not a plugin dump."
        body="Install proven agents, workflow templates and guardrail packs. Each becomes a real, editable asset in your workspace."
        flip
      >
        <MarketMock />
      </Chapter>

      <section className="relative overflow-hidden border-t border-border bg-atmosphere">
        <div className="mx-auto max-w-7xl px-6 py-32 text-center">
          <Reveal>
            <h2 className="mx-auto max-w-3xl text-5xl font-semibold leading-[1] md:text-7xl">
              Build your first AI workforce.
            </h2>
            <p className="mx-auto mt-6 max-w-md text-muted-foreground">
              Open the workspace to design a workflow draft. Backend planning and execution will be connected in the next integration phase.
            </p>
            <ul className="mx-auto mt-8 flex max-w-lg flex-wrap justify-center gap-x-6 gap-y-2 text-sm text-muted-foreground">
              {["Visual builder", "Local draft editing", "Approval gates"].map((x) => (
                <li key={x} className="flex items-center gap-1.5">
                  <Check className="h-4 w-4 text-primary" />
                  {x}
                </li>
              ))}
            </ul>
            <Link
              to="/login"
              className="mt-10 inline-flex h-12 items-center gap-2 rounded-full bg-primary px-7 font-medium text-primary-foreground shadow-lift transition-colors hover:bg-primary-deep"
            >
              Launch Workspace <ArrowRight className="h-4 w-4" />
            </Link>
          </Reveal>
        </div>
      </section>
      <footer className="border-t border-border">
        <div className="mx-auto flex max-w-7xl flex-col items-center justify-between gap-4 px-6 py-8 text-sm text-muted-foreground sm:flex-row">
          <Logo />
          <p>
            Workflow design workspace. Backend planning and execution integration is pending.
          </p>
        </div>
      </footer>
    </div>
  );
}
