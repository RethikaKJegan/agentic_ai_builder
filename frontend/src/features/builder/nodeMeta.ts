import { Bot, CheckCircle2, GitBranch, Send, ShieldCheck, Wand2, Wrench, Zap, type LucideIcon } from "lucide-react";
import type { NodeKind } from "@/domain/types";

export const NODE_META: Record<NodeKind, { label: string; icon: LucideIcon; tone: string }> = {
  trigger: { label: "Trigger", icon: Zap, tone: "bg-foreground text-background" },
  agent: { label: "AI Agent", icon: Bot, tone: "bg-primary text-primary-foreground" },
  tool: { label: "Tool", icon: Wrench, tone: "bg-highlight text-primary-deep" },
  condition: { label: "Router", icon: GitBranch, tone: "bg-highlight text-primary-deep" },
  approval: { label: "Human approval", icon: ShieldCheck, tone: "bg-warning/15 text-warning" },
  transform: { label: "Transform", icon: Wand2, tone: "bg-muted text-muted-foreground" },
  output: { label: "Output", icon: Send, tone: "bg-success/15 text-success" },
};

export const DONE_ICON = CheckCircle2;
