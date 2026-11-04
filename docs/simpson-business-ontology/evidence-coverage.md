# Connected evidence coverage and pre-run validation

Implemented locally. The existing website, services, live knowledge and original Simpson records were not changed by this task. The local frontend build includes the UI integration; the connected dataset is installed only in a private isolated application database.

The supported release covers complaint/inspection comparison, configured warranty assessment and replacement evidence/authorization review. It reuses the five-layer ontology, current source mappings, native reference checks, durable investigation DAGs, specialist CrewAI agents and source permissions. No new agents or operational write tools were added.

## What the audit found

The existing requirement registry provided good scoped gap definitions, but identity, policy applicability, exclusions, technical recommendations and authorization were marked unavailable. Existing scenarios supplied boolean test events rather than connected business records. Planning checked metadata without initial record coverage. The report UI combined optional limitations and decision blockers.

Those existing components remain. New application preparation goes through initial authorized retrieval and deterministic coverage before invoking the graph planner. Historical plans retain their original hashes and semantics; the legacy service-level planning entry remains available for existing integrations, while new HTTP, website jobs and terminal planning use preparation.

## Evidence schemas and reusable providers

`workflow_api/business_coverage.py` defines the versioned task contracts and providers. `workflow_api/schemas/business-evidence-record-v1.json` exports the detailed record schema. Records have stable case/record IDs, kind, revision, observation time, typed data and source/generated provenance with source references.

- Complaint and inspection: existing native-reference/source-mapping providers plus mandatory relevant complaint observations and linked inspection observations.
- Controlled codes/engineers: existing typed catalogue/user lookup; unresolved optional descriptions stay optional.
- Identity: a scoped evidence certificate must match the source complaint, referenced inspection and selected invoice profile; shared serial equality alone is insufficient. In released scenarios the certificate is generated, not verified company identity.
- Invoice: explicit case identity selection and valid dated observations. A combined scenario invoice profile can retain genuine invoice/sale observations from separate source records, but is labeled generated when their association is supplied by the scenario. Original records remain intact. A record labeled source must match one complete native record.
- Policy: selected version, OEM/model scope, effective period, coverage date basis, calendar-month periods, hours limits and named exclusion checks. Scope/expiry can establish a known negative outcome without creating missing evidence.
- Technical disposition: linked inspection, scoped engine, decision, author reference, reason and decision date. Recommendation is separate from confirmed diagnosis.
- Authorization: linked technical decision, scoped engine, recorded decision/roles and valid decision chronology/period. Approved, rejected, expired and revoked outcomes are distinct. This reviews evidence; it grants no company authority.
- Exclusions: exact policy linkage, scoped engine, required checks and supported findings. Confirmed exclusions produce a negative assessment, not an unknown result.

Coverage states are ready, ready with limitations, needs input, insufficient evidence, conflicting evidence and unsupported. A known rejection is complete evidence of a rejected decision. Unknown, invalid or conflicting records cannot become approvals. Required source truncation blocks a conclusion; optional bounded history is informational.

## Connected subset and provenance

The prepared subset uses A-2025-9-070 and I-2026-3-068, selected through bounded authorized reads. The runtime contains no conditions matching these complaint IDs. The preparation tool accepts any cases with the required supported source anchors and usable dated context.

For each source case it creates twelve variants: complete, negative technical decision, rejected authorization, expired policy, missing inspection, conflicting identity, missing exclusions, invalid dates, ambiguous policy, missing authorization, conflicting authorization evidence and confirmed exclusion. Total: 24 connected cases and 72 declared task checks.

Available company complaint, report, symptom, engineer and invoice observations retain original values, IDs and read times. Missing business events and identity associations are separate generated supplemental records. Scenario policy month/hour parameters reuse the pinned supplied-application fallback profile where available; this does not establish that profile's applicability to the actual company case. Effective dates, exclusions and supporting decisions are explicit scenario configuration, never official Simpson policy.

