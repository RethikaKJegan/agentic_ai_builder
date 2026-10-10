const AUTO: Record<string, "success" | "warning" | "danger" | "info" | "neutral"> = {
  completed: "success",
  success: "success",
  approved: "success",
  paused: "warning",
  paused_for_approval: "warning",
  queued: "info",
  cancelled: "neutral",
  timed_out: "danger",
  running: "info",
  failed: "danger",
  rejected: "danger",
  blocked: "danger",
};

const TONES = {
  success: "bg-success/10 text-success",
  warning: "bg-warning/15 text-warning",
  danger: "bg-destructive/10 text-destructive",
  info: "bg-highlight text-primary-deep",
  neutral: "bg-muted text-muted-foreground",
};

export function StatusPill({ status, tone }: { status: string; tone?: keyof typeof TONES }) {
  const t = tone ?? AUTO[status] ?? "neutral";
  return <span className={`inline-flex shrink-0 items-center gap-1.5 rounded-full px-2 py-0.5 text-xs font-medium capitalize ${TONES[t]}`}><span className="h-1.5 w-1.5 rounded-full bg-current" />{status}</span>;
}
