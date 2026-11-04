"""Versioned, deterministic evidence coverage over source-qualified case records."""
from copy import deepcopy
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from jsonschema import Draft202012Validator
from .business_evidence import evaluate, requirement, normalize_gaps, REGISTRY
from .business_knowledge_model import digest

VERSION='business-coverage-v1'
TASKS=('inspection','warranty','replacement')

def obj(properties):
    return dict(type='object',additionalProperties=False,required=list(properties),properties=properties)
TEXT=dict(type='string',minLength=1,maxLength=3000)
STRINGS=dict(type='array',items=TEXT,minItems=1,uniqueItems=True)
DAY=dict(type='string',pattern=r'^\d{4}-\d{2}-\d{2}$')
BOOL=dict(type='boolean')
NUMBER=dict(type='number',minimum=0)
DATA={
 'identity':obj(dict(engine_serial=TEXT,complaint_id=TEXT,inspection_ids=STRINGS,invoice_id=TEXT,oem=TEXT,model=TEXT,confirmed=BOOL)),
 'invoice':obj(dict(engine_serial=TEXT,invoice_date=DAY,sale_date=DAY)),
 'policy':obj(dict(policy_key=TEXT,revision=dict(type='integer',minimum=1),effective_from=DAY,effective_to=DAY,oems=STRINGS,models=STRINGS,coverage_mode=dict(enum=['sale_and_hours','invoice_and_hours','sale_invoice_and_hours']),sale_months=NUMBER,invoice_months=NUMBER,max_hours=NUMBER,exclusions=STRINGS)),
 'technical_decision':obj(dict(engine_serial=TEXT,inspection_id=TEXT,disposition=dict(enum=['repair','component_replacement','engine_replacement','no_replacement']),reason=TEXT,engineer_id=TEXT,decided_at=DAY,diagnosis_verified=BOOL)),
 'authorization':obj(dict(engine_serial=TEXT,technical_id=TEXT,decision=dict(enum=['approved','rejected']),payment_category=dict(enum=['warranty','goodwill','customer_paid']),authority_role=TEXT,required_role=TEXT,decided_at=DAY,valid_until=DAY,revoked=BOOL)),
 'exclusion_assessment':obj(dict(engine_serial=TEXT,policy_id=TEXT,assessed_at=DAY,checks=dict(type='array',minItems=1,items=obj(dict(exclusion=TEXT,applies=BOOL,evidence=TEXT))))),
}
PROVENANCE=obj(dict(kind=dict(enum=['source','generated']),basis=TEXT,source_references=dict(type='array',minItems=1,items=dict(type='object',minProperties=1))))
RECORD_SCHEMA=dict(oneOf=[obj(dict(record_id=TEXT,case_id=TEXT,kind=dict(const=kind),revision=dict(type='integer',minimum=1),observed_at=TEXT,provenance=PROVENANCE,data=schema)) for kind,schema in DATA.items()])
PROVIDER_FACTS={'physical_identity':'identity','invoice_association':'identity','policy_applicable':'policy','exclusion_findings':'exclusion_assessment','technical_disposition':'technical_decision','commercial_authorization':'authorization'}
EXTRA_REPLACEMENT=[requirement('linked_inspection','A supported linked inspection for replacement review.','inspection','required_for_conclusion'),requirement('inspection_observations','Recorded inspection observations supporting the technical review.','observations','required_for_conclusion',['inspection_complaint_text','inspection_defect_text','inspection_potential_cause'])]
FINGERPRINT=digest([VERSION,RECORD_SCHEMA,PROVIDER_FACTS,EXTRA_REPLACEMENT])


def validate_record(record):
    errors=list(Draft202012Validator(RECORD_SCHEMA).iter_errors(record))
    if errors:raise ValueError('Invalid business evidence record: '+('/'.join(map(str,errors[0].absolute_path)) or 'schema'))
    at=datetime.fromisoformat(record['observed_at'].replace('Z','+00:00'))
    if at.tzinfo is None:raise ValueError('Evidence observation requires an explicit timezone')
    for key,value in record['data'].items():
        if key.endswith(('_date','_at','_from','_to','_until')):date.fromisoformat(value)
    return record


def refs(record):
    return [dict(record_id=record['record_id'],kind=record['kind'],revision=record['revision'],provenance=deepcopy(record['provenance']),observed_at=record['observed_at'])]