All variants use the same schemas/providers. Source snapshots are verified against owned saved Phase 2 retrieval requests on installation. Altered company observations, unsupported source edges, mismatched provenance, credentials and cross-owner releases are rejected. Invalid-date variants are explicitly generated observations and never overwrite the original invoice dates.

## Release manifest and isolation

`workflow_api/business_environments.py` stores immutable owner/workspace-scoped releases. Dataset IDs derive from content. Manifests pin ontology/hash, source mapping digest, provider schema/executable fingerprint, policy revisions, case IDs, exact supported tasks, expected/actual coverage and limitations. Generated policy parameter provenance is retained in each case's configuration basis.

Preparation fails if a complete variant has an unexpected mandatory gap or if a negative variant differs from its declared expectation. This is a scoped coverage declaration, not population-wide completeness. Older releases remain stored; provider-incompatible releases are not offered as current selectable environments. New versions do not modify old plans or case records.

## Planning and execution

`workflow_api/investigation_coverage.py` prepares initial task coverage, saves a signed preflight receipt, and supplies compact available-evidence references, blockers, optional limitations and outcomes to the existing planner. A selected scenario/version is pinned to the workflow. Objective identifiers must agree with the selected case.

Runtime authorization and source stamps are rechecked. Real evidence is freshly retrieved before dependent analysis and final reporting; old observations are retained separately. Changed observations qualify prior interpretations rather than silently reusing them. Scenario snapshots remain explicitly historical observations; scoped evidence withdrawals are checked separately at runtime and marked in trace metadata. Revoked or conflicting evidence cannot establish a positive decision.

When required assessment evidence is absent, the dependent analysis returns a deterministic coverage result without a model call. Independent comparison and reporting can continue. Existing call/time controls and the user's provider-managed investigation token policy remain unchanged.

## UI

Workflow options now includes Investigation context: company sources or an explicit validated scenario environment, connected case, assessment date, policy selection and Check evidence. Preparation is also enforced by the new planning path even if that button is not clicked. Inputs are never implicitly set to today's date for company evidence.

The workflow shows pre-run coverage. Reports separate workflow execution, decision readiness/known outcomes, mandatory recovery needs and optional limitations. Scenario context is visible, while full provenance and exact source references remain available in technical evidence. No optional symptom/catalogue limitation is presented as a technical workflow failure.

## Exact backend commands

Use a fresh directory. This performs bounded real-source reads, prepares an isolated database, validates the release and runs all 24 scenario workflows with diagnostic offline planning/analysis. It makes no model calls and writes no company/live application records.

```bash
cd /home/raf/agentic-ai-builder
CHECK_ROOT=$(mktemp -d /tmp/simpson-coverage-XXXXXXXX)
CHECK_DIR="$CHECK_ROOT/check"
.venv-integrations/bin/python -B scripts/business_evidence_environment.py prepare \
  --source-database .local/workflows.sqlite3 --directory "$CHECK_DIR" \
  --complaint-id A-2025-9-070 --complaint-id I-2026-3-068
DB="$CHECK_DIR/isolated.sqlite3"
```

List cases/tasks and capture reproducible context IDs:

```bash
.venv-integrations/bin/python -B scripts/business_evidence_environment.py --database "$DB" cases
.venv-integrations/bin/python -B scripts/business_evidence_environment.py tasks
DATASET_ID=$(.venv-integrations/bin/python -c 'import json,sys; print(json.load(open(sys.argv[1]))["dataset_id"])' "$CHECK_DIR/environment.json")
CASE_ID=$(.venv-integrations/bin/python -c 'import json,sys; print(next(c["case_id"] for c in json.load(open(sys.argv[1]))["cases"] if c["variant"]=="complete"))' "$CHECK_DIR/environment.json")
EVIDENCE_CONTEXT=$(.venv-integrations/bin/python -c 'import json,sys; print(json.dumps({"dataset_id":sys.argv[1],"case_id":sys.argv[2]}))' "$DATASET_ID" "$CASE_ID")
```

