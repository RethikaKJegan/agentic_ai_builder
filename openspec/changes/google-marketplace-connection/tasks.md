- [x] Update Marketplace and simplify Integrations.
- [x] Verify frontend checks and desktop/mobile navigation and account setup.
- [x] Deploy and check frontend readiness.

Marketplace now lists Google instead of Slack/HubSpot and routes the card and
Connect Google links to Integrations. The generic provider grid/setup instructions
were removed, while existing account/OAuth/service selection, collapsed tool
checks and database summary remain. No backend tools, credentials or workflows
were removed or changed.

30 focused tests, TypeScript, ESLint, production build, strict scoped OpenSpec and
diff checks passed. Desktop/mobile browser checks passed on the isolated production
build and deployed frontend: Google navigation, absence of provider cards, opening
the account permission dialog, selecting all seven existing service permissions,
Continue to Google control, no page errors and no horizontal overflow. OAuth
authorization was not started; no credentials or account grants were changed.

Full suite initially had 293 passing and seven failing tests. The affected stale
integration-card test was updated and passes. The other six failures in workflow
journey/release and graph-feedback tests were reproduced on an isolated unchanged
HEAD baseline (six failed, ten passed); they are outside this UI change.

Deployed staged production .next with previous build retained under
.local/ui-rollbacks/google-marketplace-before/.next. Frontend service active and
both deployed desktop/mobile browser checks passed.
