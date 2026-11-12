# Subway example definitions and manual acceptance

These are generated restaurant procurement/finance assumptions requested by the
user, following Simpsons' separation of scenario assumptions and company facts.
They are not an official Subway policy or a copy of Simpsons manufacturing rules.
The profile is `ontology/subway/demo-business-definitions-v1.json`.

Select **Subway**. Start a new workflow for each prompt. The exact phrase
`Use Subway demo definitions v1` selects the profile; ordinary prompts and old
workflows keep their existing behavior. Explicit definitions in a prompt take
precedence over the profile defaults. Test the latest released application: local
source/test success does not establish that a running hosted process has loaded it.

## Example definitions

| Term | Example interpretation |
| --- | --- |
| Spending | Recorded PO `totalAmount`, grouped by stored currency, labelled recorded PO value; all raw statuses unless explicitly filtered |
| Restaurant / outlet | Central store record; finance sites keep separate identities |
| Supplier | Recorded PO vendor reference/label; link central vendors only through a declared supported relationship |
| Available budget | Stored line-item `availableAmount` at snapshot read time |
| Pending approval | Exact raw `PENDING` status on the requested approval collection; explicitly a demo filter |
| Invoice difference | Comparable invoice amount minus linked PO amount; arithmetic review finding, not fraud or overbilling policy |
| Missing receipt | Receipt evidence not established, not proof of non-delivery |
| Performance | Actual/AOP/UEM observations remain separate until compatible period, measure, location and currency are established |

No assumed policy can supply missing record values, source currency, store/site
identity, historical balances, current coverage, attachment contents or live events.
Example assumptions are stored separately from ontology evidence references and
do not become query grants, verified observations or executable policies.

## Business prompts

Run 1–8 without external actions first. Review both results and the Knowledge Map.

1. **PO baseline**

   > Use Subway demo definitions v1. Count all purchase orders in the available snapshot and break them down by their raw recorded status. Show query coverage and the source limitations. No external actions.

   Pass: complete-source counts, status groups reconcile with the total, no invented current-period claim.

2. **Default spending**

   > Use Subway demo definitions v1. Summarize spending in the available snapshot by currency and purchase-order status. State exactly what spending means here. No external actions.

   Pass: recorded PO value labelled as an example definition; no mixed-currency grand total, approved-commitment or cash-payment claim.

3. **Explicit override**

   > Use Subway demo definitions v1. For this request spending means recorded invoice amounts, not purchase-order value. Count invoice records and summarize their amounts separately by recorded currency. No external actions.

   Pass: invoice measure overrides PO default. Missing amounts/currencies remain explicit; no substituted PO measure.

4. **Supplier concentration**

   > Use Subway demo definitions v1. Rank the top ten recorded purchase-order vendors by recorded PO value separately for each currency. Include order counts and missing-vendor coverage. Use only supported vendor relationships. No external actions.

   Pass: ranks use complete relevant records, labels/identities are qualified, no guessed central-vendor mapping. If multiple queries are needed, preserve their individual receipts and scope.

5. **Approval backlog**

   > Use Subway demo definitions v1. Count approval records with exact raw status PENDING and show the counts of all other stored statuses for comparison. Explain that this is the demo pending definition, not an official approval policy. No external actions.

   Pass: exact status filtering, raw status coverage, zero matches allowed. No invented equivalence between stages and parent approvals.

6. **Budget evidence**

   > Use Subway demo definitions v1. Show up to twenty budget line items with their recorded availableAmount, source identity and currency or unit evidence if present. Explain missing values and why availableAmount does not establish historical budget consumption. No external actions.

   Pass: genuine line-item observations, bounded display identified, no invented currency, reservation history or policy.

7. **Invoice investigation**

   > Use Subway demo definitions v1. Investigate invoice records and their linked purchase orders using only declared relationships. Identify comparable amount differences, retain unmatched records and explain currency, scope and grain limitations. Do not infer overbilling, fraud or company tolerance policy. No external actions.

   Pass: supported links and exact receipt coverage; recomputed arithmetic; missing/incompatible comparisons remain limitations. Supported independent findings remain useful.