def source_ids(evidence,collection):
    return {r['record_id'] for r in evidence.get('records',[]) if r['collection']==collection}


def _coverage_state(gaps,unsupported=False):
    blocking=[g for g in gaps if g['impact'] in ('blocking_current_task','blocking_requested_conclusion')]
    if unsupported:return 'unsupported'
    if any(g['state'] in ('conflicting_evidence','ambiguous_value') for g in blocking):return 'conflicting_evidence'
    if any(g['fact_id'] in ('assessment_date','applicable_policy') and g['state']=='not_retrieved' for g in blocking):return 'needs_input'
    if blocking:return 'insufficient_evidence'
    return 'ready_with_limitations' if gaps else 'ready'


def coverage(task,evidence,inputs=None,business_records=(),case_id=None,revoked=(),policies=()):
    """Pure evaluation. Records come only from an authorized pinned environment."""
    inputs=deepcopy(inputs or {});records=list(business_records);invalid=[];grouped={}
    for record in records:
        try:validate_record(record)
        except (ValueError,TypeError):invalid.append(record.get('record_id'));continue
        if record['case_id']!=case_id:invalid.append(record['record_id']);continue
        grouped.setdefault(record['kind'],[]).append(record)
    selected_policy=next((r for r in grouped.get('policy',[]) if r['record_id']==inputs.get('policy_id')),None)
    base_policies=list(policies)
    if selected_policy:base_policies=[dict(policy_id=selected_policy['record_id'],revision=selected_policy['revision'],sha256=digest(selected_policy),clauses={'coverage_mode':{'value':selected_policy['data']['coverage_mode']}})]
    base=evaluate(task,evidence,inputs,base_policies)
    requirements=deepcopy(base['requirements'])
    if task=='replacement':
        extra=evaluate('inspection',evidence,inputs)['requirements']
        requirements.extend(dict(r,task=task,requirement_level='required_for_conclusion') for r in extra if r['fact_id'] in ('linked_inspection','inspection_observations'))
        identity_req=next(r for r in evaluate('warranty',evidence,inputs,base_policies)['requirements'] if r['fact_id']=='physical_identity')
        requirements.append(dict(identity_req,task=task))
    if task in ('inspection','replacement'):
        observation=requirement('complaint_observations','Relevant recorded complaint observations.','complaint_observations','required_to_execute',['complaint_symptom','complaint_oem_notes'],recovery='retrieve_evidence')
        found=[r for r in evidence.get('records',[]) if r['collection']=='tickets' and any(r.get('values',{}).get(mid,{}).get('state')=='value' and r['values'][mid].get('value') for mid in observation['mapping_ids'])]
        requirements.append(dict(task=task,**observation,state='satisfied' if found else 'not_found',source_references=[dict(record_id=r['record_id'],source_reference=r.get('source_reference',{}),read_at=r.get('read_at')) for r in found],context_id=None))
    facts={};outcomes={};provider_refs={};errors={}
    def get(kind):
        candidates=grouped.get(kind,[])
        if kind=='policy' and inputs.get('policy_id'):candidates=[r for r in candidates if r['record_id']==inputs['policy_id']]
        if not candidates:return None,'not_found'
        if any(r['record_id'] in revoked for r in candidates):return None,'not_established'
        if len({digest(r['data']) for r in candidates})>1:return None,'conflicting_evidence'
        return candidates[0],'satisfied'
    identity,is_state=get('identity');invoice,iv_state=get('invoice');policy,p_state=get('policy');technical,t_state=get('technical_decision');auth,a_state=get('authorization');exclusions,e_state=get('exclusion_assessment')
    serials={str(r['values'][m]['value']) for r in evidence.get('records',[]) for m in ('mapping:ticket_serial','mapping:invoice_serial') if r.get('values',{}).get(m,{}).get('state')=='value'}
    complaints=source_ids(evidence,'tickets');inspections=source_ids(evidence,'jointinspectionreports')
    if identity:
        d=identity['data']
        ok=d['confirmed'] and d['complaint_id'] in complaints and bool(inspections.intersection(d['inspection_ids']))
        ok=ok and invoice is not None and d['invoice_id']==invoice['record_id'] and invoice['data']['engine_serial']==d['engine_serial']
        if serials and (d['engine_serial'] not in serials or len(serials)>1):is_state='conflicting_evidence'
        elif not ok:is_state='not_established'
    for fact in ('physical_identity','invoice_association'):
        if records:facts[fact]=is_state;provider_refs[fact]=refs(identity) if identity else []
    if invoice:
        for fact in ('sale_date','invoice_date'):
            facts[fact]='invalid_value' if inputs.get('assessment_date') and date.fromisoformat(invoice['data'][fact])>date.fromisoformat(inputs['assessment_date']) else 'satisfied';provider_refs[fact]=refs(invoice)
    if policy:
        d=policy['data'];state=p_state
        if date.fromisoformat(d['effective_from'])>date.fromisoformat(d['effective_to']):state='invalid_value'
        if identity:
            matching=('*' in d['oems'] or identity['data']['oem'] in d['oems']) and ('*' in d['models'] or identity['data']['model'] in d['models'])
            outcomes['policy_scope']='applicable' if matching else 'out_of_scope'
        else:state='not_established'
        facts['policy_applicable']=state;provider_refs['policy_applicable']=refs(policy)
        if selected_policy:facts['applicable_policy']=p_state;provider_refs['applicable_policy']=refs(selected_policy)
    if records and not policy:facts['policy_applicable']=p_state
    if technical:
        d=technical['data']
        if not identity or d['engine_serial']!=identity['data']['engine_serial']:t_state='conflicting_evidence' if identity else 'not_established'
        elif d['inspection_id'] not in inspections:t_state='not_established'
        outcomes['technical_disposition']=d['disposition']
    if records:facts['technical_disposition']=t_state;provider_refs['technical_disposition']=refs(technical) if technical else []
    if auth:
        d=auth['data']
        if not technical or d['technical_id']!=technical['record_id']:a_state='not_established'
        elif d['engine_serial']!=technical['data']['engine_serial']:a_state='conflicting_evidence'
        elif d['authority_role']!=d['required_role'] or date.fromisoformat(d['valid_until'])<date.fromisoformat(d['decided_at']):a_state='not_established'
        elif date.fromisoformat(d['decided_at'])<date.fromisoformat(technical['data']['decided_at']):a_state='invalid_value'
        outcomes['authorization_outcome']=d['decision']
        if d['revoked']:outcomes['authorization_outcome']='revoked'
        if inputs.get('assessment_date') and date.fromisoformat(d['valid_until'])<date.fromisoformat(inputs['assessment_date']):outcomes['authorization_outcome']='expired'
        outcomes['commercial_category']=d['payment_category']
    if records:facts['commercial_authorization']=a_state;provider_refs['commercial_authorization']=refs(auth) if auth else []
    if exclusions:
        d=exclusions['data'];checks=d['checks']
        if not policy or d['policy_id']!=policy['record_id'] or not identity:e_state='not_established'
        elif d['engine_serial']!=identity['data']['engine_serial']:e_state='conflicting_evidence'
        elif set(c['exclusion'] for c in checks)!=set(policy['data']['exclusions']):e_state='not_established'
        elif any(len({c['applies'] for c in checks if c['exclusion']==name})>1 for name in policy['data']['exclusions']):e_state='conflicting_evidence'
        outcomes['exclusions']='applies' if any(c['applies'] for c in checks) else 'none_apply'
    if records:facts['exclusion_findings']=e_state;provider_refs['exclusion_findings']=refs(exclusions) if exclusions else []
    gaps=[]
    for req in requirements:
        fact=req['fact_id']
        if fact=='operating_hours' and req['state']=='satisfied':
            values=[r['values']['mapping:complaint_hours']['value'] for r in evidence.get('records',[]) if r.get('values',{}).get('mapping:complaint_hours',{}).get('state')=='value' and (req.get('context_id') is None or r['record_id']==req['context_id'])]
            try:
                if not values or not all(Decimal(str(v)).is_finite() and Decimal(str(v))>=0 for v in values):req['state']='invalid_value'
            except (InvalidOperation,ValueError,TypeError):req['state']='invalid_value'
        if fact in facts:req.update(state=facts[fact],source_references=provider_refs.get(fact,[]),provider='business_record:'+PROVIDER_FACTS.get(fact,'invoice'))
        invalid_kinds={r.get('kind') for r in records if r.get('record_id') in invalid}
        affected={'identity':{'physical_identity','invoice_association','technical_disposition','commercial_authorization','policy_applicable'},'invoice':{'sale_date','invoice_date','physical_identity','invoice_association'},'policy':{'applicable_policy','policy_applicable','exclusion_findings'},'technical_decision':{'technical_disposition','commercial_authorization'},'authorization':{'commercial_authorization'},'exclusion_assessment':{'exclusion_findings'}}
        if any(fact in affected.get(kind,set()) for kind in invalid_kinds):req['state']='invalid_value'
        if req['state']=='satisfied' or req['requirement_level']=='downstream':continue
        impact={'required_to_execute':'blocking_current_task','required_for_conclusion':'blocking_requested_conclusion','optional_support':'optional_supporting_evidence'}[req['requirement_level']]
        gaps.append(dict(fact_id=fact,fact=fact,task=task,requirement_level=req['requirement_level'],state=req['state'],reason=req['business_meaning'],impact=impact,recovery_action=req['recovery_action'],source_references=req['source_references'],context_id=req.get('context_id')))
    required_collections={'inspection':{'tickets','jointinspectionreports'},'warranty':{'tickets','enginedetails'},'replacement':{'tickets','jointinspectionreports'},'complaints':{'tickets'}}.get(task,set())
    for step in evidence.get('executed_steps',[]):
        if not step.get('truncated'):continue
        blocking=step.get('collection') in required_collections
        req=requirement('source_scope_complete','Retrieval reached its bounded limit; additional relevant records may exist.','source_scope','required_for_conclusion' if blocking else 'optional_support',recovery='retrieve_evidence')
        gaps.append(dict(fact_id=req['fact_id'],fact=req['fact_id'],task=task,requirement_level=req['requirement_level'],state='not_retrieved',reason=req['business_meaning'],impact='blocking_requested_conclusion' if blocking else 'optional_supporting_evidence',recovery_action=req['recovery_action'],source_references=[],context_id=step.get('collection')))
    gaps=normalize_gaps(gaps);state=_coverage_state(gaps,task not in REGISTRY)
    if task=='warranty' and state in ('ready','ready_with_limitations'):
        pd=policy['data'] if policy else None
        if pd and invoice:
            assessment=date.fromisoformat(inputs['assessment_date']);d=invoice['data'];months=lambda value:(assessment.year-value.year)*12+assessment.month-value.month
            hours=next((Decimal(str(r['values']['mapping:complaint_hours']['value'])) for r in evidence.get('records',[]) if r.get('values',{}).get('mapping:complaint_hours',{}).get('state')=='value'),None)
            sale=date.fromisoformat(d['sale_date']);inv=date.fromisoformat(d['invoice_date'])
            age_ok=('sale' not in pd['coverage_mode'] or 0<=months(sale)<=pd['sale_months']) and ('invoice' not in pd['coverage_mode'] or 0<=months(inv)<=pd['invoice_months'])
            active=date.fromisoformat(pd['effective_from'])<=assessment<=date.fromisoformat(pd['effective_to'])
            eligible=active and age_ok and hours is not None and hours<=Decimal(str(pd['max_hours'])) and outcomes.get('exclusions')=='none_apply' and outcomes.get('policy_scope')=='applicable'
            outcomes['warranty']='within_configured_conditions' if eligible else 'outside_configured_conditions'
            outcomes['policy_period']='active' if active else 'expired_or_not_effective'
    return dict(version=VERSION,provider_fingerprint=FINGERPRINT,task=task,state=state,requirements=requirements,gaps=gaps,optional_limitations=[g for g in gaps if g['impact']=='optional_supporting_evidence'],blocking_requirements=[g for g in gaps if g['impact']!='optional_supporting_evidence'],available_evidence=[r for r in requirements if r['state']=='satisfied'],business_outcomes=outcomes,provenance='scenario' if records and any(r['provenance']['kind']=='generated' for r in records) else 'source',official_approval=False,task_executable=not any(g['impact']=='blocking_current_task' for g in gaps),conclusion_ready=state in ('ready','ready_with_limitations'),invalid_record_ids=invalid,resolutions=base['resolutions'])


# Fingerprint executable provider semantics as well as its public schema.
from hashlib import sha256
from pathlib import Path
FINGERPRINT=digest([FINGERPRINT,sha256(Path(__file__).read_bytes()).hexdigest()])
