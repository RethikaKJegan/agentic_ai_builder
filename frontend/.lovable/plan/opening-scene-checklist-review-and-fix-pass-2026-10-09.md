# Opening Scene — Checklist Review and Fix Pass

## Honest status against your checklist

| Criterion | Status | Why |
|---|---|---|
| Engine has genuine 3D mechanical depth | Partial | Real 3D, but seen almost face-on; rings read as flat concentric circles with box-shaped bits. |
| White and blue dominate without looking flat | Partial | Colours are right, but lighting is even, few shadows, almost no reflections. |
| Foreground / midground / background show enormous scale | Not met | Background pillars and haze are faint; the foreground arc is barely visible; a large grey disc at the bottom reads as an error. |
| Cinematic in a still frame | Not met | Looks like a clean 3D render, not a film still — no depth haze, light glow or vignette. |
| Typography, nav, both buttons readable and working | Met | Verified; demo button opens the demo. Nav button text says "Launch workspace" (lower-case w) vs brief "Launch Workspace". |
| Desktop and mobile both work | Partial | Desktop fine. On phones the engine sits behind the eyebrow and headline, hurting readability. |
| Workspace unaffected | Met (by design) | No workspace files changed; not re-clicked after the change. |
| Build, tests, accessibility reported accurately | Partial | Typecheck and tests passed; no accessibility check (keyboard, contrast, screen reader) was run. |

## Fix pass

1. **Depth and construction** — turn the engine to a three-quarter angle; give rings real thickness with bevelled plates, inner cavity walls and side flanges; replace random boxes with ordered sub-assemblies (bolts, vents, clamps, cable runs).
2. **Lighting and materials** — add soft studio-style reflections so metal shines, a stronger blue rim light, and soft shadows on the core; add a gentle bloom on blue lines only.
3. **Scale layers** — bring a large, sharp, cropped ceramic structure into the lower-left foreground; add rows of colossal background pillars and bridges fading into haze; remove the grey disc and replace with a faint distant platform.
4. **Cinematic finish** — depth haze, a soft light shaft behind the engine, light vignette and fine film grain; tune exposure so whites keep detail.
5. **Mobile** — move the engine into the top 45% of the screen above the text and soften it behind the text.
6. **Copy consistency** — nav button reads "Launch Workspace".
7. **Verification, reported plainly** — typecheck and tests; screenshots at 1440x900 and 390x844 plus a reduced-motion still; open /app and a workflow editor; click every nav link and both buttons; keyboard tab-through with visible focus; automated accessibility scan (axe) on the landing page; contrast check on hero text over the scene.

Only the landing scene files and the nav button text change.

## Technical details
- Add `@react-three/postprocessing` (Bloom, Vignette, Noise; skipped on mobile and reduced motion) and `@react-three/drei` for a local `Environment` with `Lightformer`s (no remote HDR).
- Ring plates via `ExtrudeGeometry` with bevel, still instanced; greebles grouped into deterministic patterns per segment.
- Accessibility scan via `@axe-core/playwright` run from /tmp only (not added to the project).
