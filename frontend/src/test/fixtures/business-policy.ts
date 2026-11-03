import {businessPolicySchema,businessPolicyListSchema,businessPolicyComparisonSchema} from '../../api/business-ontology';
// Synthetic policy fixture; never a current Simpson policy.
const fixture={
  "policy": {
    "policy_key": "fixture-policy",
    "title": "Fixture policy draft",
    "source_id": "policy_source_fixture",
    "clauses": {
      "source_version": {
        "value": "V1",
        "quote": "Fixture policy version V1. Effective 2026-01-01 through 2026-12-31, inclusive, assessed on assessment date. OEM reference o1; engine model M. Sale coverage 12 months. Invoice coverage 18 months. Operating-hour limit 1000. Coverage limits include the boundary. Exclusions require evidence; missing exclusion inputs require review. Fixture calculation: sale and hours, assessment date, clamped calendar-month anniversary, inclusive period and hours. Required exclusion code misuse_check."
      },
      "effective_from": {
        "value": "2026-01-01",
        "quote": "Fixture policy version V1. Effective 2026-01-01 through 2026-12-31, inclusive, assessed on assessment date. OEM reference o1; engine model M. Sale coverage 12 months. Invoice coverage 18 months. Operating-hour limit 1000. Coverage limits include the boundary. Exclusions require evidence; missing exclusion inputs require review. Fixture calculation: sale and hours, assessment date, clamped calendar-month anniversary, inclusive period and hours. Required exclusion code misuse_check."
      },
      "effective_to": {
        "value": "2026-12-31",
        "quote": "Fixture policy version V1. Effective 2026-01-01 through 2026-12-31, inclusive, assessed on assessment date. OEM reference o1; engine model M. Sale coverage 12 months. Invoice coverage 18 months. Operating-hour limit 1000. Coverage limits include the boundary. Exclusions require evidence; missing exclusion inputs require review. Fixture calculation: sale and hours, assessment date, clamped calendar-month anniversary, inclusive period and hours. Required exclusion code misuse_check."
      },
      "oem_references": {
        "value": [
          "o1"
        ],
        "quote": "Fixture policy version V1. Effective 2026-01-01 through 2026-12-31, inclusive, assessed on assessment date. OEM reference o1; engine model M. Sale coverage 12 months. Invoice coverage 18 months. Operating-hour limit 1000. Coverage limits include the boundary. Exclusions require evidence; missing exclusion inputs require review. Fixture calculation: sale and hours, assessment date, clamped calendar-month anniversary, inclusive period and hours. Required exclusion code misuse_check."
      },
      "models": {
        "value": [
          "M"
        ],
        "quote": "Fixture policy version V1. Effective 2026-01-01 through 2026-12-31, inclusive, assessed on assessment date. OEM reference o1; engine model M. Sale coverage 12 months. Invoice coverage 18 months. Operating-hour limit 1000. Coverage limits include the boundary. Exclusions require evidence; missing exclusion inputs require review. Fixture calculation: sale and hours, assessment date, clamped calendar-month anniversary, inclusive period and hours. Required exclusion code misuse_check."
      },
      "date_basis": {
        "value": "assessment_date",
        "quote": "Fixture policy version V1. Effective 2026-01-01 through 2026-12-31, inclusive, assessed on assessment date. OEM reference o1; engine model M. Sale coverage 12 months. Invoice coverage 18 months. Operating-hour limit 1000. Coverage limits include the boundary. Exclusions require evidence; missing exclusion inputs require review. Fixture calculation: sale and hours, assessment date, clamped calendar-month anniversary, inclusive period and hours. Required exclusion code misuse_check."
      },
      "effective_bounds": {
        "value": "inclusive",
        "quote": "Fixture policy version V1. Effective 2026-01-01 through 2026-12-31, inclusive, assessed on assessment date. OEM reference o1; engine model M. Sale coverage 12 months. Invoice coverage 18 months. Operating-hour limit 1000. Coverage limits include the boundary. Exclusions require evidence; missing exclusion inputs require review. Fixture calculation: sale and hours, assessment date, clamped calendar-month anniversary, inclusive period and hours. Required exclusion code misuse_check."
      },
      "sale_months": {
        "value": 12,
        "quote": "Fixture policy version V1. Effective 2026-01-01 through 2026-12-31, inclusive, assessed on assessment date. OEM reference o1; engine model M. Sale coverage 12 months. Invoice coverage 18 months. Operating-hour limit 1000. Coverage limits include the boundary. Exclusions require evidence; missing exclusion inputs require review. Fixture calculation: sale and hours, assessment date, clamped calendar-month anniversary, inclusive period and hours. Required exclusion code misuse_check."
      },
      "invoice_months": {
        "value": 18,
        "quote": "Fixture policy version V1. Effective 2026-01-01 through 2026-12-31, inclusive, assessed on assessment date. OEM reference o1; engine model M. Sale coverage 12 months. Invoice coverage 18 months. Operating-hour limit 1000. Coverage limits include the boundary. Exclusions require evidence; missing exclusion inputs require review. Fixture calculation: sale and hours, assessment date, clamped calendar-month anniversary, inclusive period and hours. Required exclusion code misuse_check."
      },
      "max_hours": {
        "value": "1000",
        "quote": "Fixture policy version V1. Effective 2026-01-01 through 2026-12-31, inclusive, assessed on assessment date. OEM reference o1; engine model M. Sale coverage 12 months. Invoice coverage 18 months. Operating-hour limit 1000. Coverage limits include the boundary. Exclusions require evidence; missing exclusion inputs require review. Fixture calculation: sale and hours, assessment date, clamped calendar-month anniversary, inclusive period and hours. Required exclusion code misuse_check."
      },
      "coverage_boundaries": {
        "value": "inclusive",
        "quote": "Fixture policy version V1. Effective 2026-01-01 through 2026-12-31, inclusive, assessed on assessment date. OEM reference o1; engine model M. Sale coverage 12 months. Invoice coverage 18 months. Operating-hour limit 1000. Coverage limits include the boundary. Exclusions require evidence; missing exclusion inputs require review. Fixture calculation: sale and hours, assessment date, clamped calendar-month anniversary, inclusive period and hours. Required exclusion code misuse_check."
      },
      "exclusions": {
        "value": "Evidence required",
        "quote": "Fixture policy version V1. Effective 2026-01-01 through 2026-12-31, inclusive, assessed on assessment date. OEM reference o1; engine model M. Sale coverage 12 months. Invoice coverage 18 months. Operating-hour limit 1000. Coverage limits include the boundary. Exclusions require evidence; missing exclusion inputs require review. Fixture calculation: sale and hours, assessment date, clamped calendar-month anniversary, inclusive period and hours. Required exclusion code misuse_check."
      },
      "coverage_mode": {
        "value": "sale_and_hours",
        "quote": "Fixture policy version V1. Effective 2026-01-01 through 2026-12-31, inclusive, assessed on assessment date. OEM reference o1; engine model M. Sale coverage 12 months. Invoice coverage 18 months. Operating-hour limit 1000. Coverage limits include the boundary. Exclusions require evidence; missing exclusion inputs require review. Fixture calculation: sale and hours, assessment date, clamped calendar-month anniversary, inclusive period and hours. Required exclusion code misuse_check."
      },
      "coverage_date_basis": {
        "value": "assessment_date",
        "quote": "Fixture policy version V1. Effective 2026-01-01 through 2026-12-31, inclusive, assessed on assessment date. OEM reference o1; engine model M. Sale coverage 12 months. Invoice coverage 18 months. Operating-hour limit 1000. Coverage limits include the boundary. Exclusions require evidence; missing exclusion inputs require review. Fixture calculation: sale and hours, assessment date, clamped calendar-month anniversary, inclusive period and hours. Required exclusion code misuse_check."
      },
      "period_method": {
        "value": "calendar_month_anniversary_clamped",
        "quote": "Fixture policy version V1. Effective 2026-01-01 through 2026-12-31, inclusive, assessed on assessment date. OEM reference o1; engine model M. Sale coverage 12 months. Invoice coverage 18 months. Operating-hour limit 1000. Coverage limits include the boundary. Exclusions require evidence; missing exclusion inputs require review. Fixture calculation: sale and hours, assessment date, clamped calendar-month anniversary, inclusive period and hours. Required exclusion code misuse_check."
      },
      "period_boundary": {
        "value": "inclusive",
        "quote": "Fixture policy version V1. Effective 2026-01-01 through 2026-12-31, inclusive, assessed on assessment date. OEM reference o1; engine model M. Sale coverage 12 months. Invoice coverage 18 months. Operating-hour limit 1000. Coverage limits include the boundary. Exclusions require evidence; missing exclusion inputs require review. Fixture calculation: sale and hours, assessment date, clamped calendar-month anniversary, inclusive period and hours. Required exclusion code misuse_check."
      },
      "hours_boundary": {
        "value": "inclusive",
        "quote": "Fixture policy version V1. Effective 2026-01-01 through 2026-12-31, inclusive, assessed on assessment date. OEM reference o1; engine model M. Sale coverage 12 months. Invoice coverage 18 months. Operating-hour limit 1000. Coverage limits include the boundary. Exclusions require evidence; missing exclusion inputs require review. Fixture calculation: sale and hours, assessment date, clamped calendar-month anniversary, inclusive period and hours. Required exclusion code misuse_check."
      },
      "exclusion_mode": {
        "value": "checks_required",
        "quote": "Fixture policy version V1. Effective 2026-01-01 through 2026-12-31, inclusive, assessed on assessment date. OEM reference o1; engine model M. Sale coverage 12 months. Invoice coverage 18 months. Operating-hour limit 1000. Coverage limits include the boundary. Exclusions require evidence; missing exclusion inputs require review. Fixture calculation: sale and hours, assessment date, clamped calendar-month anniversary, inclusive period and hours. Required exclusion code misuse_check."
      },
      "exclusion_checks": {
        "value": [
          "misuse_check"
        ],
        "quote": "Fixture policy version V1. Effective 2026-01-01 through 2026-12-31, inclusive, assessed on assessment date. OEM reference o1; engine model M. Sale coverage 12 months. Invoice coverage 18 months. Operating-hour limit 1000. Coverage limits include the boundary. Exclusions require evidence; missing exclusion inputs require review. Fixture calculation: sale and hours, assessment date, clamped calendar-month anniversary, inclusive period and hours. Required exclusion code misuse_check."
      }
    },
    "policy_id": "p1",
    "revision": 1,
    "created_at": "2026-11-01",
    "schema_version": "simpson-policy-draft-v2",
    "status": "draft",
    "source": {
      "source_id": "policy_source_fixture",
      "title": "Fixture policy",
      "kind": "policy",
      "module_ids": [
        "warranty"
      ],
      "text": "Fixture policy version V1. Effective 2026-01-01 through 2026-12-31, inclusive, assessed on assessment date. OEM reference o1; engine model M. Sale coverage 12 months. Invoice coverage 18 months. Operating-hour limit 1000. Coverage limits include the boundary. Exclusions require evidence; missing exclusion inputs require review. Fixture calculation: sale and hours, assessment date, clamped calendar-month anniversary, inclusive period and hours. Required exclusion code misuse_check.",
      "sha256": "c115aa634f2116f171a60d1b888fe5da87723ea0ec1f5904603bb78cd2942c96",
      "origin": "owner_supplied",
      "created_at": "2026-11-01T00:00:00Z"
    },
    "missing_clauses": [],
    "business_policy_verified": false,
    "executable": false,
    "sha256": "689a7410ba8a9316e69d85f21310a6eca9ab8e11122f012e613f31a68932b12c"
  },
  "clause_specs": [
    {
      "clause_id": "source_version",
      "label": "Source policy version",
      "kind": "text",
      "choices": []
    },
    {
      "clause_id": "effective_from",
      "label": "Effective from",
      "kind": "date",
      "choices": []
    },
    {
      "clause_id": "effective_to",
      "label": "Effective through",
      "kind": "date",
      "choices": []
    },
    {
      "clause_id": "oem_references",
      "label": "OEM reference values",
      "kind": "list",
      "choices": []
    },
    {
      "clause_id": "models",
      "label": "Engine model values",
      "kind": "list",
      "choices": []
    },
    {
      "clause_id": "date_basis",
      "label": "Effective-date basis",
      "kind": "choice",
      "choices": [
        "assessment_date",
        "sale_date",
        "invoice_date"
      ]
    },
    {
      "clause_id": "effective_bounds",
      "label": "Effective-date boundaries",
      "kind": "choice",
      "choices": [
        "inclusive",
        "exclusive"
      ]
    },
    {
      "clause_id": "sale_months",
      "label": "Sale coverage months",
      "kind": "integer",
      "choices": []
    },
    {
      "clause_id": "invoice_months",
      "label": "Invoice coverage months",
      "kind": "integer",
      "choices": []
    },
    {
      "clause_id": "max_hours",
      "label": "Operating-hour limit",
      "kind": "hours",
      "choices": []
    },
    {
      "clause_id": "coverage_boundaries",
      "label": "Coverage boundary conventions",
      "kind": "text",
      "choices": []
    },
    {
      "clause_id": "exclusions",
      "label": "Exclusions and handling",
      "kind": "text",
      "choices": []
    },
    {
      "clause_id": "coverage_mode",
      "label": "Required coverage checks",
      "kind": "choice",
      "choices": [
        "sale_and_hours",
        "invoice_and_hours",
        "sale_invoice_and_hours"
      ]
    },
    {
      "clause_id": "coverage_date_basis",
      "label": "Coverage date basis",
      "kind": "choice",
      "choices": [
        "assessment_date"
      ]
    },
    {
      "clause_id": "period_method",
      "label": "Coverage month calculation",
      "kind": "choice",
      "choices": [
        "calendar_month_anniversary_clamped",
        "calendar_month_difference"
      ]
    },
    {
      "clause_id": "period_boundary",
      "label": "Coverage period boundary",
      "kind": "choice",
      "choices": [
        "inclusive",
        "exclusive"
      ]
    },
    {
      "clause_id": "hours_boundary",
      "label": "Operating-hour boundary",
      "kind": "choice",
      "choices": [
        "inclusive",
        "exclusive"
      ]
    },
    {
      "clause_id": "exclusion_mode",
      "label": "Exclusion interpretation",
      "kind": "choice",
      "choices": [
        "checks_required",
        "none_declared"
      ]
    },
    {
      "clause_id": "exclusion_checks",
      "label": "Required exclusion codes",
      "kind": "list",
      "choices": []
    }
  ]
};
export function policyDraft(){return businessPolicySchema.parse(fixture.policy);}
export function policyLibrary(populated=false){const p=policyDraft();return businessPolicyListSchema.parse({items:populated?[p]:[],sources:[p.source],clause_specs:fixture.clause_specs,business_policy_verified:false});}
export function policyComparison(){const p=policyDraft();return businessPolicyComparisonSchema.parse({comparison_version:'simpson-policy-comparison-v1',version_id:'v2',graph_id:'g1',policy_id:p.policy_id,policy_key:p.policy_key,policy_revision:1,ticket_node_id:'node1',invoice_node_id:null,assessment_at:'2026-06-01T12:00:00+05:30',status:'requires_review',eligibility:'not_evaluated',policy_clauses:p.clauses,policy_source:p.source,checks:[{check_id:'oem_references',status:'unavailable',expected:['o1'],observed:null,evidence:[],clause_ids:['oem_references']},{check_id:'effective_dates',status:'match',expected:{start:'2026-01-01',end:'2026-12-31',bounds:'inclusive',basis:'assessment_date'},observed:'2026-06-01',evidence:[],clause_ids:['date_basis','effective_from','effective_to','effective_bounds']}],review_reasons:['Draft policy authority and physical engine identity remain unverified.','Limits and exclusions were not executed.'],missing_clauses:[],candidate_comparison:'differences_or_unknowns',limits:['Saved evidence comparison only; no eligibility decision.'],provenance:{graph_created_at:'2026-10-31',source_revisions:{service:1,quality:1},graph_sha256:'graphhash',definition_sha256:'definitionhash',policy_sha256:p.sha256,policy_source_sha256:p.source.sha256},business_policy_verified:false,company_queries:0,model_calls:0,rules_executed:false,report_sha256:'comparisonhash'});}
