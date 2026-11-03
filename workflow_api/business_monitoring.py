"""Monitoring evidence over bounded saved records; no recurrence inference."""
from datetime import date
from hashlib import sha256
import re
from .business_compiler import canonical
from .business_intelligence import check_graph
from .business_warranty import observation
from .service import ApiFailure

REPORT_VERSION='simpson-monitoring-readiness-v1'
CHANGES={'internalcutins':'service','failedengineanalyses':'quality','failedpartanalyses':'quality','icacapas':'quality'}
FIELDS={
 'enginedetails':{'identity_context':['_id','engineSerialNumber','oem','engineModel','listNo']},
 'tickets':{'identity_context':['engineNo','oemOrg','engineModal'],'recorded_hours':['complaintRecord.hmr'],'change_context':['cutInNumber','cutIn']},
 'jointinspectionreports':{'failure_date':['dateOfFailure'],'failure_context':['potentialCause','defectCode','status'],'recorded_hours':['hoursCovered']},
 'claims':{'failure_date':['dateOfFailure'],'failure_context':['reason','status'],'recorded_hours':['hoursCovered']},
 'claimsftps':{'failure_date':['failureDate'],'failure_context':['defectCode','status'],'recorded_hours':['failureHours']},
 'internalcutins':{'change_context':['plant','listNo','engineCutInNumber','cutInDate','oem','defectCode','engineModel']},
 'failedengineanalyses':{'change_context':['defect','beforeImprovement','afterImprovement','cutInEsn','cutInEffectiveDate','oem','engineModel','listNo','qualityApprover','status']},
 'failedpartanalyses':{'change_context':['defect','cutInEsn','cutInEffectiveDate','oem','engineModel','qualityApprover','status']},
 'icacapas':{'change_context':['defect','beforeImprovement','afterImprovement','cutInEsn','cutInEffectiveDate','oem','engineModel','listNo']},
}
DATE_FIELDS={'dateOfFailure','failureDate','cutInDate','cutInEffectiveDate'}


def invalid(message):raise ApiFailure('BUSINESS_MONITORING_INVALID',message,422)


def calendar(value):
    if not isinstance(value,str) or not re.fullmatch(r'[0-9]{4}-[0-9]{2}-[0-9]{2}',value):invalid('Use explicit ISO calendar dates for the monitoring window.')
    try:return date.fromisoformat(value)
    except ValueError:invalid('Monitoring window date is invalid.')


