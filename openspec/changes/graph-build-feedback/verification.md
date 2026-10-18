# Verification

- Before correction: live metadata-only rebuild 0.741s, v2 read 0.020s.
- Old deployment reproduced: build button never returned to its ready label after
  new graph revision appeared; browser assertion timed out. See local
  `.local/graph-feedback/pre-deploy-reproduction.log`.
- 124 frontend/domain/proxy tests passed, including three new build success,
  failure and superseded-response scenarios. Corrected a test-only unsupported
  Testing Library `exact` option before the passing final build/type check.
- Production isolated build, TypeScript, scoped ESLint, contracts and generated
  contract drift checks passed. Strict OpenSpec and diff whitespace checks passed.
- 16 desktop/mobile production fixture browser scenarios passed, including short
  build completion without navigation/reload and preserved business selection.
- Deployed frontend-only artifact with 255 retained static assets and rollback at
  `.local/ui-rollbacks/graph-feedback-20261018/.next`. Backend/worker not restarted.
- Public site live build-to-visible-revision/button-ready: desktop Chromium 3.462s;
  mobile Chromium 2.466s; mobile WebKit 2.519s. All retained selection, no page
  errors/missing static chunks/width overflow. Measurements are not guarantees.
- Live checks requested metadata-only graph rebuilds; no business rows changed,
  mappings reviewed, provider calls or workflow executions triggered.
- All three existing services active. Physical iPhone not tested.

Evidence: `.local/graph-feedback-{regressions,final-tests,types,lint,browser,contracts}.log`,
`.local/graph-feedback/build.log`, `.local/graph-feedback/live-build.json` and screenshots.
