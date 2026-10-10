import { useEffect, useState } from "react";

export type SceneCapability = {
  ready: boolean;
  webgl: boolean;
  mobile: boolean;
  reducedMotion: boolean;
};

/** Detects WebGL support, small screens and reduced-motion preference (client only). */
export function useSceneCapability(): SceneCapability {
  const [cap, setCap] = useState<SceneCapability>({
    ready: false,
    webgl: false,
    mobile: false,
    reducedMotion: false,
  });
  useEffect(() => {
    let webgl = false;
    try {
      const c = document.createElement("canvas");
      webgl = !!(c.getContext("webgl2") || c.getContext("webgl"));
    } catch {
      webgl = false;
    }
    const mobile =
      window.matchMedia("(max-width: 767px)").matches || (navigator.hardwareConcurrency ?? 8) <= 4;
    const reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    setCap({ ready: true, webgl, mobile, reducedMotion });
  }, []);
  return cap;
}
