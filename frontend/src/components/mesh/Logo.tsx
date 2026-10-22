import { Link } from "@/lib/navigation";

export function LogoMark({ className = "h-6 w-6" }: { className?: string }) {
  return (
    <svg viewBox="0 0 32 32" className={className} aria-hidden>
      <rect width="32" height="32" rx="8" className="fill-foreground" />
      <circle cx="10" cy="11" r="2.6" className="fill-sky" />
      <circle cx="22" cy="11" r="2.6" className="fill-background" />
      <circle cx="16" cy="22" r="2.6" className="fill-primary" />
      <path d="M10 11 L22 11 L16 22 Z" fill="none" strokeWidth="1.4" className="stroke-background/60" />
    </svg>
  );
}

export function Logo({ to = "/" as "/" | "/app" }) {
  return (
    <Link to={to} className="flex items-center gap-2" aria-label="PraxilonAI home">
      <LogoMark />
      <span className="font-display text-[17px] font-semibold tracking-tight">PraxilonAI</span>
    </Link>
  );
}
