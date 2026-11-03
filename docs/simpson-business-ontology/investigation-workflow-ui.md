# Investigation workflow UI

Deployed on 3 November 2026 at https://praxi.bellcorpstudio.com/app using the existing workspace login. Frontend build: `ZOf2NBddrsZM1RGAcDDhL`.

## Try it

In **Overview**, paste:

```text
Investigate complaint A-2022-12-013, compare its linked inspection,
check warranty readiness and prepare a source-backed report identifying
discrepancies and missing evidence.
```

1. Click **Generate workflow**. This saves and validates the model-planned graph; it does not execute it.
2. Click **Run investigation**. The worker reads bounded mapped records and runs the supported CrewAI analysis nodes.
3. Click a node, or use **Steps**, to inspect actual status, observations and analysis. Selected connections are blue; skipped branches are muted. Completed nodes with explicit evidence gaps are amber.
4. Click **View report** for observations, interpretations, readiness and missing information. Source buttons open supporting records.
5. Click **Ontology evidence** for the concepts, relationships, rules and source groups used. Exact version, hashes and mappings remain inside collapsed **Technical details**.

**Fit workflow** shows the entire graph; **Readable view** zooms into the beginning, then you can pan. The Steps list also works on phones. Saved investigations appear in Overview and Workflows. Reloading their URL recovers the saved plan/run/job without submitting model work.

Supported prompts route automatically. **Workflow options → Workflow type** explicitly selects investigation or the existing general automation builder. Supported capabilities include complaint/history retrieval, linked inspection comparison, warranty readiness and replacement evidence. Graphs depend on requested capabilities and backend validation. Arbitrary prompts cannot add unsupported operations.

## Input, failures and reports

Missing identifiers accept an exact complaint ID or engine serial and queue an explicit resume. A configured evidence-gap checkpoint accepts acknowledgment without treating notes as verified facts.

**Resume eligible work** is offered for retryable failures within their attempt budget, or interrupted work subject to server lease recovery. Other failed runs offer **Start new run**: this creates separate run history under the saved plan and can incur fresh reads/model usage. **Cancel run** prevents later dispatch; incurred model usage cannot be undone. There is no automatic paid replay of interrupted jobs.

**Investigation completed — additional evidence required** means the workflow finished with unresolved business facts. It does not approve coverage, verify physical engine identity or authorize replacement.

## Backend integration and storage

ReactFlow/dagre renders the saved domain DAG directly. It remains separate from the canonical general workflow release/approval contracts and cannot dispatch general connectors.

New routes, relative to `/business-ontology/v1/investigations`:

| Operation | Route |
| --- | --- |
| List saved plans, latest runs and recent jobs | `GET /` |
| Queue planning, execution or resume | `POST /jobs` |
| Read job status | `GET /jobs/{job_id}` |

Jobs require an explicit idempotency key, kind and typed payload. Website planning uses the configured model and CrewAI. Current authority is resolved before dispatch; there is no silent offline-result substitution. The UI polls persisted state about every 1.5 seconds while work is active, avoiding long browser model requests.

Jobs use `business_investigation_jobs`; plans/runs use `business_investigation_plans` and `business_investigation_runs` in the existing application SQLite database. WorkerSupervisor hosts InvestigationJobs in the existing worker service. Standalone development startup/shutdown also manages it when planning workers are enabled. Evidence persists under existing storage/backup controls; this change adds no automatic retention deletion or public sharing.

The live knowledge package was explicitly imported as revision 7, retaining revisions 1–6. Authoring remains in `ontology/business-reference/`, including `knowledge-pack.json` and `configured-rules.json`. File edits require an explicit validated versioned import; saved runs are not silently altered.

## Verification and recovery

The real HTTPS test generated 18 nodes and two conditions. Its successful run read two unique source records across four scoped observations, performed three CrewAI analyses and produced 25 validated findings. It completed with evidence gaps. Normal login, unauthenticated API rejection, node records, report source links, evidence drawer, refresh recovery and desktop/mobile rendering were checked on the deployed website.

An initial real analysis correctly failed on an unsupported source citation. Analysis now receives an explicit legal citation catalog and output schema bound to supplied record/mapping pairs. Invalid output remains rejected; no citation substitution, silent retry or fallback report was added. The failed run is preserved. Successful acceptance used **Start new run**.

Private backup, code/configuration copies, old frontend artifacts, import receipts and browser evidence are in `.local/investigation-ui-rollout-20261103/`. Keep this directory private. `live-previous.next` is the pre-rollout frontend; `initial-release.next` is the first UI release before the citation/recovery improvement.

For frontend rollback, stop only `agentic-builder-frontend`, move the current build aside, restore the selected saved `.next` artifact and start that service. Retain prior static assets for open browsers. Backend changes are additive: preserve live knowledge and run history. Do not overwrite subsequent work with the older database backup. Recheck active work before backend/worker restarts. Existing credentials, login configuration and Nginx are unchanged; company data remains read-only.
