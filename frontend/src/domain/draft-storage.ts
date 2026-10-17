/** Shared drafts remain backwards compatible; each open tab also keeps its own recovery copy. */
const TAB_KEY = "mesh-tab-drafts-v1";
export const draftStorage = {
  getItem(name: string) {
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
    let failed = false;
    try {
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
