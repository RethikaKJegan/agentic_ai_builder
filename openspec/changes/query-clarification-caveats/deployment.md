Latest hosted runtime release: [grouped query fix](../grouped-query-model-output/deployment.md).

# Hosted query-clarification guidance — 10 November 2026

Deployed to **https://praxi.bellcorpstudio.com/**.

- Release: `query-caveat-20261110-8d3e06ad4b7d`.
- Source manifest SHA-256: `8d3e06ad4b7d4661c4687176a99416e5469f43c0c012f9b6fda3c9514ba6f848`.
- Base commit: `36fc5cee6c7abf19107a1563064c72ffceedfad0` plus existing recorded changes and this one-file runtime update.
- Frontend artifact retained: `73n0K7eciFUQ8gCNaRgsi`.
- Completed: 2026-11-10T13:08:43.923855+05:30 (India time).

The generic query agent now receives trusted guidance to distinguish metadata caveats from missing business meaning. Plain dataset counts need no field/unit definition; engine execution establishes actual coverage. Genuine nonempty clarification remains a stop guard. No saved blocked execution was rewritten or automatically retried.

82 controlled regression tests and 18 subtests passed. Six isolated baseline/candidate startup checks, fresh verified backups, authenticated public API checks, six desktop/mobile read-only browser journeys and data/credential preservation checks passed. The existing backend/worker systemd rollout was used. No frontend build switch, destructive migration, database restore, credential change, paid model call or real external tool action occurred. All services remain healthy with zero automatic restarts.

A transient SQLite-lock health failure occurred before activation; deployment waited for successful all-account rechecks and zero active runs. No database repair was attempted, and permanent contention resolution is not claimed. Live-model interpretation and live population execution remain unqualified; see [verification](verification.md). Historical shared-store audit and business semantic limitations remain separate.

Application-only rollback:

```sh
.venv-integrations/bin/python .local/query-caveat-deploy-20261110/rollback.py
```

It restores the previous runtime/crew.py and restarts backend/worker services, without restoring databases, journals or frontend artifacts. The previous source was rehearsed against copied stores. No rollback was required. Private evidence and backups are in `.local/query-caveat-deploy-20261110/`.
