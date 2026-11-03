// Synthetic saved snapshot evaluated by the Python monitoring report.
import {businessMonitoringSchema} from '../../api/business-ontology';
const fixture={
  "report_version": "simpson-monitoring-readiness-v1",
  "version_id": "v2",
  "graph_id": "g1",
  "change_node_id": null,
  "period_start": "2026-01-01",
  "period_end": "2026-12-31",
  "period_bounds": "inclusive",
  "status": "requires_evidence",
  "prerequisites": [
    {
      "prerequisite_id": "physical_identity",
      "label": "Physical-engine identity",
      "status": "unavailable",
      "message": "Serial/reference observations do not establish a stable physical engine or deduplicate incidents.",
      "evidence_observations": 0,
      "evidence_node_ids": [],
      "evidence_nodes_truncated": false
    },
    {
      "prerequisite_id": "applicability",
      "label": "Scoped change applicability",
      "status": "unavailable",
      "message": "Selected change fields do not verify model/company/plant/component scope, serial ordering, exceptions or retrofits.",
      "evidence_observations": 0,
      "evidence_node_ids": [],
      "evidence_nodes_truncated": false
    },
    {
      "prerequisite_id": "incorporation",
      "label": "Actual change incorporation",
      "status": "unavailable",
      "message": "No verified installation/production/configuration evidence mapping establishes incorporation in a physical engine.",
      "evidence_observations": 0,
      "evidence_node_ids": [],
      "evidence_nodes_truncated": false
    },
    {
      "prerequisite_id": "comparable_failures",
      "label": "Confirmed comparable failures",
      "status": "unavailable",
      "message": "Defect, potential-cause, approver and status values do not confirm equivalent mechanisms, root causes or distinct failure events.",
      "evidence_observations": 0,
      "evidence_node_ids": [],
      "evidence_nodes_truncated": false
    },
    {
      "prerequisite_id": "population",
      "label": "Eligible monitored population",
      "status": "unavailable",
      "message": "An exact-serial bounded graph is not a complete eligible engine cohort or population denominator.",
      "evidence_observations": 0,
      "evidence_node_ids": [],
      "evidence_nodes_truncated": false
    },
    {
      "prerequisite_id": "exposure",
      "label": "Longitudinal operating exposure",
      "status": "unavailable",
      "message": "Individual complaint/claim hour readings are not longitudinal exposure, follow-up completeness or a sufficient-exposure threshold.",
      "evidence_observations": 0,
      "evidence_node_ids": [],
      "evidence_nodes_truncated": false
    },
    {
      "prerequisite_id": "source_coverage",
      "label": "Observation and source coverage",
      "status": "observed_unverified",
      "message": "Collection outcomes describe bounded searches only; even all matched records cannot prove follow-up/population completeness.",
      "evidence_observations": 0,
      "evidence_node_ids": [],
      "evidence_nodes_truncated": false
    },
    {
      "prerequisite_id": "period",
      "label": "Declared observation window",
      "status": "declared",
      "message": "The entered calendar-day window is inclusive; declaring a window does not establish complete observation coverage.",
      "evidence_observations": 0,
      "evidence_node_ids": [],
      "evidence_nodes_truncated": false
    }
  ],
  "rows": [
    {
      "label": "engineNo",
      "node_id": "node1",
      "collection": "tickets",
      "field": "engineNo",
      "kind": "identifier",
      "source_state": "not_projected",
      "state": "not_projected",
      "value": null,
      "normalized": null,
      "date_precision": null,
      "syntactically_usable": false,
      "record_sha256": "4f53cda18c2baa0c0354bb5f9a3ecbe5ed12ab4d8e11ba873c2f11161202b945",
      "role": "service",
      "connection_id": "db1",
      "category": "identity_context",
      "window_bucket": "not_applicable",
      "associations": [
        "candidate"
      ],
      "selected_change": false,
      "qualification": "Separate saved source observation; not a confirmed failure, cohort member, incorporation or recurrence."
    },
    {
      "label": "oemOrg",
      "node_id": "node1",
      "collection": "tickets",
      "field": "oemOrg",
      "kind": "identifier",
      "source_state": "not_projected",
      "state": "not_projected",
      "value": null,
      "normalized": null,
      "date_precision": null,
      "syntactically_usable": false,
      "record_sha256": "4f53cda18c2baa0c0354bb5f9a3ecbe5ed12ab4d8e11ba873c2f11161202b945",
      "role": "service",
      "connection_id": "db1",
      "category": "identity_context",
      "window_bucket": "not_applicable",
      "associations": [
        "candidate"
      ],
      "selected_change": false,
      "qualification": "Separate saved source observation; not a confirmed failure, cohort member, incorporation or recurrence."
    },
    {
      "label": "engineModal",
      "node_id": "node1",
      "collection": "tickets",
      "field": "engineModal",
      "kind": "identifier",
      "source_state": "not_projected",
      "state": "not_projected",
      "value": null,
      "normalized": null,
      "date_precision": null,
      "syntactically_usable": false,
      "record_sha256": "4f53cda18c2baa0c0354bb5f9a3ecbe5ed12ab4d8e11ba873c2f11161202b945",
      "role": "service",
      "connection_id": "db1",
      "category": "identity_context",
      "window_bucket": "not_applicable",
      "associations": [
        "candidate"
      ],
      "selected_change": false,
      "qualification": "Separate saved source observation; not a confirmed failure, cohort member, incorporation or recurrence."
    },
    {
      "label": "complaintRecord.hmr",
      "node_id": "node1",
      "collection": "tickets",
      "field": "complaintRecord.hmr",
      "kind": "hours",
      "source_state": "not_projected",
      "state": "not_projected",
      "value": null,
      "normalized": null,
      "date_precision": null,
      "syntactically_usable": false,
      "record_sha256": "4f53cda18c2baa0c0354bb5f9a3ecbe5ed12ab4d8e11ba873c2f11161202b945",
      "role": "service",
      "connection_id": "db1",
      "category": "recorded_hours",
      "window_bucket": "not_applicable",
      "associations": [
        "candidate"
      ],
      "selected_change": false,
      "qualification": "Separate saved source observation; not a confirmed failure, cohort member, incorporation or recurrence."
    },
    {
      "label": "cutInNumber",
      "node_id": "node1",
      "collection": "tickets",
      "field": "cutInNumber",
      "kind": "identifier",
      "source_state": "not_projected",
      "state": "not_projected",
      "value": null,
      "normalized": null,
      "date_precision": null,
      "syntactically_usable": false,
      "record_sha256": "4f53cda18c2baa0c0354bb5f9a3ecbe5ed12ab4d8e11ba873c2f11161202b945",
      "role": "service",
      "connection_id": "db1",
      "category": "change_context",
      "window_bucket": "not_applicable",
      "associations": [
        "candidate"
      ],
      "selected_change": false,
      "qualification": "Separate saved source observation; not a confirmed failure, cohort member, incorporation or recurrence."
    },
    {
      "label": "cutIn",
      "node_id": "node1",
      "collection": "tickets",
      "field": "cutIn",
      "kind": "identifier",
      "source_state": "not_projected",
      "state": "not_projected",
      "value": null,
      "normalized": null,
      "date_precision": null,
      "syntactically_usable": false,
      "record_sha256": "4f53cda18c2baa0c0354bb5f9a3ecbe5ed12ab4d8e11ba873c2f11161202b945",
      "role": "service",
      "connection_id": "db1",
      "category": "change_context",
      "window_bucket": "not_applicable",
      "associations": [
        "candidate"
      ],
      "selected_change": false,
      "qualification": "Separate saved source observation; not a confirmed failure, cohort member, incorporation or recurrence."
    },
    {
      "label": "dateOfFailure",
      "node_id": "node2",
      "collection": "claims",
      "field": "dateOfFailure",
      "kind": "date",
      "source_state": "not_projected",
      "state": "not_projected",
      "value": null,
      "normalized": null,
      "date_precision": null,
      "syntactically_usable": false,
      "record_sha256": "4f53cda18c2baa0c0354bb5f9a3ecbe5ed12ab4d8e11ba873c2f11161202b945",
      "role": "quality",
      "connection_id": "db2",
      "category": "failure_date",
      "window_bucket": "unavailable",
      "associations": [
        "candidate"
      ],
      "selected_change": false,
      "qualification": "Separate saved source observation; not a confirmed failure, cohort member, incorporation or recurrence."
    },
    {
      "label": "reason",
      "node_id": "node2",
      "collection": "claims",
      "field": "reason",
      "kind": "identifier",
      "source_state": "not_projected",
      "state": "not_projected",
      "value": null,
      "normalized": null,
      "date_precision": null,
      "syntactically_usable": false,
      "record_sha256": "4f53cda18c2baa0c0354bb5f9a3ecbe5ed12ab4d8e11ba873c2f11161202b945",
      "role": "quality",
      "connection_id": "db2",
      "category": "failure_context",
      "window_bucket": "not_applicable",
      "associations": [
        "candidate"
      ],
      "selected_change": false,
      "qualification": "Separate saved source observation; not a confirmed failure, cohort member, incorporation or recurrence."
    },
    {
      "label": "status",
      "node_id": "node2",
      "collection": "claims",
      "field": "status",
      "kind": "identifier",
      "source_state": "not_projected",
      "state": "not_projected",
      "value": null,
      "normalized": null,
      "date_precision": null,
      "syntactically_usable": false,
      "record_sha256": "4f53cda18c2baa0c0354bb5f9a3ecbe5ed12ab4d8e11ba873c2f11161202b945",
      "role": "quality",
      "connection_id": "db2",
      "category": "failure_context",
      "window_bucket": "not_applicable",
      "associations": [
        "candidate"
      ],
      "selected_change": false,
      "qualification": "Separate saved source observation; not a confirmed failure, cohort member, incorporation or recurrence."
    },
    {
      "label": "hoursCovered",
      "node_id": "node2",
      "collection": "claims",
      "field": "hoursCovered",
      "kind": "hours",
      "source_state": "not_projected",
      "state": "not_projected",
      "value": null,
      "normalized": null,
      "date_precision": null,
      "syntactically_usable": false,
      "record_sha256": "4f53cda18c2baa0c0354bb5f9a3ecbe5ed12ab4d8e11ba873c2f11161202b945",
      "role": "quality",
      "connection_id": "db2",
      "category": "recorded_hours",
      "window_bucket": "not_applicable",
      "associations": [
        "candidate"
      ],
      "selected_change": false,
      "qualification": "Separate saved source observation; not a confirmed failure, cohort member, incorporation or recurrence."
    }
  ],
  "total_rows": 10,
  "offset": 0,
  "limit": 20,
  "has_more": false,
  "next_offset": null,
  "summary": {
    "saved_records": 2,
    "change_candidates": 0,
    "failure_date_observations": {
      "before_period": 0,
      "within_period": 0,
      "after_period": 0,
      "invalid_date": 0,
      "unavailable": 1
    },
    "truncated_collections": 0
  },
  "metrics": {
    "confirmed_recurrences": null,
    "failure_rate": null,
    "change_effectiveness": null,
    "monitored_population": null,
    "operating_exposure": null
  },
  "limits": [
    "Only this bounded immutable graph is inspected; selected change does not establish a cohort or filter records into verified applicability.",
    "Date buckets count source-field observations, not distinct failures. Claims and inspections can describe the same incident; no numerator is inferred.",
    "Zero observations is not zero failures. Missing, invalid or unprojected values and truncated/unavailable collections remain explicit.",
    "Failure dates retain recorded calendar days and date/time precision; no current-time fallback, serial ordering or post-cut-in inference.",
    "No recurrence, rate or effectiveness conclusion is available without verified identity, applicability, incorporation, comparable failures, population and exposure."
  ],
  "provenance": {
    "graph_created_at": "2026-10-31",
    "source_revisions": {
      "service": 1,
      "quality": 1
    },
    "graph_sha256": "f6504b61bc68371497bc5dd90205d846cc1d6e681100f7eba70901721116fc44",
    "definition_sha256": "6ebc1ab0fc85cbf6604fd42ae5e9640d659bf257a786ad9d892e94533bec91a1"
  },
  "company_queries": 0,
  "model_calls": 0,
  "source_writes": 0,
  "monitoring_scheduled": false,
  "report_sha256": "5b1671657b86871c9380a89f903bf60979836fcea7050347ed10536c2a5a163d"
};
export function monitoringReport(){return businessMonitoringSchema.parse(structuredClone(fixture));}