def report(snapshot,graph,body):
    if (not isinstance(body,dict) or set(body)!={'change_node_id','period_start','period_end','limit','offset'}
        or not (body['change_node_id'] is None or isinstance(body['change_node_id'],str))
        or type(body['limit']) is not int or not 1<=body['limit']<=50 or type(body['offset']) is not int or not 0<=body['offset']<=20000):invalid('Select a saved change, explicit monitoring window and bounded observation page.')
    start=calendar(body['period_start']);end=calendar(body['period_end'])
    if end<start:invalid('Monitoring window end must not precede its start.')
    check_graph(snapshot,graph)
    change=next((r for r in graph['records'] if r['node_id']==body['change_node_id']),None)
    if body['change_node_id'] is not None and (not change or CHANGES.get(change['collection'])!=change['role']):invalid('Select a supported saved cut-in, analysis or CAPA record in this graph.')
    rows=[]
    for record in graph['records']:
        associations=sorted({e['classification'] for e in graph['edges'] if record['node_id'] in (e['source'],e['target'])})
        for category,fields in FIELDS.get(record['collection'],{}).items():
            for name in fields:
                kind='date' if name in DATE_FIELDS else 'hours' if category=='recorded_hours' else 'identifier'
                item=observation(record,name,kind,name)
                bucket='not_applicable'
                if category=='failure_date':
                    bucket=('before_period' if item['normalized']<start.isoformat() else 'after_period' if item['normalized']>end.isoformat() else 'within_period') if item['syntactically_usable'] else 'invalid_date' if item['source_state']=='value' else 'unavailable'
                rows.append(dict(**item,role=record['role'],connection_id=record['connection_id'],category=category,window_bucket=bucket,associations=associations,
                    selected_change=record['node_id']==body['change_node_id'],qualification='Separate saved source observation; not a confirmed failure, cohort member, incorporation or recurrence.'))
    def evidence(category):return [r for r in rows if r['category']==category and r['syntactically_usable']]
    prerequisites=[]
    def prerequisite(key,label,status,message,items=()):
        nodes=sorted({r['node_id'] for r in items})
        prerequisites.append(dict(prerequisite_id=key,label=label,status=status,message=message,evidence_observations=len(items),evidence_node_ids=nodes[:20],evidence_nodes_truncated=len(nodes)>20))
    ids=evidence('identity_context');changes=[r for r in evidence('change_context') if r['selected_change']];failures=evidence('failure_context')
    prerequisite('physical_identity','Physical-engine identity','observed_unverified' if ids else 'unavailable','Serial/reference observations do not establish a stable physical engine or deduplicate incidents.',ids)
    prerequisite('applicability','Scoped change applicability','observed_unverified' if changes else 'unavailable','Selected change fields do not verify model/company/plant/component scope, serial ordering, exceptions or retrofits.',changes)
    prerequisite('incorporation','Actual change incorporation','unavailable','No verified installation/production/configuration evidence mapping establishes incorporation in a physical engine.')
    prerequisite('comparable_failures','Confirmed comparable failures','observed_unverified' if failures else 'unavailable','Defect, potential-cause, approver and status values do not confirm equivalent mechanisms, root causes or distinct failure events.',failures)
    prerequisite('population','Eligible monitored population','unavailable','An exact-serial bounded graph is not a complete eligible engine cohort or population denominator.')
    prerequisite('exposure','Longitudinal operating exposure','unavailable','Individual complaint/claim hour readings are not longitudinal exposure, follow-up completeness or a sufficient-exposure threshold.',evidence('recorded_hours'))
    incomplete=any(o['status']!='matched' or o['truncated'] for o in graph['outcomes'])
    prerequisite('source_coverage','Observation and source coverage','incomplete' if incomplete else 'observed_unverified','Collection outcomes describe bounded searches only; even all matched records cannot prove follow-up/population completeness.')
    prerequisite('period','Declared observation window','declared','The entered calendar-day window is inclusive; declaring a window does not establish complete observation coverage.')
    total=len(rows);page=rows[body['offset']:body['offset']+body['limit']];buckets={key:sum(r['category']=='failure_date' and r['window_bucket']==key for r in rows) for key in ['before_period','within_period','after_period','invalid_date','unavailable']}
    result=dict(report_version=REPORT_VERSION,version_id=snapshot['version_id'],graph_id=graph['graph_id'],change_node_id=body['change_node_id'],period_start=start.isoformat(),period_end=end.isoformat(),period_bounds='inclusive',
        status='requires_evidence',prerequisites=prerequisites,rows=page,total_rows=total,offset=body['offset'],limit=body['limit'],has_more=body['offset']+len(page)<total,next_offset=body['offset']+len(page) if body['offset']+len(page)<total else None,
        summary=dict(saved_records=len(graph['records']),change_candidates=sum(CHANGES.get(r['collection'])==r['role'] for r in graph['records']),failure_date_observations=buckets,truncated_collections=sum(o['truncated'] for o in graph['outcomes'])),
        metrics=dict(confirmed_recurrences=None,failure_rate=None,change_effectiveness=None,monitored_population=None,operating_exposure=None),
        limits=['Only this bounded immutable graph is inspected; selected change does not establish a cohort or filter records into verified applicability.',
            'Date buckets count source-field observations, not distinct failures. Claims and inspections can describe the same incident; no numerator is inferred.',
            'Zero observations is not zero failures. Missing, invalid or unprojected values and truncated/unavailable collections remain explicit.',
            'Failure dates retain recorded calendar days and date/time precision; no current-time fallback, serial ordering or post-cut-in inference.',
            'No recurrence, rate or effectiveness conclusion is available without verified identity, applicability, incorporation, comparable failures, population and exposure.'],
        provenance=dict(graph_created_at=graph['created_at'],source_revisions=graph['source_revisions'],graph_sha256=sha256(canonical(graph).encode()).hexdigest(),definition_sha256=sha256(canonical(snapshot).encode()).hexdigest()),
        company_queries=0,model_calls=0,source_writes=0,monitoring_scheduled=False)
    result['report_sha256']=sha256(canonical(result).encode()).hexdigest();return result


class BusinessMonitoring:
    def __init__(self,ontology,graph):self.ontology=ontology;self.graph=graph
    def run(self,auth,version_id,graph_id,body):return report(self.ontology.version(auth,version_id),self.graph.get(auth,version_id,graph_id),body)
