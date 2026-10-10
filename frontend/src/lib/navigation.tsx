"use client";
import NextLink from "next/link";
import { useParams, usePathname, useRouter, useSearchParams } from "next/navigation";
import { useCallback, useEffect, useState, type ComponentProps, type ReactNode } from "react";

type Destination = { to?: string; params?: Record<string, string>; search?: Record<string, string | undefined> };
export function routeHref({ to = "/", params = {}, search }: Destination) {
  const path = to.replace(/\$(\w+)/g, (_, key: string) => encodeURIComponent(params[key] ?? ""));
  const query = new URLSearchParams();
  for (const [key, value] of Object.entries(search ?? {})) if (value !== undefined) query.set(key, value);
  return path + (query.size ? `?${query}` : "");
}
type LinkProps = Omit<ComponentProps<typeof NextLink>, "href"> & Destination & {
  activeOptions?: { exact?: boolean }; activeProps?: { className?: string };
};
export function Link({ to, params, search, activeOptions, activeProps, className, ...props }: LinkProps) {
  const pathname = usePathname();
  const href = routeHref({ ...(to ? { to } : {}), ...(params ? { params } : {}), ...(search ? { search } : {}) });
  const path = href.split("?")[0]!;
  const active = activeOptions?.exact ? pathname === path : pathname === path || pathname.startsWith(path + "/");
  return <NextLink href={href} className={[className, active ? activeProps?.className : ""].filter(Boolean).join(" ")} aria-current={active ? "page" : undefined} {...props} />;
}
export function useNavigate(_options?: { from?: string }) {
  const router = useRouter();
  const pathname = usePathname();
  return useCallback((destination: Destination) => router.push(routeHref({ ...destination, to: destination.to ?? pathname })), [router, pathname]);
}
export function useRouteSearch(): Record<string, string | undefined> {
  return Object.fromEntries(useSearchParams().entries());
}
export function useRouteParams() { return useParams<{ id: string }>(); }
export function ClientOnly({ children, fallback = null }: { children: ReactNode; fallback?: ReactNode }) {
  const [ready, setReady] = useState(false);
  useEffect(() => setReady(true), []);
  return ready ? children : fallback;
}