Inspect coverage, required evidence, detailed records, source mappings and manifest:

```bash
.venv-integrations/bin/python -B scripts/business_evidence_environment.py --database "$DB" coverage --dataset-id "$DATASET_ID" --case-id "$CASE_ID" --task replacement
.venv-integrations/bin/python -B scripts/business_evidence_environment.py --database "$DB" records --dataset-id "$DATASET_ID" --case-id "$CASE_ID"
.venv-integrations/bin/python -B scripts/business_evidence_environment.py --database "$DB" mappings --dataset-id "$DATASET_ID"
.venv-integrations/bin/python -B scripts/business_evidence_environment.py --database "$DB" manifest --dataset-id "$DATASET_ID"
```

Submit the matching first complete case; use its identifier if selecting another case:

```bash
OBJECTIVE='Compare complaint A-2025-9-070 with its inspection, check warranty readiness and review replacement evidence.'
.venv-integrations/bin/python -B scripts/simpson_investigation.py --database "$DB" preflight --objective "$OBJECTIVE" --evidence-context "$EVIDENCE_CONTEXT"
TEST_KEY="coverage-check-$(date +%s)"
.venv-integrations/bin/python -B scripts/simpson_investigation.py --database "$DB" plan \
  --objective "$OBJECTIVE" --evidence-context "$EVIDENCE_CONTEXT" \
  --request-key "$TEST_KEY-plan" --planning-mode offline --analysis-mode offline > "$CHECK_DIR/manual-plan.json"
WORKFLOW_ID=$(.venv-integrations/bin/python -c 'import json,sys; print(json.load(open(sys.argv[1]))["workflow_id"])' "$CHECK_DIR/manual-plan.json")
.venv-integrations/bin/python -B scripts/simpson_investigation.py --database "$DB" requirements --workflow-id "$WORKFLOW_ID"
.venv-integrations/bin/python -B scripts/simpson_investigation.py --database "$DB" graph --workflow-id "$WORKFLOW_ID"
.venv-integrations/bin/python -B scripts/simpson_investigation.py --database "$DB" run --workflow-id "$WORKFLOW_ID" --request-key "$TEST_KEY-run" > "$CHECK_DIR/manual-created.json"
RUN_ID=$(.venv-integrations/bin/python -c 'import json,sys; print(json.load(open(sys.argv[1]))["run_id"])' "$CHECK_DIR/manual-created.json")
.venv-integrations/bin/python -B scripts/simpson_investigation.py --database "$DB" execute --run-id "$RUN_ID"
.venv-integrations/bin/python -B scripts/simpson_investigation.py --database "$DB" report --run-id "$RUN_ID" --section all
```

Use `--section gaps`, `recovery`, `findings`, `resolutions`, `dates` or `associations` for targeted inspection. Complete cases should have zero mandatory gaps; optional bounded-source limitations may remain. Rejected/expired/excluded variants should show known negative outcomes; incomplete/conflicting variants retain their expected requirements.

For company-only preflight, omit `--evidence-context` and add `--credentials-database .local/workflows.sqlite3` to the isolated CLI invocation. Supply `--inputs` with typed assessment date and an actually pinned policy ID when known. This will retain genuine unavailable company facts rather than manufacture them.

An operator can withdraw scenario evidence with `business_evidence_environment.py --database "$DB" revoke --dataset-id ID --record-id ID --reason TEXT`. This changes only the isolated withdrawal registry, never the company record or immutable release.

## Verification and boundaries

See [implementation verification](../../openspec/changes/business-evidence-coverage/verification.md) for file inventory, actual test counts and separate source/scenario acceptance. QA/CAPA/recurrence completeness, operational approvals/dispatch and arbitrary new business tasks are not part of this release. Existing history/recurrence read capabilities remain available with their existing qualifications.

Offline acceptance validates actual backend execution and evidence handling, not paid model reasoning quality. Model-backed planning/CrewAI remain the existing optional configured path. This task performed no new external model evaluation, live deployment or live knowledge/environment import.
