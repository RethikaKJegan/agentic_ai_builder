// Synthetic fixtures; no Simpson case conclusions are asserted.
import {businessRuleExecutionCatalogueSchema,businessRuleExecutionResultSchema,businessRuleEvidenceSchema} from '../../api/business-ontology';
const catalogue={
  "version_id": "v2",
  "graph_id": "g1",
  "handler_version": "simpson-reference-execution-v1",
  "rules": [
    {
      "rule_id": "failure:unconfirmed_similarity",
      "label": "Check root-cause evidence",
      "module_id": "failure",
      "available": true,
      "handler_version": "simpson-reference-execution-v1",
      "reason": null,
      "fact_specs": [
        {
          "field_id": "suspected_cause",
          "label": "Suspected or documented cause",
          "kind": "text",
          "choices": []
        },
        {
          "field_id": "finding_basis",
          "label": "Finding basis",
          "kind": "choice",
          "choices": [
            "similarity_only",
            "inspection",
            "test_result"
          ]
        },
        {
          "field_id": "diagnosis",
          "label": "Current case diagnosis",
          "kind": "choice",
          "choices": [
            "confirmed",
            "inconclusive",
            "ruled_out"
          ]
        },
        {
          "field_id": "finding_details",
          "label": "Inspection or test finding",
          "kind": "text",
          "choices": []
        }
      ]
    },
    {
      "rule_id": "effectivity:recurrence_needs_evidence",
      "label": "Check post-change recurrence",
      "module_id": "effectivity",
      "available": true,
      "handler_version": "simpson-reference-execution-v1",
      "reason": null,
      "fact_specs": [
        {
          "field_id": "physical_identity",
          "label": "Engine identity link",
          "kind": "choice",
          "choices": [
            "same_engine",
            "different_engines"
          ]
        },
        {
          "field_id": "applicability",
          "label": "Change applicability",
          "kind": "choice",
          "choices": [
            "applies",
            "does_not_apply"
          ]
        },
        {
          "field_id": "incorporation",
          "label": "Changed component incorporation",
          "kind": "choice",
          "choices": [
            "installed",
            "not_installed"
          ]
        },
        {
          "field_id": "mechanism",
          "label": "Failure mechanism comparison",
          "kind": "choice",
          "choices": [
            "same",
            "different"
          ]
        },
        {
          "field_id": "root_cause",
          "label": "Root-cause comparison",
          "kind": "choice",
          "choices": [
            "same",
            "different"
          ]
        },
        {
          "field_id": "inspection_conclusion",
          "label": "Current investigation conclusion",
          "kind": "choice",
          "choices": [
            "comparable_failure",
            "no_comparable_failure"
          ]
        },
        {
          "field_id": "incorporation_date",
          "label": "Actual incorporation date",
          "kind": "date",
          "choices": []
        },
        {
          "field_id": "failure_date",
          "label": "Current failure date",
          "kind": "date",
          "choices": []
        },
        {
          "field_id": "post_change_hours",
          "label": "Recorded post-change operating hours",
          "kind": "hours",
          "choices": []
        },
        {
          "field_id": "required_hours",
          "label": "Required operating exposure",
          "kind": "hours",
          "choices": []
        }
      ]
    },
    {
      "rule_id": "monitoring:rate_requires_exposure",
      "label": "Calculate evidence-backed failure rate",
      "module_id": "monitoring",
      "available": true,
      "handler_version": "simpson-reference-execution-v1",
      "reason": null,
      "fact_specs": [
        {
          "field_id": "cohort",
          "label": "Monitored cohort definition",
          "kind": "text",
          "choices": []
        },
        {
          "field_id": "period_start",
          "label": "Cohort period start",
          "kind": "date",
          "choices": []
        },
        {
          "field_id": "period_end",
          "label": "Cohort period end",
          "kind": "date",
          "choices": []
        },
        {
          "field_id": "coverage",
          "label": "Cohort follow-up coverage",
          "kind": "choice",
          "choices": [
            "complete",
            "incomplete"
          ]
        },
        {
          "field_id": "counting_basis",
          "label": "Failure counting basis",
          "kind": "choice",
          "choices": [
            "distinct_first_failures",
            "other_or_unconfirmed"
          ]
        },
        {
          "field_id": "confirmed_failures",
          "label": "Confirmed failed engines",
          "kind": "integer",
          "choices": []
        },
        {
          "field_id": "population_engines",
          "label": "Engines at risk",
          "kind": "integer",
          "choices": []
        },
        {
          "field_id": "exposure_hours",
          "label": "Total at-risk engine operating hours",
          "kind": "hours",
          "choices": []
        }
      ]
    }
  ],
  "sources": [
    {
      "source_id": "execution_source",
      "title": "Synthetic execution evidence",
      "sha256": "fixture_sha",
      "module_ids": [
        "failure",
        "effectivity",
        "monitoring"
      ]
    }
  ],
  "evidence": []
};
export function executionCatalogue(){return businessRuleExecutionCatalogueSchema.parse(structuredClone(catalogue));}

