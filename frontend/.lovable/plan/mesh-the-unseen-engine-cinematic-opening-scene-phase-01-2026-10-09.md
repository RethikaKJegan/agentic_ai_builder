# MESH — The Unseen Engine: Cinematic Opening Scene (Phase 01)

Replace only the top of the public landing page with a monumental, white-and-blue 3D scene: a colossal mechanical intelligence engine floating in a luminous architectural space, with the existing headline, buttons and navigation over it. Everything below the hero, and the whole workspace, stays untouched.

## What the visitor will see
- A full-screen 3D world, already visible on load: a central engine made of nested segmented titanium rings, radial spokes, ceramic plates, recessed dark cavities and thin blue energy conduits; detached agent modules floating around it; huge architectural forms fading into blue-white haze; large cropped metal structures passing close to the camera.
- Slow, filmed motion: rings turning independently at different speeds, a very gentle camera push-in, foreground/background parallax, occasional blue pulses through the modules, soft mouse parallax on desktop.
- Hero text (exact copy from the brief): eyebrow, "An entire AI workforce. / One coordinated system.", supporting line, "Launch Workspace" (to /app) and "Explore Interactive Demo" (to /app?demo=complaint), plus a small "AI generation and runs are simulated" notice.
- Refined translucent-white navigation: Product, How it works, Marketplace, Governance, Launch Workspace — same destinations as today.
- Text and buttons appear instantly; the 3D scene fades in once loaded.

## Fallbacks
- Reduced motion: scene renders as a still frame (no animation).
- No WebGL / failure: a generated, locally stored still image of the engine in the same style, so nobody sees a blank area.
- Phones and weaker devices: fewer parts, lower resolution, re-framed composition with the engine above the text.

## Out of scope (later phases)
Activation interaction, scroll-driven seven-scene journey, any change to /app, workflows, simulation, governance, store, global colors/fonts or UI primitives. No publishing.

## Files that will change
- `src/routes/index.tsx` — swap the hero block and nav styling only; keep the six chapters and footer.
- New: `src/features/landing/cinematic/` — `CinematicHero.tsx` (DOM overlay + client-only loader), `EngineScene.tsx` (3D canvas), `engineParts.ts` (procedural geometry), `materials.ts`, `useSceneCapability.ts` (WebGL/mobile/reduced-motion detection).
- New asset: `src/assets/engine-fallback.jpg` (generated still).
- `src/features/landing/HeroNetwork.tsx` — kept unchanged as the rollback reference.
- `package.json` — add `three`, `@react-three/fiber`, `@react-three/drei` (only if needed for environment lighting), `@types/three`.

## Technical details
- Canvas loaded via ClientOnly + React.lazy, matching the workflow builder pattern; no three.js imports on the server.
- Procedural geometry built once with instanced meshes (hundreds of repeated parts in few draw calls); materials are MeshStandard/MeshPhysical in ceramic, brushed titanium, polished silver, frosted glass and blue emissive; fog + gradient background for atmosphere; key/rim/hemisphere lights.
- DPR capped (1.75 desktop, 1.25 mobile); rendering paused when the hero is off-screen (IntersectionObserver) or the tab is hidden; context-loss handler swaps to the still image; full cleanup on unmount.
- Fixed hero height to avoid layout shift; canvas is aria-hidden and pointer-events don't block text or scroll.

## Validation
Typecheck and existing tests; load `/` with no SSR errors; confirm `/app`, the editor, both buttons and anchor links work; screenshots at 1440x900 and phone size, plus reduced-motion and no-WebGL fallback.
