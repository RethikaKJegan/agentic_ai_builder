import { motion, useReducedMotion } from "motion/react";
import { useEffect, useState } from "react";

// Abstract agents drift independently, then resolve into a coordinated workflow graph.
const NODES = [
  { id: "t", graph: [120, 300], scatter: [180, 120] },
  { id: "a", graph: [300, 300], scatter: [520, 90] },
  { id: "l", graph: [480, 210], scatter: [860, 160] },
  { id: "k", graph: [480, 390], scatter: [300, 480] },
  { id: "r", graph: [660, 300], scatter: [1060, 420] },
  { id: "h", graph: [840, 200], scatter: [700, 520] },
  { id: "w", graph: [840, 400], scatter: [1140, 110] },
  { id: "o", graph: [1020, 300], scatter: [90, 460] },
] as const;
const EDGES: [string, string][] = [
  ["t", "a"],
  ["a", "l"],
  ["a", "k"],
  ["l", "r"],
  ["k", "r"],
  ["r", "h"],
  ["r", "w"],
  ["h", "o"],
  ["w", "o"],
];
const pos = (id: string) => NODES.find((n) => n.id === id)!.graph;

export function HeroNetwork() {
  const reduce = useReducedMotion();
  const [formed, setFormed] = useState(true);
  useEffect(() => {
    if (reduce) return;
    const first = setTimeout(() => setFormed(false), 4200);
    const iv = setInterval(() => setFormed((f) => !f), 5200);
    return () => {
      clearTimeout(first);
      clearInterval(iv);
    };
  }, [reduce]);

  return (
    <svg
      viewBox="0 0 1140 600"
      className="h-full w-full"
      preserveAspectRatio="xMidYMid slice"
      aria-hidden
    >
      <defs>
        <radialGradient id="node-glow">
          <stop offset="0%" stopColor="var(--primary)" stopOpacity="0.25" />
          <stop offset="100%" stopColor="var(--primary)" stopOpacity="0" />
        </radialGradient>
      </defs>
      {EDGES.map(([a, b], i) => {
        const [x1, y1] = pos(a);
        const [x2, y2] = pos(b);
        const mx = (x1 + x2) / 2;
        const d = `M${x1},${y1} C${mx},${y1} ${mx},${y2} ${x2},${y2}`;
        return (
          <g key={`${a}${b}`}>
            <motion.path
              d={d}
              fill="none"
              stroke="var(--sky)"
              strokeWidth={1.2}
              initial={{ pathLength: 0, opacity: 0 }}
              animate={{ pathLength: formed ? 1 : 0, opacity: formed ? 0.7 : 0 }}
              transition={{
                duration: 0.9,
                delay: formed ? 0.5 + i * 0.07 : 0,
                ease: [0.22, 1, 0.36, 1],
              }}
            />
            {formed && !reduce && (
              <circle r={2.6} fill="var(--primary)">
                <animateMotion
                  dur={`${2.4 + (i % 3) * 0.5}s`}
                  repeatCount="indefinite"
                  path={d}
                  begin={`${1.2 + i * 0.15}s`}
                />
              </circle>
            )}
          </g>
        );
      })}
      {NODES.map((n, i) => {
        const [x, y] = formed ? n.graph : n.scatter;
        return (
          <motion.g
            key={n.id}
            initial={false}
            animate={{ x, y }}
            transition={{ type: "spring", stiffness: 40, damping: 14, delay: i * 0.04 }}
          >
            <circle r={44} fill="url(#node-glow)" />
            <rect
              x={-30}
              y={-18}
              width={60}
              height={36}
              rx={10}
              fill="var(--background)"
              stroke={i === 4 ? "var(--primary)" : "var(--border-accent)"}
              strokeWidth={1.2}
            />
            <circle
              cx={-14}
              cy={0}
              r={5}
              fill={i === 0 ? "var(--foreground)" : i === 5 ? "var(--warning)" : "var(--primary)"}
            />
            <rect
              x={-4}
              y={-4}
              width={22}
              height={3}
              rx={1.5}
              fill="var(--foreground)"
              opacity={0.7}
            />
            <rect
              x={-4}
              y={3}
              width={14}
              height={3}
              rx={1.5}
              fill="var(--muted-foreground)"
              opacity={0.5}
            />
          </motion.g>
        );
      })}
    </svg>
  );
}
