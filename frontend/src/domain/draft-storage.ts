/** Shared drafts remain backwards compatible; each open tab also keeps its own recovery copy. */
const TAB_KEY = "mesh-tab-drafts-v1";
import { BROWSER_SESSION, browserSessionCurrent } from "@/lib/browser-session";
const TAB_SESSION = "mesh-tab-session-v1";
export const draftStorage = {
  getItem(name: string) {
    if (!browserSessionCurrent()) return null;
    if ((sessionStorage.getItem(TAB_SESSION) || "") !== (localStorage.getItem(BROWSER_SESSION) || "")) {
      sessionStorage.removeItem(TAB_KEY);
      sessionStorage.setItem(TAB_SESSION, localStorage.getItem(BROWSER_SESSION) || "");
    }
    const shared = localStorage.getItem(name);
    try {
      const tab = sessionStorage.getItem(TAB_KEY);
      if (tab && (JSON.parse(tab)?.state?.workflows?.length ?? 0) > 0) return tab;
    } catch {
      /* Fall back to the existing shared draft key. */
    }
    return shared;
  },
  setItem(name: string, value: string) {
    if (!browserSessionCurrent()) return;
    let failed = false;
    try {
      sessionStorage.setItem(TAB_SESSION, localStorage.getItem(BROWSER_SESSION) || "");
      sessionStorage.setItem(TAB_KEY, value);
    } catch {
      failed = true;
    }
    try {
      localStorage.setItem(name, value);
    } catch {
      failed = true;
    }
    if (failed) window.dispatchEvent(new Event("mesh-draft-storage-error"));
  },
  removeItem(name: string) {
    localStorage.removeItem(name);
    sessionStorage.removeItem(TAB_KEY);
  },
};
