# Subway ontology evidence resolution

Deployed 10 November 2026. This corrects overly broad prerequisites in ontology
retrieval and supplies existing evidence routes before treating a question as blocked.
Workflow code, query engines, saved workflows and source records are unchanged.

The immutable v4 ontology and all four package revisions remain intact. A separate
hashed supplement, `ontology/subway/evidence-resolution-v1.json`, is attached only to
retrieved copies from the exact v4 content hash and Subway workspace/owner. Retrieved
references retain the original definition hash and expose a separate resolution hash
and exact source-code quotations. Other tenants, owners and versions receive no
supplement. This is evidence guidance, not executable policy or new action authority.

| Question | Evidence route now supplied | When additional evidence is needed |
| --- | --- | --- |
| Does a proposed amount fit a line item's budget? | Read its current `availableAmount`; aggregate the supplied requested amounts by line item and compare, following the archived service guard. | Historical reservation ownership, lifecycle or balance at a past date needs historical records. |
| Does this PO need a requisition approval? | Establish whether `purchaseRequestId` is supplied/present. The code invokes PR validation only for that branch; direct PO facts remain usable without a PR. | A genuinely linked requisition requires its own approval evidence; PO approval cannot substitute for it. |
| What happened during this approval's stages? | Use the stage's own identity, approval reference, status, actor fields, action dates and comments. Try exact parent/inverse/backlink/report references for parent context. | Final parent status or document identity cannot be established merely because one stage says approved. |

The complete original-record scan checked 43,439 POs, 94,452 approvals, 22,550 line
items, 3,236 budgets, 213,676 stages and both databases' audit/API logs. No supplied PO
has a populated requisition link, no supplied approval is typed `pr_approval`, and all
22,550 line items have numeric `availableAmount`; none has stored `reservedAmount`.
These snapshot observations do not prove a historical application's version or branch.
The live readers must still fetch current facts rather than use these counts as answers.

Exact backlinks were also checked in line items, budgets, CF mappings, vendor-GRN
stage timelines and smallware stages, in addition to the earlier PO/GRN/invoice/budget
modification checks. Complete PO, GRN and advance-payment report snapshots contain no
matching approval reference for the four orphan parent IDs. Audit history did not
recover those parent objects. All eleven child stage records remain usable evidence;
no synthetic approval or inferred final decision was inserted. Original archives,
logs and mail records were not imported into the client's query surface.

Verification: 225 baseline regressions passed before the correction; 12 focused
resolution/dump-grounding tests and 36 affected ontology/auth/isolation regressions
passed afterward (overlapping suites). All 13 rule questions and 65 definition lookups
still pass with exact citations. Shared contracts, strict OpenSpec and whitespace
checks pass. Both live client sessions/ontology APIs respond after Subway's reload;
foreign-source requests are denied both ways. Fingerprints preserve workflow code,
live workflows/revisions/runs, credentials, metadata, Google accounts, ontology and
package documents. Simpsons was not restarted. No external model calls or company
source writes were made. No workflow was executed as part of this correction.

Private receipts: `.local/tenants/subway/reaudit-20261110/`, including the alternative
source scans, exact backlink checks, evidence matrix, test logs, preservation hashes
and live resolution verification. Rollback restores only `business_planning.py` from
`release/business_planning.before.py` and reloads Subway; its base v4 remains unchanged.
