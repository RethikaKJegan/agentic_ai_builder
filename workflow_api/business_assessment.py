"""Deterministic draft calculations with strict business-evidence gates."""
from calendar import monthrange
from datetime import date
from decimal import Decimal
from hashlib import sha256
from .business_compiler import canonical
from .business_identity import resolve
from .business_warranty import prepare,parse_date,parse_hours

ASSESSMENT_VERSION='simpson-warranty-assessment-v1'


def decide(checks,*,policy_verified,identity_verified,applicability_verified):
    """Internal decision kernel; verification is never accepted from HTTP input."""
    if (policy_verified is not True or identity_verified is not True or applicability_verified is not True
        or not checks or any(c.get('status') not in ('passed','failed') for c in checks)):
        return 'Requires Review'
    return 'Warranty Not Eligible' if any(c['status']=='failed' for c in checks) else 'Warranty Eligible'


def period(start,as_of,months,method,boundary):
    if (not isinstance(start,str) or not isinstance(as_of,str) or type(months) is not int or not 0<=months<=1200
        or method not in ('calendar_month_anniversary_clamped','calendar_month_difference') or boundary not in ('inclusive','exclusive')):
        return dict(status='unknown',observed=None,limit=months,deadline=None,message='A required date, month limit or calculation/boundary convention is unavailable.')
    try:
        begin=date.fromisoformat(start);end=date.fromisoformat(as_of)
        if end<begin:return dict(status='unknown',observed=None,limit=months,deadline=None,message='The start date follows the assessment date; source chronology needs review.')
        if method=='calendar_month_difference':
            elapsed=(end.year-begin.year)*12+end.month-begin.month;passed=elapsed<=months if boundary=='inclusive' else elapsed<months
            return dict(status='passed' if passed else 'failed',observed=elapsed,limit=months,deadline=None,message='Declared calendar month difference ignores day of month; no anniversary convention was substituted.')
        month_index=begin.year*12+begin.month-1+months;year,month=divmod(month_index,12);month+=1
        deadline=date(year,month,min(begin.day,monthrange(year,month)[1]));passed=end<=deadline if boundary=='inclusive' else end<deadline
        return dict(status='passed' if passed else 'failed',observed=end.isoformat(),limit=months,deadline=deadline.isoformat(),message='Declared monthly anniversary clamps to the target month’s last day; the selected boundary is applied explicitly.')
    except (ValueError,OverflowError,TypeError):
        return dict(status='unknown',observed=None,limit=months,deadline=None,message='Dates are invalid or the anniversary is outside the supported calendar range.')


