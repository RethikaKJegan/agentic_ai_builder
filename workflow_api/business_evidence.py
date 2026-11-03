"""Pure task requirements and source-qualified evidence evaluation.

No model calls, source I/O, writes or acceptance of caller-supplied verified facts.
Agent suggestions are advisory and cannot introduce mandatory requirements.
"""
from copy import deepcopy
import re
from .business_knowledge_model import digest

VERSION = 'task-evidence-v1'
LEVELS = ('required_to_execute', 'required_for_conclusion', 'optional_support', 'downstream')
RECOVERY = {
    'retrieve_evidence': ('retrieval_preview', 'Create a fresh authorized retrieval preview for this task.'),
    'resolve_code': ('retrieval_preview', 'Retrieve the referenced controlled-code record from the permitted catalogue.'),
    'resolve_engineer': ('retrieval_preview', 'Retrieve the referenced user through its permitted native identifier.'),
    'check_mapping': ('knowledge_inspect', 'Inspect the saved mapping and source metadata; import a corrected version if needed.'),
    'assessment_date': ('investigation_plan_input', 'Create a fresh plan with an explicit ISO assessment_date input; completed runs are not overwritten.'),
    'applicable_policy': ('investigation_plan_input', 'Select an available pinned policy_id in a fresh plan; establish its applicability separately.'),
    'verify_evidence': ('evidence_review', 'Inspect supporting source evidence; confirmation requires an authorized evidence provider.'),
    'identity': ('evidence_review', 'Review source-qualified identity candidates and obtain supported identifying evidence.'),
}


def requirement(fact, meaning, provider, level='required_for_conclusion', mappings=(), recovery='verify_evidence'):
    return dict(fact_id=fact, business_meaning=meaning, requirement_level=level,
                provider=provider, mapping_ids=['mapping:'+m for m in mappings],
                validation_rule='source_qualified_'+provider, missing_behavior='preserve_unknown',
                recovery_action=dict(id=recovery, mechanism=RECOVERY[recovery][0], description=RECOVERY[recovery][1], executable=False))


COMPLAINT = requirement('complaint_evidence', 'A source complaint record.', 'complaint', 'required_to_execute', recovery='retrieve_evidence')
CODE = requirement('symptom_description', 'Controlled description of the recorded symptom identifier.', 'code', 'optional_support', recovery='resolve_code')
DATE = requirement('inspection_failure_date', 'Recorded inspection failure calendar date.', 'mapped', 'optional_support', ['inspection_failure_date'], 'check_mapping')
REGISTRY = {
 'complaints': [COMPLAINT, CODE],
 'inspection': [COMPLAINT,
    requirement('linked_inspection', 'An inspection report with a supported direct complaint reference.', 'inspection', 'required_to_execute', recovery='retrieve_evidence'),
    requirement('inspection_observations', 'Relevant observations from the linked report.', 'observations', 'required_to_execute', ['inspection_complaint_text','inspection_defect_text','inspection_potential_cause']),
    CODE, DATE,
    requirement('engineer_reference', 'Source user associated with the recorded engineer reference.', 'engineer', 'optional_support', recovery='resolve_engineer'),
    requirement('inspection_activity_completion_evidence', 'Evidence confirming activity completion separately from report publication.', 'unavailable', 'downstream')],
 'warranty': [COMPLAINT,
    requirement('applicable_policy', 'An explicitly selected policy revision pinned in the ontology.', 'policy', recovery='applicable_policy'),
    requirement('assessment_date', 'An explicitly supplied assessment date.', 'input', recovery='assessment_date'),
    requirement('operating_hours', 'Valid nonnegative complaint-reported operating hours.', 'mapped', mappings=['complaint_hours'], recovery='check_mapping'),
    requirement('physical_identity', 'Established physical-engine identity.', 'unavailable', recovery='identity'),
    requirement('invoice_association', 'Supported selection among source-qualified invoice candidates.', 'invoice', 'optional_support', recovery='identity'),
    requirement('policy_applicable', 'Evidence establishing applicability of the selected policy.', 'unavailable'),
    requirement('exclusion_findings', 'Verified findings for exclusions required by the selected policy.', 'unavailable')],
 'replacement': [COMPLAINT,
    requirement('technical_disposition', 'Supported repair or replacement technical recommendation.', 'unavailable'),
    requirement('commercial_authorization', 'Actual commercial authorization distinct from technical recommendation.', 'unavailable'),
    requirement('replacement_records', 'Available source replacement records.', 'replacement', 'optional_support', recovery='retrieve_evidence')],
 'history': [requirement('history_evidence', 'Available complaint, invoice or QA source history.', 'history', 'required_to_execute', recovery='retrieve_evidence'), CODE,
    requirement('closure_rationale', 'Recorded case timeline or closure explanation.', 'closure', 'optional_support', recovery='retrieve_evidence'),
    requirement('physical_identity', 'Identity evidence for a consolidated physical-engine history.', 'unavailable')],
 'recurrence': [requirement('history_evidence', 'Available invoice and QA observations.', 'history', 'required_to_execute', recovery='retrieve_evidence'),
    *[requirement(fact, meaning, 'unavailable') for fact, meaning in [
        ('change_applicability', 'Verified applicable change and its configuration scope.'),
        ('actual_incorporation', 'Evidence of actual incorporation for the scoped engine.'),
        ('comparable_confirmed_failure', 'Confirmed comparable failure mechanisms.'),
        ('physical_identity', 'Resolved physical identity for the monitored population.'),
        ('monitored_population', 'Defined eligible population for the requested conclusion.'),
        ('operating_exposure', 'Exposure and follow-up sufficient for the requested effectiveness conclusion.')]]],
}
REGISTRY_SHA256 = digest([VERSION, REGISTRY, RECOVERY])


