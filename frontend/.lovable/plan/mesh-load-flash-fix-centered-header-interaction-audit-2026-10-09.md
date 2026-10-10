# MESH — Load flash fix, centered header, interaction audit

Scope: landing page fixes plus an audit of every control across `/app`. No redesign, no new libraries, no brand changes, the 3D engine stays.

## 1. Remove the image flash on first load
- Cause: `CinematicHero` shows `engine-fallback.jpg` right away (server-rendered), then a timer fades the 3D canvas in over the top of it, so the photo shows briefly first.
- Fix: delete `StillBackdrop`, its import and the jpg file. Until the scene is ready, show only the existing `bg-atmosphere` gradient (the same on the server and in the browser).
- Fade the canvas in when the scene reports its first rendered frame (an `onFirstFrame` callback fired from a frame hook inside `EngineScene`), not on the 300ms timer.
- If WebGL is missing or the context is lost, keep the gradient. Keep the existing offscreen pause, reduced-motion handling and mobile settings.

## 2. Remove the four nav links
- Remove Product, How it works, Marketplace and Governance, along with the links array. No hamburger menu replaces them. Page sections and the `/app` pages stay.

## 3. New header
- Three-column grid (`1fr auto 1fr`) so the logo sits at the true center of the viewport; Launch Workspace is in the right column.
- Clicking the logo on the landing page scrolls smoothly to the top. The workspace logo keeps its current behavior.
- Scroll state (past about 12px, using a passive listener plus requestAnimationFrame): header height goes from 64px to 56px, the glass background gets more opaque and more blurred, a slow 12s CSS gradient drifts across it (blue → clear → light cyan), and a thin blue line appears along the bottom edge. Transitions are smooth, and reduced motion turns off the drift.
- Logo hover: a soft glow and a slight lift with a spring easing. No spinning.
- Narrow screens (320–390px): the button shows a shorter "Launch" label (still named "Launch Workspace" for screen readers), with tighter padding and no horizontal scrolling.
- Gradient keyframes go into `styles.css` as a utility that uses the existing color tokens.

## 4. Landing-page controls
- "Generate workflow" in the typing preview becomes a real link to `/app?demo=complaint`.
- Marketplace preview cards link to `/app/marketplace?item=<id>`. The marketplace reads `item` to preselect that asset (or the card links to real catalog ids).
- Other illustrations (inspector, policies, trace) get a "Preview" label and lose any clickable-looking hover styling.

## 5. Interaction audit for `/app`
Go through each area in the brief (overview, builder, marketplace, agents/governance, integrations/knowledge, runs/approvals/monitoring/settings, shell). For every control, read the code and confirm it does what it says, then fix:
- buttons that do nothing or go to the wrong page; repeated clicks that submit twice (guard generate, publish and install); success messages shown without a real change
- empty or invalid input on the overview: show an inline error
- the disabled entries in the builder's versions menu become clearly read-only info rows (a version list with labels)
- icon-only buttons with no accessible name; missing focus rings; dropdowns and dialogs that don't close
- any hydration or console warnings found in the browser
All fixes go through the existing store, domain functions and router. Governance checks stay enforced. Simulated features stay labelled as simulated.

## 6. Polish
Make hover, active and focus states, corner rounding and shadows consistent wherever the audit finds gaps. No new loading screens.

## 7. Verification (reported exactly as run)
- TypeScript, build, lint and the existing 46 tests. Add tests for the marketplace `item` preselect and the overview input check.
- Playwright: first-load frames with no image request or flash, header centering measured at 320/375/390/768/1280px, scroll state, every landing link, the main `/app` flows (generate, edit, test, approve, publish, install, pause agent), state after a page refresh, keyboard tab order, reduced motion, console and hydration errors.
- An axe accessibility scan, rerun after the fixes.

## 8. Final report
Files changed, the root cause, header behavior, the list of interactions grouped by area, what is simulated, check results and remaining limitations.

## Technical notes
- Files: `CinematicHero.tsx`, `EngineScene.tsx`, `src/routes/index.tsx`, `src/styles.css`, `src/components/mesh/Logo.tsx` (adds optional onClick/className props), `app.marketplace.tsx`, and whichever `/app` files the audit finds.
- No store schema change, so no data migration is needed.