const reports={
  "failure:unconfirmed_similarity": {
    "outcome": "documented_root_cause",
    "checks": [
      {
        "check_id": "suspected_cause",
        "status": "passed",
        "observed": "Gasket leak",
        "message": "A cause must be explicitly stated; no cause is inferred from similar symptoms."
      },
      {
        "check_id": "finding_basis",
        "status": "passed",
        "observed": "inspection",
        "message": "Similarity alone cannot confirm a root cause."
      },
      {
        "check_id": "diagnosis",
        "status": "passed",
        "observed": "confirmed",
        "message": "A current-case conclusion must be documented."
      },
      {
        "check_id": "finding_details",
        "status": "passed",
        "observed": "Inspection and pressure test identify a gasket leak.",
        "message": "The current inspection/test finding must be stated."
      }
    ],
    "calculations": {},
    "rule_id": "failure:unconfirmed_similarity",
    "label": "Check root-cause evidence",
    "handler_version": "simpson-reference-execution-v1",
    "version_id": "v2",
    "graph_id": "g1",
    "subject_node_id": "node1",
    "change_node_id": null,
    "evidence_id": "ev0",
    "facts": {
      "suspected_cause": {
        "value": "Gasket leak",
        "quote": "Synthetic execution evidence: {\"effectivity:recurrence_needs_evidence\": {\"applicability\": \"applies\", \"failure_date\": \"2026-06-01\", \"incorporation\": \"installed\", \"incorporation_date\": \"2026-01-01\", \"inspection_conclusion\": \"comparable_failure\", \"mechanism\": \"same\", \"physical_identity\": \"same_engine\", \"post_change_hours\": \"100\", \"required_hours\": \"100\", \"root_cause\": \"same\"}, \"failure:unconfirmed_similarity\": {\"diagnosis\": \"confirmed\", \"finding_basis\": \"inspection\", \"finding_details\": \"Inspection and pressure test identify a gasket leak.\", \"suspected_cause\": \"Gasket leak\"}, \"monitoring:rate_requires_exposure\": {\"cohort\": \"Synthetic MODEL-A cohort\", \"confirmed_failures\": 5, \"counting_basis\": \"distinct_first_failures\", \"coverage\": \"complete\", \"exposure_hours\": \"10000\", \"period_end\": \"2026-12-31\", \"period_start\": \"2026-01-01\", \"population_engines\": 100}}"
      },
      "finding_basis": {
        "value": "inspection",
        "quote": "Synthetic execution evidence: {\"effectivity:recurrence_needs_evidence\": {\"applicability\": \"applies\", \"failure_date\": \"2026-06-01\", \"incorporation\": \"installed\", \"incorporation_date\": \"2026-01-01\", \"inspection_conclusion\": \"comparable_failure\", \"mechanism\": \"same\", \"physical_identity\": \"same_engine\", \"post_change_hours\": \"100\", \"required_hours\": \"100\", \"root_cause\": \"same\"}, \"failure:unconfirmed_similarity\": {\"diagnosis\": \"confirmed\", \"finding_basis\": \"inspection\", \"finding_details\": \"Inspection and pressure test identify a gasket leak.\", \"suspected_cause\": \"Gasket leak\"}, \"monitoring:rate_requires_exposure\": {\"cohort\": \"Synthetic MODEL-A cohort\", \"confirmed_failures\": 5, \"counting_basis\": \"distinct_first_failures\", \"coverage\": \"complete\", \"exposure_hours\": \"10000\", \"period_end\": \"2026-12-31\", \"period_start\": \"2026-01-01\", \"population_engines\": 100}}"
      },
      "diagnosis": {
        "value": "confirmed",
        "quote": "Synthetic execution evidence: {\"effectivity:recurrence_needs_evidence\": {\"applicability\": \"applies\", \"failure_date\": \"2026-06-01\", \"incorporation\": \"installed\", \"incorporation_date\": \"2026-01-01\", \"inspection_conclusion\": \"comparable_failure\", \"mechanism\": \"same\", \"physical_identity\": \"same_engine\", \"post_change_hours\": \"100\", \"required_hours\": \"100\", \"root_cause\": \"same\"}, \"failure:unconfirmed_similarity\": {\"diagnosis\": \"confirmed\", \"finding_basis\": \"inspection\", \"finding_details\": \"Inspection and pressure test identify a gasket leak.\", \"suspected_cause\": \"Gasket leak\"}, \"monitoring:rate_requires_exposure\": {\"cohort\": \"Synthetic MODEL-A cohort\", \"confirmed_failures\": 5, \"counting_basis\": \"distinct_first_failures\", \"coverage\": \"complete\", \"exposure_hours\": \"10000\", \"period_end\": \"2026-12-31\", \"period_start\": \"2026-01-01\", \"population_engines\": 100}}"
      },
      "finding_details": {
        "value": "Inspection and pressure test identify a gasket leak.",
        "quote": "Synthetic execution evidence: {\"effectivity:recurrence_needs_evidence\": {\"applicability\": \"applies\", \"failure_date\": \"2026-06-01\", \"incorporation\": \"installed\", \"incorporation_date\": \"2026-01-01\", \"inspection_conclusion\": \"comparable_failure\", \"mechanism\": \"same\", \"physical_identity\": \"same_engine\", \"post_change_hours\": \"100\", \"required_hours\": \"100\", \"root_cause\": \"same\"}, \"failure:unconfirmed_similarity\": {\"diagnosis\": \"confirmed\", \"finding_basis\": \"inspection\", \"finding_details\": \"Inspection and pressure test identify a gasket leak.\", \"suspected_cause\": \"Gasket leak\"}, \"monitoring:rate_requires_exposure\": {\"cohort\": \"Synthetic MODEL-A cohort\", \"confirmed_failures\": 5, \"counting_basis\": \"distinct_first_failures\", \"coverage\": \"complete\", \"exposure_hours\": \"10000\", \"period_end\": \"2026-12-31\", \"period_start\": \"2026-01-01\", \"population_engines\": 100}}"
      }
    },
    "source": {
      "source_id": "execution_source",
      "title": "Synthetic execution evidence",
      "sha256": "fixture_source_hash"
    },
    "observations": [],
    "qualification": "Computed from selected source-cited assertions, not independently verified.",
    "limits": [
      "No source/model call or business record write."
    ],
    "provenance": {
      "definition_sha256": "fixture_rule_hash",
      "graph_sha256": "fixture_graph_hash",
      "evidence_sha256": "fixture_evidence_hash"
    },
    "rules_executed": true,
    "company_queries": 0,
    "model_calls": 0,
    "source_writes": 0,
    "independently_verified": false,
    "report_sha256": "fixture_report_hash"
  },
  "effectivity:recurrence_needs_evidence": {
    "outcome": "recurrence_supported",
    "checks": [
      {
        "check_id": "physical_identity",
        "status": "passed",
        "observed": "same_engine",
        "message": "Required cited condition: same engine."
      },
      {
        "check_id": "applicability",
        "status": "passed",
        "observed": "applies",
        "message": "Required cited condition: applies."
      },
      {
        "check_id": "incorporation",
        "status": "passed",
        "observed": "installed",
        "message": "Required cited condition: installed."
      },
      {
        "check_id": "mechanism",
        "status": "passed",
        "observed": "same",
        "message": "Required cited condition: same."
      },
      {
        "check_id": "root_cause",
        "status": "passed",
        "observed": "same",
        "message": "Required cited condition: same."
      },
      {
        "check_id": "inspection_conclusion",
        "status": "passed",
        "observed": "comparable_failure",
        "message": "Required cited condition: comparable failure."
      },
      {
        "check_id": "incorporation_date",
        "status": "passed",
        "observed": "2026-01-01",
        "message": "Explicit source input required."
      },
      {
        "check_id": "failure_date",
        "status": "passed",
        "observed": "2026-06-01",
        "message": "Explicit source input required."
      },
      {
        "check_id": "post_change_hours",
        "status": "passed",
        "observed": "100",
        "message": "Explicit source input required."
      },
      {
        "check_id": "required_hours",
        "status": "passed",
        "observed": "100",
        "message": "Explicit source input required."
      },
      {
        "check_id": "post_change_chronology",
        "status": "passed",
        "observed": {
          "incorporation_date": "2026-01-01",
          "failure_date": "2026-06-01"
        },
        "message": "Failure must be on/after documented incorporation; calendar-day precision only."
      },
      {
        "check_id": "sufficient_exposure",
        "status": "passed",
        "observed": {
          "hours": "100",
          "required": "100"
        },
        "message": "Recorded post-change hours must meet the cited minimum; no threshold is invented."
      }
    ],
    "calculations": {},
    "rule_id": "effectivity:recurrence_needs_evidence",
    "label": "Check post-change recurrence",
    "handler_version": "simpson-reference-execution-v1",
    "version_id": "v2",
    "graph_id": "g1",
    "subject_node_id": "node1",
    "change_node_id": "change1",
    "evidence_id": "ev1",
    "facts": {
      "physical_identity": {
        "value": "same_engine",
        "quote": "Synthetic execution evidence: {\"effectivity:recurrence_needs_evidence\": {\"applicability\": \"applies\", \"failure_date\": \"2026-06-01\", \"incorporation\": \"installed\", \"incorporation_date\": \"2026-01-01\", \"inspection_conclusion\": \"comparable_failure\", \"mechanism\": \"same\", \"physical_identity\": \"same_engine\", \"post_change_hours\": \"100\", \"required_hours\": \"100\", \"root_cause\": \"same\"}, \"failure:unconfirmed_similarity\": {\"diagnosis\": \"confirmed\", \"finding_basis\": \"inspection\", \"finding_details\": \"Inspection and pressure test identify a gasket leak.\", \"suspected_cause\": \"Gasket leak\"}, \"monitoring:rate_requires_exposure\": {\"cohort\": \"Synthetic MODEL-A cohort\", \"confirmed_failures\": 5, \"counting_basis\": \"distinct_first_failures\", \"coverage\": \"complete\", \"exposure_hours\": \"10000\", \"period_end\": \"2026-12-31\", \"period_start\": \"2026-01-01\", \"population_engines\": 100}}"
      },
      "applicability": {
        "value": "applies",
        "quote": "Synthetic execution evidence: {\"effectivity:recurrence_needs_evidence\": {\"applicability\": \"applies\", \"failure_date\": \"2026-06-01\", \"incorporation\": \"installed\", \"incorporation_date\": \"2026-01-01\", \"inspection_conclusion\": \"comparable_failure\", \"mechanism\": \"same\", \"physical_identity\": \"same_engine\", \"post_change_hours\": \"100\", \"required_hours\": \"100\", \"root_cause\": \"same\"}, \"failure:unconfirmed_similarity\": {\"diagnosis\": \"confirmed\", \"finding_basis\": \"inspection\", \"finding_details\": \"Inspection and pressure test identify a gasket leak.\", \"suspected_cause\": \"Gasket leak\"}, \"monitoring:rate_requires_exposure\": {\"cohort\": \"Synthetic MODEL-A cohort\", \"confirmed_failures\": 5, \"counting_basis\": \"distinct_first_failures\", \"coverage\": \"complete\", \"exposure_hours\": \"10000\", \"period_end\": \"2026-12-31\", \"period_start\": \"2026-01-01\", \"population_engines\": 100}}"
      },
      "incorporation": {
        "value": "installed",
        "quote": "Synthetic execution evidence: {\"effectivity:recurrence_needs_evidence\": {\"applicability\": \"applies\", \"failure_date\": \"2026-06-01\", \"incorporation\": \"installed\", \"incorporation_date\": \"2026-01-01\", \"inspection_conclusion\": \"comparable_failure\", \"mechanism\": \"same\", \"physical_identity\": \"same_engine\", \"post_change_hours\": \"100\", \"required_hours\": \"100\", \"root_cause\": \"same\"}, \"failure:unconfirmed_similarity\": {\"diagnosis\": \"confirmed\", \"finding_basis\": \"inspection\", \"finding_details\": \"Inspection and pressure test identify a gasket leak.\", \"suspected_cause\": \"Gasket leak\"}, \"monitoring:rate_requires_exposure\": {\"cohort\": \"Synthetic MODEL-A cohort\", \"confirmed_failures\": 5, \"counting_basis\": \"distinct_first_failures\", \"coverage\": \"complete\", \"exposure_hours\": \"10000\", \"period_end\": \"2026-12-31\", \"period_start\": \"2026-01-01\", \"population_engines\": 100}}"
      },
      "mechanism": {
        "value": "same",
        "quote": "Synthetic execution evidence: {\"effectivity:recurrence_needs_evidence\": {\"applicability\": \"applies\", \"failure_date\": \"2026-06-01\", \"incorporation\": \"installed\", \"incorporation_date\": \"2026-01-01\", \"inspection_conclusion\": \"comparable_failure\", \"mechanism\": \"same\", \"physical_identity\": \"same_engine\", \"post_change_hours\": \"100\", \"required_hours\": \"100\", \"root_cause\": \"same\"}, \"failure:unconfirmed_similarity\": {\"diagnosis\": \"confirmed\", \"finding_basis\": \"inspection\", \"finding_details\": \"Inspection and pressure test identify a gasket leak.\", \"suspected_cause\": \"Gasket leak\"}, \"monitoring:rate_requires_exposure\": {\"cohort\": \"Synthetic MODEL-A cohort\", \"confirmed_failures\": 5, \"counting_basis\": \"distinct_first_failures\", \"coverage\": \"complete\", \"exposure_hours\": \"10000\", \"period_end\": \"2026-12-31\", \"period_start\": \"2026-01-01\", \"population_engines\": 100}}"
      },
      "root_cause": {
        "value": "same",
        "quote": "Synthetic execution evidence: {\"effectivity:recurrence_needs_evidence\": {\"applicability\": \"applies\", \"failure_date\": \"2026-06-01\", \"incorporation\": \"installed\", \"incorporation_date\": \"2026-01-01\", \"inspection_conclusion\": \"comparable_failure\", \"mechanism\": \"same\", \"physical_identity\": \"same_engine\", \"post_change_hours\": \"100\", \"required_hours\": \"100\", \"root_cause\": \"same\"}, \"failure:unconfirmed_similarity\": {\"diagnosis\": \"confirmed\", \"finding_basis\": \"inspection\", \"finding_details\": \"Inspection and pressure test identify a gasket leak.\", \"suspected_cause\": \"Gasket leak\"}, \"monitoring:rate_requires_exposure\": {\"cohort\": \"Synthetic MODEL-A cohort\", \"confirmed_failures\": 5, \"counting_basis\": \"distinct_first_failures\", \"coverage\": \"complete\", \"exposure_hours\": \"10000\", \"period_end\": \"2026-12-31\", \"period_start\": \"2026-01-01\", \"population_engines\": 100}}"
      },
      "inspection_conclusion": {
        "value": "comparable_failure",
        "quote": "Synthetic execution evidence: {\"effectivity:recurrence_needs_evidence\": {\"applicability\": \"applies\", \"failure_date\": \"2026-06-01\", \"incorporation\": \"installed\", \"incorporation_date\": \"2026-01-01\", \"inspection_conclusion\": \"comparable_failure\", \"mechanism\": \"same\", \"physical_identity\": \"same_engine\", \"post_change_hours\": \"100\", \"required_hours\": \"100\", \"root_cause\": \"same\"}, \"failure:unconfirmed_similarity\": {\"diagnosis\": \"confirmed\", \"finding_basis\": \"inspection\", \"finding_details\": \"Inspection and pressure test identify a gasket leak.\", \"suspected_cause\": \"Gasket leak\"}, \"monitoring:rate_requires_exposure\": {\"cohort\": \"Synthetic MODEL-A cohort\", \"confirmed_failures\": 5, \"counting_basis\": \"distinct_first_failures\", \"coverage\": \"complete\", \"exposure_hours\": \"10000\", \"period_end\": \"2026-12-31\", \"period_start\": \"2026-01-01\", \"population_engines\": 100}}"
      },
      "incorporation_date": {
        "value": "2026-01-01",
        "quote": "Synthetic execution evidence: {\"effectivity:recurrence_needs_evidence\": {\"applicability\": \"applies\", \"failure_date\": \"2026-06-01\", \"incorporation\": \"installed\", \"incorporation_date\": \"2026-01-01\", \"inspection_conclusion\": \"comparable_failure\", \"mechanism\": \"same\", \"physical_identity\": \"same_engine\", \"post_change_hours\": \"100\", \"required_hours\": \"100\", \"root_cause\": \"same\"}, \"failure:unconfirmed_similarity\": {\"diagnosis\": \"confirmed\", \"finding_basis\": \"inspection\", \"finding_details\": \"Inspection and pressure test identify a gasket leak.\", \"suspected_cause\": \"Gasket leak\"}, \"monitoring:rate_requires_exposure\": {\"cohort\": \"Synthetic MODEL-A cohort\", \"confirmed_failures\": 5, \"counting_basis\": \"distinct_first_failures\", \"coverage\": \"complete\", \"exposure_hours\": \"10000\", \"period_end\": \"2026-12-31\", \"period_start\": \"2026-01-01\", \"population_engines\": 100}}"
      },
      "failure_date": {
        "value": "2026-06-01",
        "quote": "Synthetic execution evidence: {\"effectivity:recurrence_needs_evidence\": {\"applicability\": \"applies\", \"failure_date\": \"2026-06-01\", \"incorporation\": \"installed\", \"incorporation_date\": \"2026-01-01\", \"inspection_conclusion\": \"comparable_failure\", \"mechanism\": \"same\", \"physical_identity\": \"same_engine\", \"post_change_hours\": \"100\", \"required_hours\": \"100\", \"root_cause\": \"same\"}, \"failure:unconfirmed_similarity\": {\"diagnosis\": \"confirmed\", \"finding_basis\": \"inspection\", \"finding_details\": \"Inspection and pressure test identify a gasket leak.\", \"suspected_cause\": \"Gasket leak\"}, \"monitoring:rate_requires_exposure\": {\"cohort\": \"Synthetic MODEL-A cohort\", \"confirmed_failures\": 5, \"counting_basis\": \"distinct_first_failures\", \"coverage\": \"complete\", \"exposure_hours\": \"10000\", \"period_end\": \"2026-12-31\", \"period_start\": \"2026-01-01\", \"population_engines\": 100}}"
      },
      "post_change_hours": {
        "value": "100",
        "quote": "Synthetic execution evidence: {\"effectivity:recurrence_needs_evidence\": {\"applicability\": \"applies\", \"failure_date\": \"2026-06-01\", \"incorporation\": \"installed\", \"incorporation_date\": \"2026-01-01\", \"inspection_conclusion\": \"comparable_failure\", \"mechanism\": \"same\", \"physical_identity\": \"same_engine\", \"post_change_hours\": \"100\", \"required_hours\": \"100\", \"root_cause\": \"same\"}, \"failure:unconfirmed_similarity\": {\"diagnosis\": \"confirmed\", \"finding_basis\": \"inspection\", \"finding_details\": \"Inspection and pressure test identify a gasket leak.\", \"suspected_cause\": \"Gasket leak\"}, \"monitoring:rate_requires_exposure\": {\"cohort\": \"Synthetic MODEL-A cohort\", \"confirmed_failures\": 5, \"counting_basis\": \"distinct_first_failures\", \"coverage\": \"complete\", \"exposure_hours\": \"10000\", \"period_end\": \"2026-12-31\", \"period_start\": \"2026-01-01\", \"population_engines\": 100}}"
      },
      "required_hours": {
        "value": "100",
        "quote": "Synthetic execution evidence: {\"effectivity:recurrence_needs_evidence\": {\"applicability\": \"applies\", \"failure_date\": \"2026-06-01\", \"incorporation\": \"installed\", \"incorporation_date\": \"2026-01-01\", \"inspection_conclusion\": \"comparable_failure\", \"mechanism\": \"same\", \"physical_identity\": \"same_engine\", \"post_change_hours\": \"100\", \"required_hours\": \"100\", \"root_cause\": \"same\"}, \"failure:unconfirmed_similarity\": {\"diagnosis\": \"confirmed\", \"finding_basis\": \"inspection\", \"finding_details\": \"Inspection and pressure test identify a gasket leak.\", \"suspected_cause\": \"Gasket leak\"}, \"monitoring:rate_requires_exposure\": {\"cohort\": \"Synthetic MODEL-A cohort\", \"confirmed_failures\": 5, \"counting_basis\": \"distinct_first_failures\", \"coverage\": \"complete\", \"exposure_hours\": \"10000\", \"period_end\": \"2026-12-31\", \"period_start\": \"2026-01-01\", \"population_engines\": 100}}"
      }
    },
    "source": {
      "source_id": "execution_source",
      "title": "Synthetic execution evidence",
      "sha256": "fixture_source_hash"
    },
    "observations": [],
    "qualification": "Computed from selected source-cited assertions, not independently verified.",
    "limits": [
      "No source/model call or business record write."
    ],
    "provenance": {
      "definition_sha256": "fixture_rule_hash",
      "graph_sha256": "fixture_graph_hash",
      "evidence_sha256": "fixture_evidence_hash"
    },
    "rules_executed": true,
    "company_queries": 0,
    "model_calls": 0,
    "source_writes": 0,
    "independently_verified": false,
    "report_sha256": "fixture_report_hash"
  },
  "monitoring:rate_requires_exposure": {
    "outcome": "rate_calculated",
    "checks": [
      {
        "check_id": "cohort",
        "status": "passed",
        "observed": "Synthetic MODEL-A cohort",
        "message": "Explicit cohort and common observation period required."
      },
      {
        "check_id": "period_start",
        "status": "passed",
        "observed": "2026-01-01",
        "message": "Explicit cohort and common observation period required."
      },
      {
        "check_id": "period_end",
        "status": "passed",
        "observed": "2026-12-31",
        "message": "Explicit cohort and common observation period required."
      },
      {
        "check_id": "coverage",
        "status": "passed",
        "observed": "complete",
        "message": "Incomplete cohort follow-up cannot establish this rate."
      },
      {
        "check_id": "counting_basis",
        "status": "passed",
        "observed": "distinct_first_failures",
        "message": "Numerator must count distinct engines with a confirmed first failure."
      },
      {
        "check_id": "confirmed_failures",
        "status": "passed",
        "observed": 5,
        "message": "Zero is valid only as a documented confirmed count."
      },
      {
        "check_id": "population_engines",
        "status": "passed",
        "observed": 100,
        "message": "At-risk population must be positive."
      },
      {
        "check_id": "exposure_hours",
        "status": "passed",
        "observed": "10000",
        "message": "Total at-risk engine-hours must be positive; one complaint hour reading is not a cohort denominator."
      },
      {
        "check_id": "count_consistency",
        "status": "passed",
        "observed": {
          "failures": 5,
          "population": 100
        },
        "message": "Distinct failed engines cannot exceed the at-risk engine population."
      },
      {
        "check_id": "period_consistency",
        "status": "passed",
        "observed": {
          "start": "2026-01-01",
          "end": "2026-12-31"
        },
        "message": "Cohort period start cannot follow period end."
      }
    ],
    "calculations": {
      "failed_engine_percentage": "5.000000",
      "first_failures_per_1000_engine_hours": "0.500000",
      "percentage_formula": "confirmed failed engines / engines at risk \u00d7 100",
      "incidence_formula": "confirmed first failures / total at-risk engine-hours \u00d7 1000",
      "rounding": "six decimal places, half-even",
      "cohort": "Synthetic MODEL-A cohort",
      "period_start": "2026-01-01",
      "period_end": "2026-12-31"
    },
    "rule_id": "monitoring:rate_requires_exposure",
    "label": "Calculate evidence-backed failure rate",
    "handler_version": "simpson-reference-execution-v1",
    "version_id": "v2",
    "graph_id": "g1",
    "subject_node_id": null,
    "change_node_id": null,
    "evidence_id": "ev2",
    "facts": {
      "cohort": {
        "value": "Synthetic MODEL-A cohort",
        "quote": "Synthetic execution evidence: {\"effectivity:recurrence_needs_evidence\": {\"applicability\": \"applies\", \"failure_date\": \"2026-06-01\", \"incorporation\": \"installed\", \"incorporation_date\": \"2026-01-01\", \"inspection_conclusion\": \"comparable_failure\", \"mechanism\": \"same\", \"physical_identity\": \"same_engine\", \"post_change_hours\": \"100\", \"required_hours\": \"100\", \"root_cause\": \"same\"}, \"failure:unconfirmed_similarity\": {\"diagnosis\": \"confirmed\", \"finding_basis\": \"inspection\", \"finding_details\": \"Inspection and pressure test identify a gasket leak.\", \"suspected_cause\": \"Gasket leak\"}, \"monitoring:rate_requires_exposure\": {\"cohort\": \"Synthetic MODEL-A cohort\", \"confirmed_failures\": 5, \"counting_basis\": \"distinct_first_failures\", \"coverage\": \"complete\", \"exposure_hours\": \"10000\", \"period_end\": \"2026-12-31\", \"period_start\": \"2026-01-01\", \"population_engines\": 100}}"
      },
      "period_start": {
        "value": "2026-01-01",
        "quote": "Synthetic execution evidence: {\"effectivity:recurrence_needs_evidence\": {\"applicability\": \"applies\", \"failure_date\": \"2026-06-01\", \"incorporation\": \"installed\", \"incorporation_date\": \"2026-01-01\", \"inspection_conclusion\": \"comparable_failure\", \"mechanism\": \"same\", \"physical_identity\": \"same_engine\", \"post_change_hours\": \"100\", \"required_hours\": \"100\", \"root_cause\": \"same\"}, \"failure:unconfirmed_similarity\": {\"diagnosis\": \"confirmed\", \"finding_basis\": \"inspection\", \"finding_details\": \"Inspection and pressure test identify a gasket leak.\", \"suspected_cause\": \"Gasket leak\"}, \"monitoring:rate_requires_exposure\": {\"cohort\": \"Synthetic MODEL-A cohort\", \"confirmed_failures\": 5, \"counting_basis\": \"distinct_first_failures\", \"coverage\": \"complete\", \"exposure_hours\": \"10000\", \"period_end\": \"2026-12-31\", \"period_start\": \"2026-01-01\", \"population_engines\": 100}}"
      },
      "period_end": {
        "value": "2026-12-31",
        "quote": "Synthetic execution evidence: {\"effectivity:recurrence_needs_evidence\": {\"applicability\": \"applies\", \"failure_date\": \"2026-06-01\", \"incorporation\": \"installed\", \"incorporation_date\": \"2026-01-01\", \"inspection_conclusion\": \"comparable_failure\", \"mechanism\": \"same\", \"physical_identity\": \"same_engine\", \"post_change_hours\": \"100\", \"required_hours\": \"100\", \"root_cause\": \"same\"}, \"failure:unconfirmed_similarity\": {\"diagnosis\": \"confirmed\", \"finding_basis\": \"inspection\", \"finding_details\": \"Inspection and pressure test identify a gasket leak.\", \"suspected_cause\": \"Gasket leak\"}, \"monitoring:rate_requires_exposure\": {\"cohort\": \"Synthetic MODEL-A cohort\", \"confirmed_failures\": 5, \"counting_basis\": \"distinct_first_failures\", \"coverage\": \"complete\", \"exposure_hours\": \"10000\", \"period_end\": \"2026-12-31\", \"period_start\": \"2026-01-01\", \"population_engines\": 100}}"
      },
      "coverage": {
        "value": "complete",
        "quote": "Synthetic execution evidence: {\"effectivity:recurrence_needs_evidence\": {\"applicability\": \"applies\", \"failure_date\": \"2026-06-01\", \"incorporation\": \"installed\", \"incorporation_date\": \"2026-01-01\", \"inspection_conclusion\": \"comparable_failure\", \"mechanism\": \"same\", \"physical_identity\": \"same_engine\", \"post_change_hours\": \"100\", \"required_hours\": \"100\", \"root_cause\": \"same\"}, \"failure:unconfirmed_similarity\": {\"diagnosis\": \"confirmed\", \"finding_basis\": \"inspection\", \"finding_details\": \"Inspection and pressure test identify a gasket leak.\", \"suspected_cause\": \"Gasket leak\"}, \"monitoring:rate_requires_exposure\": {\"cohort\": \"Synthetic MODEL-A cohort\", \"confirmed_failures\": 5, \"counting_basis\": \"distinct_first_failures\", \"coverage\": \"complete\", \"exposure_hours\": \"10000\", \"period_end\": \"2026-12-31\", \"period_start\": \"2026-01-01\", \"population_engines\": 100}}"
      },
      "counting_basis": {
        "value": "distinct_first_failures",
        "quote": "Synthetic execution evidence: {\"effectivity:recurrence_needs_evidence\": {\"applicability\": \"applies\", \"failure_date\": \"2026-06-01\", \"incorporation\": \"installed\", \"incorporation_date\": \"2026-01-01\", \"inspection_conclusion\": \"comparable_failure\", \"mechanism\": \"same\", \"physical_identity\": \"same_engine\", \"post_change_hours\": \"100\", \"required_hours\": \"100\", \"root_cause\": \"same\"}, \"failure:unconfirmed_similarity\": {\"diagnosis\": \"confirmed\", \"finding_basis\": \"inspection\", \"finding_details\": \"Inspection and pressure test identify a gasket leak.\", \"suspected_cause\": \"Gasket leak\"}, \"monitoring:rate_requires_exposure\": {\"cohort\": \"Synthetic MODEL-A cohort\", \"confirmed_failures\": 5, \"counting_basis\": \"distinct_first_failures\", \"coverage\": \"complete\", \"exposure_hours\": \"10000\", \"period_end\": \"2026-12-31\", \"period_start\": \"2026-01-01\", \"population_engines\": 100}}"
      },
      "confirmed_failures": {
        "value": 5,
        "quote": "Synthetic execution evidence: {\"effectivity:recurrence_needs_evidence\": {\"applicability\": \"applies\", \"failure_date\": \"2026-06-01\", \"incorporation\": \"installed\", \"incorporation_date\": \"2026-01-01\", \"inspection_conclusion\": \"comparable_failure\", \"mechanism\": \"same\", \"physical_identity\": \"same_engine\", \"post_change_hours\": \"100\", \"required_hours\": \"100\", \"root_cause\": \"same\"}, \"failure:unconfirmed_similarity\": {\"diagnosis\": \"confirmed\", \"finding_basis\": \"inspection\", \"finding_details\": \"Inspection and pressure test identify a gasket leak.\", \"suspected_cause\": \"Gasket leak\"}, \"monitoring:rate_requires_exposure\": {\"cohort\": \"Synthetic MODEL-A cohort\", \"confirmed_failures\": 5, \"counting_basis\": \"distinct_first_failures\", \"coverage\": \"complete\", \"exposure_hours\": \"10000\", \"period_end\": \"2026-12-31\", \"period_start\": \"2026-01-01\", \"population_engines\": 100}}"
      },
      "population_engines": {
        "value": 100,
        "quote": "Synthetic execution evidence: {\"effectivity:recurrence_needs_evidence\": {\"applicability\": \"applies\", \"failure_date\": \"2026-06-01\", \"incorporation\": \"installed\", \"incorporation_date\": \"2026-01-01\", \"inspection_conclusion\": \"comparable_failure\", \"mechanism\": \"same\", \"physical_identity\": \"same_engine\", \"post_change_hours\": \"100\", \"required_hours\": \"100\", \"root_cause\": \"same\"}, \"failure:unconfirmed_similarity\": {\"diagnosis\": \"confirmed\", \"finding_basis\": \"inspection\", \"finding_details\": \"Inspection and pressure test identify a gasket leak.\", \"suspected_cause\": \"Gasket leak\"}, \"monitoring:rate_requires_exposure\": {\"cohort\": \"Synthetic MODEL-A cohort\", \"confirmed_failures\": 5, \"counting_basis\": \"distinct_first_failures\", \"coverage\": \"complete\", \"exposure_hours\": \"10000\", \"period_end\": \"2026-12-31\", \"period_start\": \"2026-01-01\", \"population_engines\": 100}}"
      },
      "exposure_hours": {
        "value": "10000",
        "quote": "Synthetic execution evidence: {\"effectivity:recurrence_needs_evidence\": {\"applicability\": \"applies\", \"failure_date\": \"2026-06-01\", \"incorporation\": \"installed\", \"incorporation_date\": \"2026-01-01\", \"inspection_conclusion\": \"comparable_failure\", \"mechanism\": \"same\", \"physical_identity\": \"same_engine\", \"post_change_hours\": \"100\", \"required_hours\": \"100\", \"root_cause\": \"same\"}, \"failure:unconfirmed_similarity\": {\"diagnosis\": \"confirmed\", \"finding_basis\": \"inspection\", \"finding_details\": \"Inspection and pressure test identify a gasket leak.\", \"suspected_cause\": \"Gasket leak\"}, \"monitoring:rate_requires_exposure\": {\"cohort\": \"Synthetic MODEL-A cohort\", \"confirmed_failures\": 5, \"counting_basis\": \"distinct_first_failures\", \"coverage\": \"complete\", \"exposure_hours\": \"10000\", \"period_end\": \"2026-12-31\", \"period_start\": \"2026-01-01\", \"population_engines\": 100}}"
      }
    },
    "source": {
      "source_id": "execution_source",
      "title": "Synthetic execution evidence",
      "sha256": "fixture_source_hash"
    },
    "observations": [],
    "qualification": "Computed from selected source-cited assertions, not independently verified.",
    "limits": [
      "No source/model call or business record write."
    ],
    "provenance": {
      "definition_sha256": "fixture_rule_hash",
      "graph_sha256": "fixture_graph_hash",
      "evidence_sha256": "fixture_evidence_hash"
    },
    "rules_executed": true,
    "company_queries": 0,
    "model_calls": 0,
    "source_writes": 0,
    "independently_verified": false,
    "report_sha256": "fixture_report_hash"
  }
};
const evidence={
  "failure:unconfirmed_similarity": {
    "evidence_id": "ev0",
    "version_id": "v2",
    "graph_id": "g1",
    "rule_id": "failure:unconfirmed_similarity",
    "subject_node_id": "node1",
    "change_node_id": null,
    "revision": 1,
    "created_at": "2026-11-01",
    "source_id": "execution_source",
    "source": {
      "source_id": "execution_source",
      "title": "Synthetic execution evidence",
      "kind": "evidence",
      "module_ids": [
        "failure",
        "effectivity",
        "monitoring"
      ],
      "text": "Synthetic execution evidence: {\"effectivity:recurrence_needs_evidence\": {\"applicability\": \"applies\", \"failure_date\": \"2026-06-01\", \"incorporation\": \"installed\", \"incorporation_date\": \"2026-01-01\", \"inspection_conclusion\": \"comparable_failure\", \"mechanism\": \"same\", \"physical_identity\": \"same_engine\", \"post_change_hours\": \"100\", \"required_hours\": \"100\", \"root_cause\": \"same\"}, \"failure:unconfirmed_similarity\": {\"diagnosis\": \"confirmed\", \"finding_basis\": \"inspection\", \"finding_details\": \"Inspection and pressure test identify a gasket leak.\", \"suspected_cause\": \"Gasket leak\"}, \"monitoring:rate_requires_exposure\": {\"cohort\": \"Synthetic MODEL-A cohort\", \"confirmed_failures\": 5, \"counting_basis\": \"distinct_first_failures\", \"coverage\": \"complete\", \"exposure_hours\": \"10000\", \"period_end\": \"2026-12-31\", \"period_start\": \"2026-01-01\", \"population_engines\": 100}}",
      "sha256": "fixture_source_hash",
      "origin": "owner_supplied"
    },
    "facts": {
      "suspected_cause": {
        "value": "Gasket leak",
        "quote": "Synthetic execution evidence: {\"effectivity:recurrence_needs_evidence\": {\"applicability\": \"applies\", \"failure_date\": \"2026-06-01\", \"incorporation\": \"installed\", \"incorporation_date\": \"2026-01-01\", \"inspection_conclusion\": \"comparable_failure\", \"mechanism\": \"same\", \"physical_identity\": \"same_engine\", \"post_change_hours\": \"100\", \"required_hours\": \"100\", \"root_cause\": \"same\"}, \"failure:unconfirmed_similarity\": {\"diagnosis\": \"confirmed\", \"finding_basis\": \"inspection\", \"finding_details\": \"Inspection and pressure test identify a gasket leak.\", \"suspected_cause\": \"Gasket leak\"}, \"monitoring:rate_requires_exposure\": {\"cohort\": \"Synthetic MODEL-A cohort\", \"confirmed_failures\": 5, \"counting_basis\": \"distinct_first_failures\", \"coverage\": \"complete\", \"exposure_hours\": \"10000\", \"period_end\": \"2026-12-31\", \"period_start\": \"2026-01-01\", \"population_engines\": 100}}"
      },
      "finding_basis": {
        "value": "inspection",
        "quote": "Synthetic execution evidence: {\"effectivity:recurrence_needs_evidence\": {\"applicability\": \"applies\", \"failure_date\": \"2026-06-01\", \"incorporation\": \"installed\", \"incorporation_date\": \"2026-01-01\", \"inspection_conclusion\": \"comparable_failure\", \"mechanism\": \"same\", \"physical_identity\": \"same_engine\", \"post_change_hours\": \"100\", \"required_hours\": \"100\", \"root_cause\": \"same\"}, \"failure:unconfirmed_similarity\": {\"diagnosis\": \"confirmed\", \"finding_basis\": \"inspection\", \"finding_details\": \"Inspection and pressure test identify a gasket leak.\", \"suspected_cause\": \"Gasket leak\"}, \"monitoring:rate_requires_exposure\": {\"cohort\": \"Synthetic MODEL-A cohort\", \"confirmed_failures\": 5, \"counting_basis\": \"distinct_first_failures\", \"coverage\": \"complete\", \"exposure_hours\": \"10000\", \"period_end\": \"2026-12-31\", \"period_start\": \"2026-01-01\", \"population_engines\": 100}}"
      },
      "diagnosis": {
        "value": "confirmed",
        "quote": "Synthetic execution evidence: {\"effectivity:recurrence_needs_evidence\": {\"applicability\": \"applies\", \"failure_date\": \"2026-06-01\", \"incorporation\": \"installed\", \"incorporation_date\": \"2026-01-01\", \"inspection_conclusion\": \"comparable_failure\", \"mechanism\": \"same\", \"physical_identity\": \"same_engine\", \"post_change_hours\": \"100\", \"required_hours\": \"100\", \"root_cause\": \"same\"}, \"failure:unconfirmed_similarity\": {\"diagnosis\": \"confirmed\", \"finding_basis\": \"inspection\", \"finding_details\": \"Inspection and pressure test identify a gasket leak.\", \"suspected_cause\": \"Gasket leak\"}, \"monitoring:rate_requires_exposure\": {\"cohort\": \"Synthetic MODEL-A cohort\", \"confirmed_failures\": 5, \"counting_basis\": \"distinct_first_failures\", \"coverage\": \"complete\", \"exposure_hours\": \"10000\", \"period_end\": \"2026-12-31\", \"period_start\": \"2026-01-01\", \"population_engines\": 100}}"
      },
      "finding_details": {
        "value": "Inspection and pressure test identify a gasket leak.",
        "quote": "Synthetic execution evidence: {\"effectivity:recurrence_needs_evidence\": {\"applicability\": \"applies\", \"failure_date\": \"2026-06-01\", \"incorporation\": \"installed\", \"incorporation_date\": \"2026-01-01\", \"inspection_conclusion\": \"comparable_failure\", \"mechanism\": \"same\", \"physical_identity\": \"same_engine\", \"post_change_hours\": \"100\", \"required_hours\": \"100\", \"root_cause\": \"same\"}, \"failure:unconfirmed_similarity\": {\"diagnosis\": \"confirmed\", \"finding_basis\": \"inspection\", \"finding_details\": \"Inspection and pressure test identify a gasket leak.\", \"suspected_cause\": \"Gasket leak\"}, \"monitoring:rate_requires_exposure\": {\"cohort\": \"Synthetic MODEL-A cohort\", \"confirmed_failures\": 5, \"counting_basis\": \"distinct_first_failures\", \"coverage\": \"complete\", \"exposure_hours\": \"10000\", \"period_end\": \"2026-12-31\", \"period_start\": \"2026-01-01\", \"population_engines\": 100}}"
      }
    },
    "qualification": "Source-cited synthetic assertions, not independently verified.",
    "sha256": "fixture_evidence_hash"
  },
  "effectivity:recurrence_needs_evidence": {
    "evidence_id": "ev1",
    "version_id": "v2",
    "graph_id": "g1",
    "rule_id": "effectivity:recurrence_needs_evidence",
    "subject_node_id": "node1",
    "change_node_id": "change1",
    "revision": 1,
    "created_at": "2026-11-01",
    "source_id": "execution_source",
    "source": {
      "source_id": "execution_source",
      "title": "Synthetic execution evidence",
      "kind": "evidence",
      "module_ids": [
        "failure",
        "effectivity",
        "monitoring"
      ],
      "text": "Synthetic execution evidence: {\"effectivity:recurrence_needs_evidence\": {\"applicability\": \"applies\", \"failure_date\": \"2026-06-01\", \"incorporation\": \"installed\", \"incorporation_date\": \"2026-01-01\", \"inspection_conclusion\": \"comparable_failure\", \"mechanism\": \"same\", \"physical_identity\": \"same_engine\", \"post_change_hours\": \"100\", \"required_hours\": \"100\", \"root_cause\": \"same\"}, \"failure:unconfirmed_similarity\": {\"diagnosis\": \"confirmed\", \"finding_basis\": \"inspection\", \"finding_details\": \"Inspection and pressure test identify a gasket leak.\", \"suspected_cause\": \"Gasket leak\"}, \"monitoring:rate_requires_exposure\": {\"cohort\": \"Synthetic MODEL-A cohort\", \"confirmed_failures\": 5, \"counting_basis\": \"distinct_first_failures\", \"coverage\": \"complete\", \"exposure_hours\": \"10000\", \"period_end\": \"2026-12-31\", \"period_start\": \"2026-01-01\", \"population_engines\": 100}}",
      "sha256": "fixture_source_hash",
      "origin": "owner_supplied"
    },
    "facts": {
      "physical_identity": {
        "value": "same_engine",
        "quote": "Synthetic execution evidence: {\"effectivity:recurrence_needs_evidence\": {\"applicability\": \"applies\", \"failure_date\": \"2026-06-01\", \"incorporation\": \"installed\", \"incorporation_date\": \"2026-01-01\", \"inspection_conclusion\": \"comparable_failure\", \"mechanism\": \"same\", \"physical_identity\": \"same_engine\", \"post_change_hours\": \"100\", \"required_hours\": \"100\", \"root_cause\": \"same\"}, \"failure:unconfirmed_similarity\": {\"diagnosis\": \"confirmed\", \"finding_basis\": \"inspection\", \"finding_details\": \"Inspection and pressure test identify a gasket leak.\", \"suspected_cause\": \"Gasket leak\"}, \"monitoring:rate_requires_exposure\": {\"cohort\": \"Synthetic MODEL-A cohort\", \"confirmed_failures\": 5, \"counting_basis\": \"distinct_first_failures\", \"coverage\": \"complete\", \"exposure_hours\": \"10000\", \"period_end\": \"2026-12-31\", \"period_start\": \"2026-01-01\", \"population_engines\": 100}}"
      },
      "applicability": {
        "value": "applies",
        "quote": "Synthetic execution evidence: {\"effectivity:recurrence_needs_evidence\": {\"applicability\": \"applies\", \"failure_date\": \"2026-06-01\", \"incorporation\": \"installed\", \"incorporation_date\": \"2026-01-01\", \"inspection_conclusion\": \"comparable_failure\", \"mechanism\": \"same\", \"physical_identity\": \"same_engine\", \"post_change_hours\": \"100\", \"required_hours\": \"100\", \"root_cause\": \"same\"}, \"failure:unconfirmed_similarity\": {\"diagnosis\": \"confirmed\", \"finding_basis\": \"inspection\", \"finding_details\": \"Inspection and pressure test identify a gasket leak.\", \"suspected_cause\": \"Gasket leak\"}, \"monitoring:rate_requires_exposure\": {\"cohort\": \"Synthetic MODEL-A cohort\", \"confirmed_failures\": 5, \"counting_basis\": \"distinct_first_failures\", \"coverage\": \"complete\", \"exposure_hours\": \"10000\", \"period_end\": \"2026-12-31\", \"period_start\": \"2026-01-01\", \"population_engines\": 100}}"
      },
      "incorporation": {
        "value": "installed",
        "quote": "Synthetic execution evidence: {\"effectivity:recurrence_needs_evidence\": {\"applicability\": \"applies\", \"failure_date\": \"2026-06-01\", \"incorporation\": \"installed\", \"incorporation_date\": \"2026-01-01\", \"inspection_conclusion\": \"comparable_failure\", \"mechanism\": \"same\", \"physical_identity\": \"same_engine\", \"post_change_hours\": \"100\", \"required_hours\": \"100\", \"root_cause\": \"same\"}, \"failure:unconfirmed_similarity\": {\"diagnosis\": \"confirmed\", \"finding_basis\": \"inspection\", \"finding_details\": \"Inspection and pressure test identify a gasket leak.\", \"suspected_cause\": \"Gasket leak\"}, \"monitoring:rate_requires_exposure\": {\"cohort\": \"Synthetic MODEL-A cohort\", \"confirmed_failures\": 5, \"counting_basis\": \"distinct_first_failures\", \"coverage\": \"complete\", \"exposure_hours\": \"10000\", \"period_end\": \"2026-12-31\", \"period_start\": \"2026-01-01\", \"population_engines\": 100}}"
      },
      "mechanism": {
        "value": "same",
        "quote": "Synthetic execution evidence: {\"effectivity:recurrence_needs_evidence\": {\"applicability\": \"applies\", \"failure_date\": \"2026-06-01\", \"incorporation\": \"installed\", \"incorporation_date\": \"2026-01-01\", \"inspection_conclusion\": \"comparable_failure\", \"mechanism\": \"same\", \"physical_identity\": \"same_engine\", \"post_change_hours\": \"100\", \"required_hours\": \"100\", \"root_cause\": \"same\"}, \"failure:unconfirmed_similarity\": {\"diagnosis\": \"confirmed\", \"finding_basis\": \"inspection\", \"finding_details\": \"Inspection and pressure test identify a gasket leak.\", \"suspected_cause\": \"Gasket leak\"}, \"monitoring:rate_requires_exposure\": {\"cohort\": \"Synthetic MODEL-A cohort\", \"confirmed_failures\": 5, \"counting_basis\": \"distinct_first_failures\", \"coverage\": \"complete\", \"exposure_hours\": \"10000\", \"period_end\": \"2026-12-31\", \"period_start\": \"2026-01-01\", \"population_engines\": 100}}"
      },
      "root_cause": {
        "value": "same",
        "quote": "Synthetic execution evidence: {\"effectivity:recurrence_needs_evidence\": {\"applicability\": \"applies\", \"failure_date\": \"2026-06-01\", \"incorporation\": \"installed\", \"incorporation_date\": \"2026-01-01\", \"inspection_conclusion\": \"comparable_failure\", \"mechanism\": \"same\", \"physical_identity\": \"same_engine\", \"post_change_hours\": \"100\", \"required_hours\": \"100\", \"root_cause\": \"same\"}, \"failure:unconfirmed_similarity\": {\"diagnosis\": \"confirmed\", \"finding_basis\": \"inspection\", \"finding_details\": \"Inspection and pressure test identify a gasket leak.\", \"suspected_cause\": \"Gasket leak\"}, \"monitoring:rate_requires_exposure\": {\"cohort\": \"Synthetic MODEL-A cohort\", \"confirmed_failures\": 5, \"counting_basis\": \"distinct_first_failures\", \"coverage\": \"complete\", \"exposure_hours\": \"10000\", \"period_end\": \"2026-12-31\", \"period_start\": \"2026-01-01\", \"population_engines\": 100}}"
      },
      "inspection_conclusion": {
        "value": "comparable_failure",
        "quote": "Synthetic execution evidence: {\"effectivity:recurrence_needs_evidence\": {\"applicability\": \"applies\", \"failure_date\": \"2026-06-01\", \"incorporation\": \"installed\", \"incorporation_date\": \"2026-01-01\", \"inspection_conclusion\": \"comparable_failure\", \"mechanism\": \"same\", \"physical_identity\": \"same_engine\", \"post_change_hours\": \"100\", \"required_hours\": \"100\", \"root_cause\": \"same\"}, \"failure:unconfirmed_similarity\": {\"diagnosis\": \"confirmed\", \"finding_basis\": \"inspection\", \"finding_details\": \"Inspection and pressure test identify a gasket leak.\", \"suspected_cause\": \"Gasket leak\"}, \"monitoring:rate_requires_exposure\": {\"cohort\": \"Synthetic MODEL-A cohort\", \"confirmed_failures\": 5, \"counting_basis\": \"distinct_first_failures\", \"coverage\": \"complete\", \"exposure_hours\": \"10000\", \"period_end\": \"2026-12-31\", \"period_start\": \"2026-01-01\", \"population_engines\": 100}}"
      },
      "incorporation_date": {
        "value": "2026-01-01",
        "quote": "Synthetic execution evidence: {\"effectivity:recurrence_needs_evidence\": {\"applicability\": \"applies\", \"failure_date\": \"2026-06-01\", \"incorporation\": \"installed\", \"incorporation_date\": \"2026-01-01\", \"inspection_conclusion\": \"comparable_failure\", \"mechanism\": \"same\", \"physical_identity\": \"same_engine\", \"post_change_hours\": \"100\", \"required_hours\": \"100\", \"root_cause\": \"same\"}, \"failure:unconfirmed_similarity\": {\"diagnosis\": \"confirmed\", \"finding_basis\": \"inspection\", \"finding_details\": \"Inspection and pressure test identify a gasket leak.\", \"suspected_cause\": \"Gasket leak\"}, \"monitoring:rate_requires_exposure\": {\"cohort\": \"Synthetic MODEL-A cohort\", \"confirmed_failures\": 5, \"counting_basis\": \"distinct_first_failures\", \"coverage\": \"complete\", \"exposure_hours\": \"10000\", \"period_end\": \"2026-12-31\", \"period_start\": \"2026-01-01\", \"population_engines\": 100}}"
      },
      "failure_date": {
        "value": "2026-06-01",
        "quote": "Synthetic execution evidence: {\"effectivity:recurrence_needs_evidence\": {\"applicability\": \"applies\", \"failure_date\": \"2026-06-01\", \"incorporation\": \"installed\", \"incorporation_date\": \"2026-01-01\", \"inspection_conclusion\": \"comparable_failure\", \"mechanism\": \"same\", \"physical_identity\": \"same_engine\", \"post_change_hours\": \"100\", \"required_hours\": \"100\", \"root_cause\": \"same\"}, \"failure:unconfirmed_similarity\": {\"diagnosis\": \"confirmed\", \"finding_basis\": \"inspection\", \"finding_details\": \"Inspection and pressure test identify a gasket leak.\", \"suspected_cause\": \"Gasket leak\"}, \"monitoring:rate_requires_exposure\": {\"cohort\": \"Synthetic MODEL-A cohort\", \"confirmed_failures\": 5, \"counting_basis\": \"distinct_first_failures\", \"coverage\": \"complete\", \"exposure_hours\": \"10000\", \"period_end\": \"2026-12-31\", \"period_start\": \"2026-01-01\", \"population_engines\": 100}}"
      },
      "post_change_hours": {
        "value": "100",
        "quote": "Synthetic execution evidence: {\"effectivity:recurrence_needs_evidence\": {\"applicability\": \"applies\", \"failure_date\": \"2026-06-01\", \"incorporation\": \"installed\", \"incorporation_date\": \"2026-01-01\", \"inspection_conclusion\": \"comparable_failure\", \"mechanism\": \"same\", \"physical_identity\": \"same_engine\", \"post_change_hours\": \"100\", \"required_hours\": \"100\", \"root_cause\": \"same\"}, \"failure:unconfirmed_similarity\": {\"diagnosis\": \"confirmed\", \"finding_basis\": \"inspection\", \"finding_details\": \"Inspection and pressure test identify a gasket leak.\", \"suspected_cause\": \"Gasket leak\"}, \"monitoring:rate_requires_exposure\": {\"cohort\": \"Synthetic MODEL-A cohort\", \"confirmed_failures\": 5, \"counting_basis\": \"distinct_first_failures\", \"coverage\": \"complete\", \"exposure_hours\": \"10000\", \"period_end\": \"2026-12-31\", \"period_start\": \"2026-01-01\", \"population_engines\": 100}}"
      },
      "required_hours": {
        "value": "100",
        "quote": "Synthetic execution evidence: {\"effectivity:recurrence_needs_evidence\": {\"applicability\": \"applies\", \"failure_date\": \"2026-06-01\", \"incorporation\": \"installed\", \"incorporation_date\": \"2026-01-01\", \"inspection_conclusion\": \"comparable_failure\", \"mechanism\": \"same\", \"physical_identity\": \"same_engine\", \"post_change_hours\": \"100\", \"required_hours\": \"100\", \"root_cause\": \"same\"}, \"failure:unconfirmed_similarity\": {\"diagnosis\": \"confirmed\", \"finding_basis\": \"inspection\", \"finding_details\": \"Inspection and pressure test identify a gasket leak.\", \"suspected_cause\": \"Gasket leak\"}, \"monitoring:rate_requires_exposure\": {\"cohort\": \"Synthetic MODEL-A cohort\", \"confirmed_failures\": 5, \"counting_basis\": \"distinct_first_failures\", \"coverage\": \"complete\", \"exposure_hours\": \"10000\", \"period_end\": \"2026-12-31\", \"period_start\": \"2026-01-01\", \"population_engines\": 100}}"
      }
    },
    "qualification": "Source-cited synthetic assertions, not independently verified.",
    "sha256": "fixture_evidence_hash"
  },
  "monitoring:rate_requires_exposure": {
    "evidence_id": "ev2",
    "version_id": "v2",
    "graph_id": "g1",
    "rule_id": "monitoring:rate_requires_exposure",
    "subject_node_id": null,
    "change_node_id": null,
    "revision": 1,
    "created_at": "2026-11-01",
    "source_id": "execution_source",
    "source": {
      "source_id": "execution_source",
      "title": "Synthetic execution evidence",
      "kind": "evidence",
      "module_ids": [
        "failure",
        "effectivity",
        "monitoring"
      ],
      "text": "Synthetic execution evidence: {\"effectivity:recurrence_needs_evidence\": {\"applicability\": \"applies\", \"failure_date\": \"2026-06-01\", \"incorporation\": \"installed\", \"incorporation_date\": \"2026-01-01\", \"inspection_conclusion\": \"comparable_failure\", \"mechanism\": \"same\", \"physical_identity\": \"same_engine\", \"post_change_hours\": \"100\", \"required_hours\": \"100\", \"root_cause\": \"same\"}, \"failure:unconfirmed_similarity\": {\"diagnosis\": \"confirmed\", \"finding_basis\": \"inspection\", \"finding_details\": \"Inspection and pressure test identify a gasket leak.\", \"suspected_cause\": \"Gasket leak\"}, \"monitoring:rate_requires_exposure\": {\"cohort\": \"Synthetic MODEL-A cohort\", \"confirmed_failures\": 5, \"counting_basis\": \"distinct_first_failures\", \"coverage\": \"complete\", \"exposure_hours\": \"10000\", \"period_end\": \"2026-12-31\", \"period_start\": \"2026-01-01\", \"population_engines\": 100}}",
      "sha256": "fixture_source_hash",
      "origin": "owner_supplied"
    },
    "facts": {
      "cohort": {
        "value": "Synthetic MODEL-A cohort",
        "quote": "Synthetic execution evidence: {\"effectivity:recurrence_needs_evidence\": {\"applicability\": \"applies\", \"failure_date\": \"2026-06-01\", \"incorporation\": \"installed\", \"incorporation_date\": \"2026-01-01\", \"inspection_conclusion\": \"comparable_failure\", \"mechanism\": \"same\", \"physical_identity\": \"same_engine\", \"post_change_hours\": \"100\", \"required_hours\": \"100\", \"root_cause\": \"same\"}, \"failure:unconfirmed_similarity\": {\"diagnosis\": \"confirmed\", \"finding_basis\": \"inspection\", \"finding_details\": \"Inspection and pressure test identify a gasket leak.\", \"suspected_cause\": \"Gasket leak\"}, \"monitoring:rate_requires_exposure\": {\"cohort\": \"Synthetic MODEL-A cohort\", \"confirmed_failures\": 5, \"counting_basis\": \"distinct_first_failures\", \"coverage\": \"complete\", \"exposure_hours\": \"10000\", \"period_end\": \"2026-12-31\", \"period_start\": \"2026-01-01\", \"population_engines\": 100}}"
      },
      "period_start": {
        "value": "2026-01-01",
        "quote": "Synthetic execution evidence: {\"effectivity:recurrence_needs_evidence\": {\"applicability\": \"applies\", \"failure_date\": \"2026-06-01\", \"incorporation\": \"installed\", \"incorporation_date\": \"2026-01-01\", \"inspection_conclusion\": \"comparable_failure\", \"mechanism\": \"same\", \"physical_identity\": \"same_engine\", \"post_change_hours\": \"100\", \"required_hours\": \"100\", \"root_cause\": \"same\"}, \"failure:unconfirmed_similarity\": {\"diagnosis\": \"confirmed\", \"finding_basis\": \"inspection\", \"finding_details\": \"Inspection and pressure test identify a gasket leak.\", \"suspected_cause\": \"Gasket leak\"}, \"monitoring:rate_requires_exposure\": {\"cohort\": \"Synthetic MODEL-A cohort\", \"confirmed_failures\": 5, \"counting_basis\": \"distinct_first_failures\", \"coverage\": \"complete\", \"exposure_hours\": \"10000\", \"period_end\": \"2026-12-31\", \"period_start\": \"2026-01-01\", \"population_engines\": 100}}"
      },
      "period_end": {
        "value": "2026-12-31",
        "quote": "Synthetic execution evidence: {\"effectivity:recurrence_needs_evidence\": {\"applicability\": \"applies\", \"failure_date\": \"2026-06-01\", \"incorporation\": \"installed\", \"incorporation_date\": \"2026-01-01\", \"inspection_conclusion\": \"comparable_failure\", \"mechanism\": \"same\", \"physical_identity\": \"same_engine\", \"post_change_hours\": \"100\", \"required_hours\": \"100\", \"root_cause\": \"same\"}, \"failure:unconfirmed_similarity\": {\"diagnosis\": \"confirmed\", \"finding_basis\": \"inspection\", \"finding_details\": \"Inspection and pressure test identify a gasket leak.\", \"suspected_cause\": \"Gasket leak\"}, \"monitoring:rate_requires_exposure\": {\"cohort\": \"Synthetic MODEL-A cohort\", \"confirmed_failures\": 5, \"counting_basis\": \"distinct_first_failures\", \"coverage\": \"complete\", \"exposure_hours\": \"10000\", \"period_end\": \"2026-12-31\", \"period_start\": \"2026-01-01\", \"population_engines\": 100}}"
      },
      "coverage": {
        "value": "complete",
        "quote": "Synthetic execution evidence: {\"effectivity:recurrence_needs_evidence\": {\"applicability\": \"applies\", \"failure_date\": \"2026-06-01\", \"incorporation\": \"installed\", \"incorporation_date\": \"2026-01-01\", \"inspection_conclusion\": \"comparable_failure\", \"mechanism\": \"same\", \"physical_identity\": \"same_engine\", \"post_change_hours\": \"100\", \"required_hours\": \"100\", \"root_cause\": \"same\"}, \"failure:unconfirmed_similarity\": {\"diagnosis\": \"confirmed\", \"finding_basis\": \"inspection\", \"finding_details\": \"Inspection and pressure test identify a gasket leak.\", \"suspected_cause\": \"Gasket leak\"}, \"monitoring:rate_requires_exposure\": {\"cohort\": \"Synthetic MODEL-A cohort\", \"confirmed_failures\": 5, \"counting_basis\": \"distinct_first_failures\", \"coverage\": \"complete\", \"exposure_hours\": \"10000\", \"period_end\": \"2026-12-31\", \"period_start\": \"2026-01-01\", \"population_engines\": 100}}"
      },
      "counting_basis": {
        "value": "distinct_first_failures",
        "quote": "Synthetic execution evidence: {\"effectivity:recurrence_needs_evidence\": {\"applicability\": \"applies\", \"failure_date\": \"2026-06-01\", \"incorporation\": \"installed\", \"incorporation_date\": \"2026-01-01\", \"inspection_conclusion\": \"comparable_failure\", \"mechanism\": \"same\", \"physical_identity\": \"same_engine\", \"post_change_hours\": \"100\", \"required_hours\": \"100\", \"root_cause\": \"same\"}, \"failure:unconfirmed_similarity\": {\"diagnosis\": \"confirmed\", \"finding_basis\": \"inspection\", \"finding_details\": \"Inspection and pressure test identify a gasket leak.\", \"suspected_cause\": \"Gasket leak\"}, \"monitoring:rate_requires_exposure\": {\"cohort\": \"Synthetic MODEL-A cohort\", \"confirmed_failures\": 5, \"counting_basis\": \"distinct_first_failures\", \"coverage\": \"complete\", \"exposure_hours\": \"10000\", \"period_end\": \"2026-12-31\", \"period_start\": \"2026-01-01\", \"population_engines\": 100}}"
      },
      "confirmed_failures": {
        "value": 5,
        "quote": "Synthetic execution evidence: {\"effectivity:recurrence_needs_evidence\": {\"applicability\": \"applies\", \"failure_date\": \"2026-06-01\", \"incorporation\": \"installed\", \"incorporation_date\": \"2026-01-01\", \"inspection_conclusion\": \"comparable_failure\", \"mechanism\": \"same\", \"physical_identity\": \"same_engine\", \"post_change_hours\": \"100\", \"required_hours\": \"100\", \"root_cause\": \"same\"}, \"failure:unconfirmed_similarity\": {\"diagnosis\": \"confirmed\", \"finding_basis\": \"inspection\", \"finding_details\": \"Inspection and pressure test identify a gasket leak.\", \"suspected_cause\": \"Gasket leak\"}, \"monitoring:rate_requires_exposure\": {\"cohort\": \"Synthetic MODEL-A cohort\", \"confirmed_failures\": 5, \"counting_basis\": \"distinct_first_failures\", \"coverage\": \"complete\", \"exposure_hours\": \"10000\", \"period_end\": \"2026-12-31\", \"period_start\": \"2026-01-01\", \"population_engines\": 100}}"
      },
      "population_engines": {
        "value": 100,
        "quote": "Synthetic execution evidence: {\"effectivity:recurrence_needs_evidence\": {\"applicability\": \"applies\", \"failure_date\": \"2026-06-01\", \"incorporation\": \"installed\", \"incorporation_date\": \"2026-01-01\", \"inspection_conclusion\": \"comparable_failure\", \"mechanism\": \"same\", \"physical_identity\": \"same_engine\", \"post_change_hours\": \"100\", \"required_hours\": \"100\", \"root_cause\": \"same\"}, \"failure:unconfirmed_similarity\": {\"diagnosis\": \"confirmed\", \"finding_basis\": \"inspection\", \"finding_details\": \"Inspection and pressure test identify a gasket leak.\", \"suspected_cause\": \"Gasket leak\"}, \"monitoring:rate_requires_exposure\": {\"cohort\": \"Synthetic MODEL-A cohort\", \"confirmed_failures\": 5, \"counting_basis\": \"distinct_first_failures\", \"coverage\": \"complete\", \"exposure_hours\": \"10000\", \"period_end\": \"2026-12-31\", \"period_start\": \"2026-01-01\", \"population_engines\": 100}}"
      },
      "exposure_hours": {
        "value": "10000",
        "quote": "Synthetic execution evidence: {\"effectivity:recurrence_needs_evidence\": {\"applicability\": \"applies\", \"failure_date\": \"2026-06-01\", \"incorporation\": \"installed\", \"incorporation_date\": \"2026-01-01\", \"inspection_conclusion\": \"comparable_failure\", \"mechanism\": \"same\", \"physical_identity\": \"same_engine\", \"post_change_hours\": \"100\", \"required_hours\": \"100\", \"root_cause\": \"same\"}, \"failure:unconfirmed_similarity\": {\"diagnosis\": \"confirmed\", \"finding_basis\": \"inspection\", \"finding_details\": \"Inspection and pressure test identify a gasket leak.\", \"suspected_cause\": \"Gasket leak\"}, \"monitoring:rate_requires_exposure\": {\"cohort\": \"Synthetic MODEL-A cohort\", \"confirmed_failures\": 5, \"counting_basis\": \"distinct_first_failures\", \"coverage\": \"complete\", \"exposure_hours\": \"10000\", \"period_end\": \"2026-12-31\", \"period_start\": \"2026-01-01\", \"population_engines\": 100}}"
      }
    },
    "qualification": "Source-cited synthetic assertions, not independently verified.",
    "sha256": "fixture_evidence_hash"
  }
};
export const rateRule='monitoring:rate_requires_exposure';
export function executionResult(id=rateRule,complete=true){const value=structuredClone(reports[id as keyof typeof reports]);if(!complete){return businessRuleExecutionResultSchema.parse({...value,outcome:'insufficient_evidence',facts:{},source:null,evidence_id:null,calculations:{},checks:value.checks.map(c=>({...c,status:'unknown',observed:null})),provenance:{...value.provenance,evidence_sha256:null}});}return businessRuleExecutionResultSchema.parse(value);}
export function executionEvidence(id=rateRule){return businessRuleEvidenceSchema.parse(structuredClone(evidence[id as keyof typeof evidence]));}