def definitions(task, policies=(), inputs=None):
    """Policy-dependent dates are selected from pinned definitions, never guessed."""
    result=deepcopy(REGISTRY.get(task, []));inputs=inputs or {}
    if task=='warranty':
        policy=next((p for p in policies if p['policy_id']==inputs.get('policy_id')),None)
        mode=(policy or {}).get('clauses',{}).get('coverage_mode')
        if isinstance(mode,dict):mode=mode.get('value')
        for fact, modes, mapping in [('sale_date',('sale_and_hours','sale_invoice_and_hours'),'sale_date'),('invoice_date',('invoice_and_hours','sale_invoice_and_hours'),'invoice_date')]:
            if mode in modes:result.append(requirement(fact,'Date required by the selected policy.', 'mapped', mappings=[mapping], recovery='check_mapping'))
            elif mode is None:result.append(requirement(fact,'Potential policy date requirement; policy selection is unresolved.', 'mapped','optional_support',[mapping],'check_mapping'))
    return [dict(task=task,**r) for r in result]


def source_ref(record):
    return {k:deepcopy(record[k]) for k in ('record_id','collection','connection_id','source_role','source_reference','metadata_revision','read_at') if k in record}


def resolution_views(evidence):
    """Resolve only typed edges produced by the authorized read executor."""
    records={r['record_id']:r for r in evidence.get('records',[])};result=[]
    for binding,kind,original in [('identity:complaint_code','controlled_code','complaintRecord.natureOfCustomerComplaint'),('identity:ticket_engineer','engineer','serviceEngineer')]:
        for record in records.values():
            if record['collection']!='tickets' or original not in record['fields']:continue
            matches=[]
            for edge in evidence.get('reference_edges',[]):
                if edge['binding_id']!=binding or edge.get('classification')!='direct_reference':continue
                if edge['parent_record_id']==record['record_id']:target=records.get(edge['record_id'])
                elif edge['record_id']==record['record_id']:target=records.get(edge['parent_record_id'])
                else:continue
                if target:matches.append(target)
            target=matches[0] if len(matches)==1 else None
            state='resolved' if target else 'ambiguous_value' if matches else 'not_found'
            if not matches:
                collection='simpsoncodes' if kind=='controlled_code' else 'users'
                steps=[s for s in evidence.get('executed_steps',[]) if s.get('collection')==collection]
                mappings=[m for m in evidence.get('selected_mappings',[]) if m['collection']==collection]
                if any('native_reference_type_mismatch' in s.get('unresolved',[]) for s in steps):state='invalid_value'
                elif mappings and not any(m.get('availability','available')=='available' for m in mappings):state='unsupported_mapping'
                elif mappings and not steps:state='not_retrieved'
            resolved={}
            if target:
                for mid,v in target['values'].items():
                    if v['state']=='value':resolved[mid]=deepcopy(v['value'])
                if kind=='controlled_code' and (not resolved.get('mapping:code_description') or resolved.get('mapping:code_type') not in (None,'COMPLAINT') or resolved.get('mapping:code_active') is False):state='not_established'
            result.append(dict(kind=kind,original_value=deepcopy(record['fields'][original]),record_id=record['record_id'],status=state,resolved_values=resolved,source_references=[source_ref(record),*([source_ref(target)] if target else [])]))
    return result


def mapping_state(record, mid):
    value=record.get('values',{}).get(mid)
    if value is None:return 'not_retrieved'
    return {'value':'satisfied','unknown':'not_found','conversion_issue':'invalid_value','ambiguous_value':'ambiguous_value','reference_unresolved':'not_established'}.get(value['state'],'not_established')


