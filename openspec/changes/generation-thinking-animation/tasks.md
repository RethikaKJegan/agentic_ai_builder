- [x] Replace the visible busy label with an accessible thinking animation.
- [x] Verify desktop/mobile busy and idle states and deploy the frontend.

Evidence: only app.index.tsx changed in application code. Four existing generation/source tests, production build, types, lint, strict OpenSpec and diff checks passed. Desktop/mobile browser checks used mocked planning jobs (no live model calls) to verify three dots, disabled/busy state, reduced-motion behavior and cancellation restoring the retry button. Frontend deployed with rollback build retained; backend unchanged.
