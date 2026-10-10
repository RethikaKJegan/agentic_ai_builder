import { useEffect, useState } from "react";
import { useMesh } from "@/domain/store";
import { useBackend } from "@/api/state";

/** Rehydrates persisted local draft state once on the client. */
export function useMeshHydrated() {
  const [ready, setReady] = useState(false);
  useEffect(() => {
    Promise.resolve(useMesh.persist.rehydrate()).then(() => { setReady(true); void useBackend.getState().initialize(); });
  }, []);
  return ready;
}
