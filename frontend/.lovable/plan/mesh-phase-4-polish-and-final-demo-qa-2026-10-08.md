# MESH — Phase 4: Polish and final demo QA

## What gets built
1. **Phone and tablet layouts**
   - Workflow editor on small screens switches to a step list: tap a step to open its settings in a bottom sheet. The test panel opens full screen.
   - Workspace menu: on phones, a "More" button opens the full list of pages; on tablets the sidebar collapses automatically.
   - Wide tables (Monitoring, Runs, Settings, Governance) become stacked cards on phones.
2. **Keyboard shortcuts**
   - Global: Cmd/Ctrl+K search, G then O/W/A/R/M to jump to pages, ? opens a shortcuts sheet.
   - Editor: Cmd/Ctrl+Z / Shift+Z undo/redo, Delete removes the selected step, Cmd/Ctrl+Enter runs a test, F fits the view, Esc closes panels.
   - The search palette gets the new pages (Approvals, Runs, Monitoring, Governance, Settings) and quick actions (switch role, reset demo).
3. **Visual polish**
   - Consistent page headers, empty states and loading skeletons in place of "Loading workspace…".
   - Subtle page-enter motion that respects reduced-motion settings; visible focus rings; better contrast on muted text.
   - Notifications bell shows pending approvals with a direct link to the inbox.
4. **Guided demo**
   - Optional "Investor demo" checklist on the Overview (generate, edit by prompt, change model, test, approve, publish, view monitoring), ticking off steps as they happen from real app state.
5. **Final QA**
   - Walk the full investor demo in a test browser at desktop and phone sizes, fix anything broken, confirm no console errors and that every simulated item is labelled.

## Technical details
- Mobile editor list mode reuses store data and `AgentInspector`; ReactFlow stays client-only and is not mounted on small screens (`useIsMobile`).
- Shortcut handling in one `useShortcuts` hook in `src/features/shell`, ignoring keystrokes inside inputs.
- Demo checklist progress derived in a pure `src/domain/demoProgress.ts` (from workflows, runs, audit) with tests.
- Skeletons via existing shadcn `skeleton`; motion via `motion` with `useReducedMotion`.
