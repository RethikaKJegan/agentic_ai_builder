# Simpsons technical field verification — 2026-10-30

Four of the eleven originally unresolved fields were observed through targeted read-only queries on the existing Simpsons connections. All four were observed as BSON strings. This confirms field presence and sampled type, not business meaning, global consistency, account/company reference targets, or approval policy.

| Collection | Field | Technical result |
| --- | --- | --- |
| `tickets` | `engineReplacementStatus` | Observed string |
| `tickets` | `cutInNumber` | Observed string |
| `advaced-engine-replacements` | `oem` | Observed string; target account not independently verified |
| `courseschedules` | `requestedBy` | Observed string; target account not independently verified |
| `claimsftps` | `status` | No matching field observed in the completed existence query; collection has records and no declaration for this field |
| `failedpartanalyses` | `partNumber` | Collection empty; no database schema declaration |
| `failedpartanalyses` | `approvedBy` | Collection empty; no database schema declaration |
| `icacapas` | `defect` | Collection empty; no database schema declaration |
| `workshopmanualrevisions` | `manual` | Collection empty; no database schema declaration; exact application field name still unverified |
| `workshopmanualrevisions` | `version` | Collection empty; no database schema declaration |
| `workshopmanualrevisions` | `approvedBy` | Collection empty; no database schema declaration |

An empty MongoDB collection without a validator cannot establish its allowed field names. The seven remaining bindings require authoritative application model/schema evidence, or later permitted observations. An application developer can provide that technical evidence without a business expert. Expert review is still needed for intended meanings and policies; none is inferred from this check.

The [revised unpublished draft](draft-v2/README.md) retains all 416 record identities and reduces unresolved bindings from eleven to seven. It adds stable metadata field identifiers using the existing connector identity function, hashes the technical evidence into the affected attributes' provenance, and advances only copied local metadata revisions. Original [draft records](draft/ontology.json) and the original isolated database are preserved. This is an artifact revision, not an approved published ontology version.

## Method and boundaries

- Existing connector configuration and scoped saved connection identities were reused. SQLite input was opened read-only; no application service was instantiated against the live store. A separate diagnostic checked current connector credentials read-only and found them equal to the saved credentials; no credentials were changed or exported.
- Collection metadata discovery is bounded to 100 collections. Each existence/type query has a three-second server limit and each connector session a sixty-second deadline. Field queries use `$exists`, then at most 25 matching documents, then server-side BSON type grouping. Matching counts are bounded sample counts, not population totals.
- An initial multi-name metadata filter was rejected by the Atlas deployment with code 8000. The final check reused the existing connector's supported bounded collection listing and completed all eleven outcomes. [Initial attempt](field-verification-initial-attempt.json) and [completed evidence](field-verification.json) are retained separately.
- No source documents, identifiers, credentials or source values were exported. No company data/schema writes, workflow executions, business approvals, calibration labels or publication actions were performed.
- The construction step consumes the saved technical report offline and writes only a new local database and new artifacts. Both input SQLite SHA-256 values match. It does not contact company systems.

Revised database: `.local/ontology-foundation/simpsons-domain-draft-v2.sqlite3`, owner-only permissions, no copied connector secrets. Native validation passes; the three ontology-only previews retain 181, 88 and 91 records. No approved selection manifest is created, and draft-only publication remains blocked.

Reproduce the offline construction with new output paths:

```sh
.venv-integrations/bin/python scripts/build_simpsons_ontology.py \
  --field-verification docs/ontology-review/simpsons/field-verification.json \
  --database .local/ontology-foundation/simpsons-domain-draft-next.sqlite3 \
  --output docs/ontology-review/simpsons/draft-next
```

The technical verification script deliberately refuses to overwrite existing evidence. This review leaves actual Simpsons business approval/publication and the earlier production build gate pending.
