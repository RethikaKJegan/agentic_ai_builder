Latest hosted backend release: [evidence-reference validation fix](../action-evidence-reference-validation/deployment.md).

Latest backend hotfix: [query-envelope-binding deployment](../query-envelope-binding/deployment.md).

# Hosted query clarification release — 10 November 2026

Deployed to **https://praxi.bellcorpstudio.com/**.

- Release: `query-clarification-20261110-fc82d6cf5e08`.
- Frontend build: `73n0K7eciFUQ8gCNaRgsi`; previous `C038xXGULZ07Dhwu_uq7R`.
- Base commit: `36fc5cee6c7abf19107a1563064c72ffceedfad0` plus the frozen 23-file release manifest, SHA-256 `fc82d6cf5e08ea008ec0b9c4d87741a1237d1892f2be22f5fc27987390ec0465`. No new Git commit is claimed.
- Completed: 2026-11-10T11:59:16.413298+05:30 (India).

Existing systemd rollout restarted three backends, the shared worker and the frontend, switching to the qualified artifact. No nginx/login/service-unit configuration, credential, source business record or shared schema was changed. No destructive migration, database restore, paid model call, email or Sheets write was performed by this release.

Fresh private backups under `.local/query-clarification-deploy-20261110/backups/` contain verified online SQLite copies of all three stores, 53 configuration/credential files, source and the prior frontend, plus nine auxiliary provider files/journals. Each database passed quick_check. Baseline and candidate startup/rollback compatibility were rehearsed with copied stores, network disabled and protected rows preserved. Final gates found no in-flight runs/jobs or active schedules.

Post-release HTTPS checks and six desktop/mobile journeys passed across operator, Simpson and Subway. The actual failed Simpson workflow was reopened on both screen sizes: it now displays its saved clarification and retains the selected account without modifying the old run. Queries requiring a definition stop before reads; actual-write reconciliation and exact-payload email approvals remain enforced. All five services are healthy with zero automatic restarts. History/job counts, encrypted credentials and configuration hashes are preserved.

Application-only rollback:

```
.venv-integrations/bin/python .local/query-clarification-deploy-20261110/rollback.py
```

Restores the previous source files and retained frontend artifact `frontend/.next-before-clarification-20261110`, then restarts existing services. It does not restore databases or journals. No rollback was required.

See [verification.md](verification.md) for exact tests, root cause, included changes and semantic limitations. No successful paid/live-model clarified workflow execution or actual customer statistic is claimed.
