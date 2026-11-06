/** A presentation-cache generation, never an authentication credential. */
export const BROWSER_SESSION = "mesh-browser-session-v1";
let observed: string | null | undefined;
export function browserSessionCurrent() {
  if (typeof window === "undefined") return true;
  try {
    const current = localStorage.getItem(BROWSER_SESSION);
    if (observed === undefined) observed = current;
    return observed === current;
  } catch { return false; }
}
export function resetBrowserSession() {
  localStorage.setItem(BROWSER_SESSION, crypto.randomUUID());
  localStorage.removeItem("mesh-local-drafts-v1");
  sessionStorage.clear();
}