def assess(policy,snapshot,graph,body,comparison):
    readiness=prepare(snapshot,graph,dict(ticket_node_id=body['ticket_node_id']));associations=resolve(snapshot,graph,dict(ticket_node_id=body['ticket_node_id']))
    inputs={i['field']:i for i in readiness['inputs']};clauses=policy['clauses'];value=lambda key:clauses.get(key,{}).get('value')
    as_of=parse_date(body['assessment_at'])['calendar_date'];checks=[]
    def add(code,status,message,*,observed=None,expected=None,evidence=None,clause_ids=None):
        checks.append(dict(check_id=code,status=status,message=message,observed=observed,expected=expected,evidence=evidence or [],clause_ids=clause_ids or []))
    mode=value('coverage_mode');mode_known=mode in ('sale_and_hours','invoice_and_hours','sale_invoice_and_hours')
    date_basis_known=value('coverage_date_basis')=='assessment_date'
    add('coverage_profile','passed' if mode_known and date_basis_known else 'unknown','Coverage mode and assessment-date basis must be explicitly cited; no legacy defaults are applied.',observed=mode,expected='Explicit supported coverage mode/date basis',clause_ids=['coverage_mode','coverage_date_basis'])
    invoice=next((i for i in readiness['invoice_candidates'] if i['node_id']==body['invoice_node_id']),None)
    for name,required,start_item,key in [
        ('sale_period',mode in ('sale_and_hours','sale_invoice_and_hours'),inputs['complaintRecord.dateOfSale'],'sale_months'),
        ('invoice_period',mode in ('invoice_and_hours','sale_invoice_and_hours'),invoice['observations'][2] if invoice else None,'invoice_months'),
    ]:
        if not required:continue
        result=period(start_item['normalized'] if start_item and start_item['syntactically_usable'] and date_basis_known else None,as_of,value(key),value('period_method'),value('period_boundary'))
        add(name,result['status'],result['message'],observed=dict(start=start_item['normalized'] if start_item else None,assessment_date=as_of,calculated=result['observed'],deadline=result['deadline']),expected=dict(months=value(key),method=value('period_method'),boundary=value('period_boundary')),evidence=[start_item] if start_item else [],clause_ids=[key,'period_method','period_boundary','coverage_date_basis'])
    hours=inputs['complaintRecord.hmr'];limit=parse_hours(value('max_hours'));boundary=value('hours_boundary');hour_state='unknown'
    if hours['syntactically_usable'] and limit is not None and boundary in ('inclusive','exclusive'):
        a,b=Decimal(hours['normalized']),Decimal(limit);hour_state='passed' if (a<=b if boundary=='inclusive' else a<b) else 'failed'
    add('operating_hours',hour_state,'Only primary recorded complaint hours are compared with the cited plain-decimal limit and explicit boundary; zero is preserved.',observed=hours['normalized'],expected=dict(max_hours=limit,boundary=boundary),evidence=[hours],clause_ids=['max_hours','hours_boundary'])
    exclusion_mode=value('exclusion_mode');codes=value('exclusion_checks')
    if exclusion_mode=='none_declared' and codes is None:
        add('exclusions','passed','The selected draft explicitly declares no exclusions; authority/meaning remain unverified.',observed='none_declared',clause_ids=['exclusion_mode','exclusions'])
    elif exclusion_mode=='checks_required' and isinstance(codes,list) and codes:
        for code in codes:add('exclusion:'+code,'unknown','No verified source mapping/finding is available for this required exclusion. Raw warranty/status flags are not interpreted.',expected='Verified present/absent exclusion finding',clause_ids=['exclusion_mode','exclusion_checks','exclusions'])
    else:add('exclusions','unknown','Exclusion interpretation or the required check catalogue is missing.',clause_ids=['exclusion_mode','exclusion_checks','exclusions'])
    blockers=[]
    def block(code,message):blockers.append(dict(code=code,message=message))
    # This library contains draft interpretations only. No current stored draft
    # or caller-controlled boolean can promote itself to authoritative policy.
    policy_verified=False;identity_verified=associations['physical_engine_identity']=='confirmed'
    applicability_verified=False
    block('POLICY_AUTHORITY_UNVERIFIED','The selected policy is a cited draft; business authority and semantic completeness are not established.')
    if not identity_verified:block('PHYSICAL_IDENTITY_UNRESOLVED','Physical-engine identity and selected invoice applicability are not confirmed.')
    if any(c['status']!='match' for c in comparison['checks']):block('POLICY_SCOPE_UNRESOLVED','A policy scope/effectivity comparison differs or is unavailable; this is not a claim denial.')
    else:block('POLICY_APPLICABILITY_UNVERIFIED','Observed scope/date matches do not establish verified policy applicability.')
    if any(c['status']=='unknown' for c in checks):block('REQUIRED_EVIDENCE_UNKNOWN','One or more required coverage/exclusion parameters or observations are unavailable.')
    if any(o['truncated'] for o in graph['outcomes']):block('SOURCE_COVERAGE_TRUNCATED','The bounded graph contains truncated records/search domains.')
    if associations['conflicts']:block('COMPANY_PATH_CONFLICT','The complaint/account company paths conflict.')
    classification=decide(checks,policy_verified=policy_verified,identity_verified=identity_verified,applicability_verified=applicability_verified)
    draft='incomplete_evidence' if any(c['status']=='unknown' for c in checks) else 'outside_declared_limits' if any(c['status']=='failed' for c in checks) else 'within_declared_limits'
    result=dict(assessment_version=ASSESSMENT_VERSION,version_id=snapshot['version_id'],graph_id=graph['graph_id'],policy_id=policy['policy_id'],policy_revision=policy['revision'],ticket_node_id=body['ticket_node_id'],invoice_node_id=body['invoice_node_id'],assessment_at=body['assessment_at'],
        classification=classification,draft_calculation=draft,checks=checks,blockers=blockers,policy_clauses=clauses,policy_source=comparison['policy_source'],applicability_checks=comparison['checks'],
        physical_engine_identity=associations['physical_engine_identity'],business_policy_verified=False,eligibility_final=False,
        provenance={**comparison['provenance'],'association_report_sha256':associations['report_sha256'],'reference_basis_sha256':associations['provenance']['reference_basis_sha256']},
        limits=['Draft calculations are not an eligibility approval or claim denial.','Verified policy authority/applicability, identity and complete required evidence are mandatory for a final decision.','Only explicitly selected saved observations and declared conventions are used; no source/model calls or current-time defaults.','Required exclusion findings remain unknown until an authoritative evidence mapping exists.','No company record or eligibility decision was written.'],
        company_queries=0,model_calls=0,coverage_calculations_performed=any(c['status'] in ('passed','failed') for c in checks if c['check_id'] in ('sale_period','invoice_period','operating_hours')),business_rules_executed=False)
    result['report_sha256']=sha256(canonical(result).encode()).hexdigest();return result


