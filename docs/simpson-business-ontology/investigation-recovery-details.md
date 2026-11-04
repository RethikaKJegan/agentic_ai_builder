# Investigation recovery, report cross-check and workflow details

## Confirmed observations

The supplied simple-report facts match saved mapped evidence for A-2022-12-013:
reported serial S325M79495, five operating hours, symptom identifier UC05, CLOSED
ticket, PUBLISHED report, inspection date 2025-03-11 and recorded defect text
`F.I.P Found Faulty`. The raw failure date `13-06-29` fails the pinned conversion;
no date was guessed. All persisted finding reference pairs were revalidated against
their supplied packets. This checks reference validity and key values, not an
independent engineering diagnosis. Inspection publication, physical identity,
policy applicability and commercial authorization remain qualified.

The previous UI could count one record twice when separate reads supplied different
mapped fields. Compatible source-qualified records now merge those fields for
presentation. Different sources and conflicting values are not silently merged.
The inspected simple run contains 23 unique record identifiers; earlier displays
of 24 were not proof of 24 distinct records.

The hard prompt had two failed runs: `run_49e1cfc39d2b41e78f00c5f6fc82acd0` and
`run_f4f27a616dba4d1096631a0d3805df3d`. The latter replacement specialist failed
before source dispatch after approximately 3.2 seconds. Historical handling stored
only INVOCATION_FAILED and discarded the underlying exception. Worker logs also
contained database-transaction failures without their category, so the precise
historical exception cannot be recovered or asserted conclusively.

## Corrections

A deterministic contention test reproduces a concrete fault in that path: tool
discovery requested a SQLite writer lock even though it only read current grants,
revision and tool metadata. Holding another writer made the old path fail. Tool
discovery and other read-only delegation checks now use read transactions; the
same controlled test succeeds while the writer remains held. Actual state changes
still acquire write transactions and recheck revision/authority. No provider call
or external operation was moved inside a transaction, and no source/permission
check was removed. Busy timeouts remain finite.

Storage contention now retains DATABASE_BUSY through existing wrappers; its
recovery category is storage_contention, separate from missing business evidence.
An uncertain write still requires reconciliation. Unknown failures are described
as internal service failures requiring inspection, rather than automatically
blaming ontology/evidence. Node failure events include safe exception class/stage,
and database logs retain category/code/write mode. Raw SQL, exception messages,
provider output, credentials and source contents are not added to diagnostics.

Workflow details now contains the question, existing investigation context,
selected Google account and optional connected-tool fields. Changes prepare a
new immutable workflow and require normal validation/approval. Saved account,
package and action resource settings are restored when opening the panel.
The main canvas no longer carries the full question. Run, report, recovery,
cancel and refresh actions share the same wrapping toolbar.

Read-tool receipts expose actual bounded return counts and message/event
identifiers for verification; they do not expose mailbox bodies or pagination
cursors. A zero-match search is a valid observed result.

## Feedback behavior

Existing pure-model structured-output correction remains bounded and budgeted.
A new run may use sanitized model-output diagnostics from the latest failed run of
the exact same approved revision, owner and workspace. Only relevant task/code/hint
metadata is supplied, separately from source evidence and validated experience.
Prior raw model output is never replayed as evidence. A new run still rereads
current sources and checks current permissions. Infrastructure failures use
infrastructure recovery; the LLM cannot fix a database lock by changing facts.

This does not automatically patch code, invent policies, publish ontology changes,
change model weights, grant tools, bypass approvals or replay uncertain writes.
No automatic new run is triggered. Unsupported goals and real missing evidence
remain visible; no universal promise of failure-free execution is made.

## Tool test in the UI

Open Workflow options for a new request, or Workflow details for an existing one.
Choose the intended Google account. Select **Mail Search** as the optional connected
action, enter query `A-2022-12-013` and limit `5`, and choose the registered authorized
destination if required. Then use:

```text
Retrieve complaint A-2022-12-013 and compare its linked inspection. Search Gmail
using the selected Google account and supplied query A-2022-12-013. Prepare a
source-backed complaint comparison and show the mail-search tool receipt with
the actual matching message identifiers and number returned. If no messages
match, say so. Do not send or draft email, schedule events, update spreadsheets
or modify records.
```

Generate, review, validate, approve and run the new plan. Inspect the mail-search
node's Connected tool results / Tool response receipt, the selected account, and
its actual returned count. Search returns identifiers; fetching message bodies
requires a separate explicit read operation. This is a read-only test, not proof
that sending, drafting, Calendar or Sheets writes work.

## Validation and deployment

See `openspec/changes/investigation-recovery-details/verification.md` for actual
counts, configured-model acceptance, deployment receipt and remaining limits.
The full configured-provider check is available with explicit approval for the
selected mapped evidence:

```bash
.venv-integrations/bin/python -B scripts/check_dynamic_investigation.py \
  --database .local/workflows.sqlite3 --live-model --include-related-evidence
```

It uses a private application/registry copy, four bounded business read adapters,
no Google actions, no arbitrary attachments, no company writes and provider
response storage disabled. This run requires authorization for replacement as
well as complaint, inspection and warranty-readiness evidence.
