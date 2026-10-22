import { ClientOnly, Link } from "@/lib/navigation";
import { motion } from "motion/react";
import { lazy, Suspense, useEffect, useRef, useState } from "react";
import { ArrowRight } from "lucide-react";
import { useSceneCapability } from "./useSceneCapability";

const EngineScene = lazy(() => import("./EngineScene"));
const ease = [0.22, 1, 0.36, 1] as const;

function SceneLayer() {
  const cap = useSceneCapability();
  const ref = useRef<HTMLDivElement>(null);
  const [active, setActive] = useState(true);
  const [lost, setLost] = useState(false);
  const [shown, setShown] = useState(false);

  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    const io = new IntersectionObserver(([e]) =>
      setActive(!!e?.isIntersecting && !document.hidden),
    );
    io.observe(el);
    const vis = () => setActive(!document.hidden);
    document.addEventListener("visibilitychange", vis);
    return () => {
      io.disconnect();
      document.removeEventListener("visibilitychange", vis);
    };
  }, []);

  const use3D = cap.ready && cap.webgl && !lost;
  return (
    <div ref={ref} className="absolute inset-0">
      {use3D && (
        <Suspense fallback={null}>
          <div
            className={`absolute inset-0 transition-opacity duration-[1500ms] ${shown ? "opacity-100" : "opacity-0"}`}
          >
            <EngineScene
              mobile={cap.mobile}
              animate={!cap.reducedMotion}
              active={active}
              onContextLost={() => setLost(true)}
              onFirstFrame={() => setShown(true)}
            />
          </div>
        </Suspense>
      )}
    </div>
  );
}

export function CinematicHero() {
  return (
    <section className="relative h-[100svh] min-h-[640px] overflow-hidden bg-atmosphere">
      <div className="pointer-events-none absolute inset-0" aria-hidden>
        <ClientOnly fallback={null}>
          <SceneLayer />
        </ClientOnly>
        {/* legibility veils */}
        <div className="absolute inset-0 bg-gradient-to-r from-background/90 via-background/45 to-transparent max-md:bg-gradient-to-t max-md:from-background max-md:via-background/85 max-md:to-transparent" />
        <div className="absolute inset-x-0 bottom-0 h-40 bg-gradient-to-b from-transparent to-background" />
      </div>

      <div className="relative mx-auto flex h-full w-full max-w-7xl items-center px-6 pt-16 max-md:items-end max-md:pb-12">
        <div className="max-w-xl lg:max-w-[38rem]">
          <motion.p
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ duration: 0.8 }}
            className="font-mono text-[11px] font-medium uppercase tracking-[0.22em] text-primary-deep"
          >
            PraxilonAI / The agentic AI operating system
          </motion.p>
          <motion.h1
            initial={{ opacity: 0, y: 24 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 1.1, ease }}
            className="mt-6 text-[44px] font-semibold leading-[0.98] tracking-tight sm:text-6xl xl:text-[68px]"
          >
            An entire AI workforce.
            <span className="block text-primary">One coordinated system.</span>
          </motion.h1>
          <motion.p
            initial={{ opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.9, delay: 0.2, ease }}
            className="mt-6 max-w-lg text-lg leading-relaxed text-foreground/75"
          >
            Design intelligent workflows, coordinate specialized agents, and keep every decision
            visible — from one visual workspace.
          </motion.p>
          <motion.div
            initial={{ opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.9, delay: 0.35, ease }}
            className="mt-9 flex flex-wrap gap-3"
          >
            <Link
              to="/app"
              className="group inline-flex h-12 items-center gap-2 rounded-full bg-primary px-6 font-medium text-primary-foreground shadow-lift transition-colors hover:bg-primary-deep"
            >
              Launch Workspace{" "}
              <ArrowRight className="h-4 w-4 transition-transform group-hover:translate-x-0.5" />
            </Link>
          </motion.div>
          <p className="mt-6 text-xs text-muted-foreground">
            Design drafts now. Backend planning and execution integration is pending.
          </p>
        </div>
      </div>
    </section>
  );
}