8. **Location attribution**

   > Use Subway demo definitions v1. Show the restaurant stores available in the snapshot. Separately summarize purchase orders by their recorded finance location where supported. Explain whether the sources establish a mapping between those locations and central stores. No external actions.

   Pass: distinct location namespaces. No similarity-based cross-database identity or made-up restaurant spending.

9. **Performance readiness**

   > Use Subway demo definitions v1. Review the available P&L actual, AOP and UEM definitions and evidence. Explain which restaurant performance comparisons are supported and which need compatible measures, periods, locations or formulas. Cite the available definitions. No external actions.

   Pass: useful source-cited explanation. Collection names do not establish official formulas or restaurant profitability.

10. **Documents and freshness**

    > Use Subway demo definitions v1. Explain the available budget and procurement definitions using actual indexed document passages where available. Distinguish example assumptions, application-code descriptions and observed records. State which attachment contents and current-period data coverage are unavailable. No external actions.

    Pass: exact available passages/citations, no invented PDF content, current data or company policy.

## Integration prompts

Select your connected Google account before testing 11–15. These prompts prepare
real external actions: review the exact recipient, payload and approvals before Run.
Native read-only prompts above need no Google account. Public research also needs
the existing tenant research tools enabled.

11. **Email**

    > Use Subway demo definitions v1. Count purchase orders by raw status in the available snapshot and email me the summary using my selected Google account. Include the source limitations and demo-assumption label.

12. **Sheets + email**

    > Use Subway demo definitions v1. Summarize recorded PO value by stored currency and raw status, create a new Google Sheet with the results and email me its link using my selected Google account. Preserve the demo-assumption label and historical snapshot limitation.

13. **Daily schedule**

    > Use Subway demo definitions v1. Every day at 6 PM India time, count purchase orders by raw status from the available snapshot and email me the result. Label the source historical and do not claim it contains today's activity. Prepare the schedule for review.

14. **Calendar**

    > Use Subway demo definitions v1. Investigate supported invoice-to-PO amount differences now, then add a thirty-minute review to my primary calendar tomorrow at 10 AM India time with the qualified findings and limitations in the description. Use my selected Google account. Prepare for review.

15. **Public research**

    > Use Subway demo definitions v1. Summarize the available procurement evidence and research public guidance on restaurant invoice reconciliation. Keep private records, supplier identities, document IDs and business amounts out of outbound searches. Separate public recommendations from company policy. No email or other external writes.

For email, verify a delivery receipt and actual inbox arrival. For Sheets, open the
artifact and compare its contents with verified query results. For Calendar, verify
the event ID, date, time, duration and content. For schedules, verify consent, active
state, next occurrence and actual occurrence history; a saved proposal is insufficient.

## Record each manual result

Record prompt number, workflow ID/version, run ID, profile ID/hash from saved
planning context, query IDs, observed answer, expected-versus-actual differences,
tool receipts/artifact links, and schedule details where relevant. Mark outcomes
as passed, failed, or limited by a named source/configuration prerequisite.

An honest missing-data limitation is not evidence that absent facts should be
fabricated. A valid supported query failing with a type error, incorrect arithmetic,
wrong source routing or missing required UI behavior is a defect to investigate.

## Remaining prerequisites

- Release the latest tested source before using these prompts to accept the new behavior.
- Supply an authorized live event/refresh adapter for real-time and current-period automation; restored snapshots are not feeds.
- Supply actual source identity mappings or missing document contents when a use case requires them.
- Verify real Google consent/delivery and live model quality manually.
- Qualify PostgreSQL concurrency/failover with an isolated configured test DSN if PostgreSQL deployment is intended.

The example profile resolves explicitly chosen vocabulary for testing. It does not
complete those external prerequisites or establish official restaurant policies.
