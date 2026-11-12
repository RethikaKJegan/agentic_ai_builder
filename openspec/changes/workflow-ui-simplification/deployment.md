# Workflow UI deployment — 12 November 2026

Deployed to https://praxi.bellcorpstudio.com/app for Simpson, Subway and the operator workspace.

- Release: `workflow-ui-20261112-8a29d2f2ef9a`.
- Frontend build: `AoUYHmeZ37Ru3lHZPJFBo`.
- Verified at 12:08 PM India time.
- Live API/session/worker checks passed for all three workspace routes.
- Four live desktop/mobile checks passed for Simpson/Subway: single workflow list, Rename/Duplicate/Delete menu entries, workflow-scoped Background automation, and no unrelated knowledge module boxes. No browser errors or horizontal overflow.
- Existing workflow histories, encrypted Google connection records, automation, ontology versions and knowledge packages were preserved. Existing environment/credential configuration files are unchanged. No database restore, workflow submission, paid model call or external provider write was performed for verification.

The four backend/worker services use a separate application source copy under `.local/workflow-ui-release-20261112/app`, selected by persistent `zzzz-workflow-ui-release.conf` systemd overrides. The frontend uses the tested build in `frontend/.next`. Unrelated concurrent evaluator/recovery edits in the development workspace were excluded; the existing provider wrapper gets only the title-forwarding method required by this release.

The initial isolated startup rejected relocated credential/registry/procurement paths. Release-local data-root constants were corrected to the existing protected repository data directory, preserving registry containment and connector symlink checks. All five services subsequently passed readiness with zero automatic restarts after their corrected starts. Application code in the development workspace was not modified for these deployment-path adjustments.

Fresh consistent Simpson/Subway SQLite backups, source hashes, environment copies, a baseline source copy and the previously verified frontend rollback artifact are retained privately. Operator history was checked in place; no new full operator snapshot was made. Actual active work and near-due schedules were checked before restart.

Application-only rollback:

```sh
.venv-integrations/bin/python .local/workflow-ui-release-20261112/deploy.py rollback
```

This switches services to the baseline source copy and restores the retained verified frontend artifact. It never restores databases. Deployment evidence, final source hashes and read-only live screenshots are in `.local/workflow-ui-release-20261112/`.

Refresh the Workflows page to load the new UI. Existing names use short presentation fallbacks; new interpreted requests generate short names before planning. Manual names and original prompts are retained. Live menu actions were inspected without renaming, duplicating or deleting customer workflows; actual mutation behavior was verified in isolated tests before deployment.