def missing_policy(snapshot,graph,body):
    readiness=prepare(snapshot,graph,dict(ticket_node_id=body['ticket_node_id']));associations=resolve(snapshot,graph,dict(ticket_node_id=body['ticket_node_id']))
    if body['invoice_node_id'] is not None and not any(i['node_id']==body['invoice_node_id'] for i in readiness['invoice_candidates']):
        from .service import ApiFailure
        raise ApiFailure('BUSINESS_ASSESSMENT_INVALID','Selected invoice is not in this saved graph.',422)
    hours=next(i for i in readiness['inputs'] if i['field']=='complaintRecord.hmr')
    result=dict(assessment_version=ASSESSMENT_VERSION,version_id=snapshot['version_id'],graph_id=graph['graph_id'],policy_id=None,policy_revision=None,ticket_node_id=body['ticket_node_id'],invoice_node_id=body['invoice_node_id'],assessment_at=body['assessment_at'],
        classification='Requires Review',draft_calculation='incomplete_evidence',
        checks=[dict(check_id='coverage_profile',status='unknown',message='No policy was selected; no coverage, boundaries or exclusions can be inferred.',observed=None,expected='An applicable authoritative policy',evidence=[],clause_ids=[]),
            dict(check_id='operating_hours',status='unknown',message='Recorded hours are preserved, but no policy limit or boundary is available.',observed=hours['normalized'],expected=None,evidence=[hours],clause_ids=[])],
        blockers=[dict(code='POLICY_MISSING',message='No warranty policy is selected. Missing policy requires review, not approval or denial.'),dict(code='PHYSICAL_IDENTITY_UNRESOLVED',message='Physical-engine identity remains unresolved.')],
        policy_clauses={},policy_source=None,applicability_checks=[],physical_engine_identity='unresolved',business_policy_verified=False,eligibility_final=False,
        provenance={**readiness['provenance'],'policy_sha256':None,'policy_source_sha256':None,'association_report_sha256':associations['report_sha256'],'reference_basis_sha256':associations['provenance']['reference_basis_sha256']},
        limits=['No policy values, limits or exclusions were inferred.','Requires Review is an evidence state, not approval or claim denial.','Only the explicitly selected saved complaint is inspected; no company/model call or decision write.'],
        company_queries=0,model_calls=0,coverage_calculations_performed=False,business_rules_executed=False)
    result['report_sha256']=sha256(canonical(result).encode()).hexdigest();return result