def evaluate(task, evidence, inputs=None, policies=()):
    """Evaluate source-backed requirements; preserve scope and per-record gaps."""
    inputs=inputs or {};records=evidence.get('records',[]);views=resolution_views(evidence)
    selected={m['id']:m for m in evidence.get('selected_mappings',evidence.get('mappings',[]))}
    outcomes=[];gaps=[]
    for req in definitions(task,policies,inputs):
        provider=req['provider'];refs=[];state='not_established';contexts=[None]
        if provider in ('complaint','history','replacement','closure'):
            collections={'complaint':('tickets',),'history':('tickets','enginedetails','failedengineanalyses'),'replacement':('enginereplacements','partreplacements','floatengines'),'closure':('tickettimelines',)}[provider]
            found=[r for r in records if r['collection'] in collections]
            # A timeline observation is not automatically a closure decision.
            if provider=='closure':found=[r for r in found if str(r['fields'].get('stage','')).upper() in ('CLOSED','RESOLVED') and r['fields'].get('description')]
            state='satisfied' if found else 'not_found';refs=[source_ref(r) for r in found]
        elif provider=='inspection':
            ids={r['record_id'] for r in records if r['collection']=='jointinspectionreports'}
            found=[e for e in evidence.get('reference_edges',[]) if e['binding_id']=='identity:inspection_ticket' and e.get('classification')=='direct_reference' and (e['record_id'] in ids or e['parent_record_id'] in ids)]
            state='satisfied' if found else 'not_established' if ids else 'not_found';refs=[source_ref(r) for r in records if r['record_id'] in ids]
        elif provider in ('code','engineer'):
            found=[v for v in views if v['kind']==('controlled_code' if provider=='code' else 'engineer')]
            contexts=found or [None]
        elif provider=='observations':
            found=[r for r in records if r['collection']=='jointinspectionreports' and any(r['values'].get(m,{}).get('state')=='value' and r['values'][m].get('value') for m in req['mapping_ids'])]
            state='satisfied' if found else 'not_found';refs=[source_ref(r) for r in found]
        elif provider=='mapped':
            found=[r for r in records if any(m in r.get('values',{}) for m in req['mapping_ids'])]
            contexts=found or [None]
        elif provider=='input':
            from .business_knowledge_model import convert
            state='not_retrieved' if not inputs.get(req['fact_id']) else 'satisfied' if convert(inputs[req['fact_id']],'iso_date','date')['state']=='value' else 'invalid_value'
        elif provider=='policy':
            chosen=next((p for p in policies if p['policy_id']==inputs.get('policy_id')),None)
            state='satisfied' if chosen else 'not_retrieved';refs=[dict(policy_id=chosen['policy_id'],revision=chosen['revision'],sha256=chosen['sha256'])] if chosen else []
        elif provider=='invoice':
            found={r['record_id']:r for r in records if r['collection']=='enginedetails'}
            state='ambiguous_value' if len(found)>1 else 'not_established' if found else 'not_found'
            refs=[source_ref(r) for r in found.values()]
        for context in contexts:
            local_state=state;local_refs=refs
            if provider in ('code','engineer'):
                local_state=('satisfied' if context['status']=='resolved' else context['status']) if context else 'not_retrieved'
                local_refs=context['source_references'] if context else []
            elif provider=='mapped':
                if context:
                    states=[mapping_state(context,m) for m in req['mapping_ids'] if m in context['values']]
                    local_state='satisfied' if 'satisfied' in states else states[0] if states else 'not_retrieved'
                    local_refs=[source_ref(context)]
                else:local_state='unsupported_mapping' if not any(m in selected and selected[m].get('availability','available')=='available' for m in req['mapping_ids']) else 'not_found'
            context_id=context.get('record_id') if context else None
            item=dict(**req,state=local_state,source_references=deepcopy(local_refs),context_id=context_id)
            outcomes.append(item)
            if local_state=='satisfied':continue
            impact={'required_to_execute':'blocking_current_task','required_for_conclusion':'blocking_requested_conclusion','optional_support':'optional_supporting_evidence','downstream':'later_stage'}[req['requirement_level']]
            reason='Inspection evidence is missing: no supported linked report.' if req['fact_id']=='linked_inspection' else req['business_meaning']
            gaps.append(dict(fact_id=req['fact_id'],fact=req['fact_id'],task=task,requirement_level=req['requirement_level'],state=local_state,reason=reason,impact=impact,recovery_action=deepcopy(req['recovery_action']),source_references=deepcopy(local_refs),context_id=context_id))
    return dict(version=VERSION,registry_sha256=REGISTRY_SHA256,task=task,requirements=outcomes,gaps=normalize_gaps(gaps),resolutions=views,
                task_executable=not any(g['impact']=='blocking_current_task' for g in gaps),
                conclusion_ready=not any(g['impact'] in ('blocking_current_task','blocking_requested_conclusion') for g in gaps))


def normalize_gaps(gaps):
    """Merge duplicate facts only within the same task/record/requirement context."""
    merged={}
    for raw in gaps:
        g=deepcopy(raw);key=(g['task'],g['fact_id'],g.get('context_id'),g['requirement_level'],g['state'])
        if key not in merged:merged[key]=g
        else:
            refs=merged[key]['source_references']+g.get('source_references',[])
            merged[key]['source_references']=list({digest(r):r for r in refs}.values())
    for key,g in merged.items():g['gap_id']='gap_'+digest(key)[:24]
    return list(merged.values())


def reconcile_suggestions(analyses, results):
    """Suggestions remain advisory; no fuzzy match may satisfy a requirement."""
    suggestions={}
    for analysis in analyses:
        for text in analysis.get('missing_information',[]):
            normalized=' '.join(re.findall(r'[a-z0-9]+',text.lower()))
            if normalized:suggestions.setdefault(normalized,dict(text=text,classification='agent_suggestion',mandatory=False))
    return list(suggestions.values())
