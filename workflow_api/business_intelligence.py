"""Fixed evidence-qualified reports on immutable source graphs, never an agent."""
from datetime import date,datetime
from hashlib import sha256
import re

from registry.safety import reject_secrets
from .business_compiler import canonical
from .service import ApiFailure

REPORT_VERSION='simpson-snapshot-intelligence-v1'
QUESTIONS={
 'service_path':dict(label='Recorded service path',description='Source records and direct references retained in this bounded engine graph; candidate serial associations remain separate.'),
 'claim_fields':dict(label='Recorded claim fields',description='Manual and SAP claim values remain separate. Literal status/reason fields are not interpreted as approved policy or verified rejection reasons.'),
 'inspection_findings':dict(label='Recorded inspection findings',description='Inspection observations and potential causes are source statements, not confirmed mechanisms or root causes.'),
 'quality_changes':dict(label='Quality and change evidence',description='QA, cut-in and CAPA records are shown without asserting applicability, incorporation or effectiveness.'),
 'dated_observations':dict(label='Dated source observations',description='Groups source dates by recorded calendar day. Date precision and missing timezone remain explicit; chronology does not imply causation.'),
 'evidence_gaps':dict(label='Evidence and policy gaps',description='Recorded missing values, collection coverage, mapping/validation issues and unresolved definition questions; no warranty decision or rate is computed.'),
}
FIELDS={
 'claim_fields':{'claims':['claimReferenceNumber','claimNumber','status','reason','machineSaleDate','dateOfFailure','hoursCovered'], 'claimsftps':['claimReference','claimId','status','reason','machineSaleDate','failureDate','failureHours','simpsonInvoiceDate','partValue']},
 'inspection_findings':{'jointinspectionreports':['dateOfFailure','dateOfSale','hoursCovered','status','potentialCause','defectCode']},
 'quality_changes':{'failedengineanalyses':['defect','beforeImprovement','afterImprovement','cutInEsn','cutInEffectiveDate','qualityApprover','status'],'internalcutins':['plant','listNo','engineCutInNumber','cutInDate','oem','engineModel'],'icacapas':['defect','beforeImprovement','afterImprovement','cutInEsn','cutInEffectiveDate']},
 'dated_observations':{'enginedetails':['invoiceDate','buildDate'],'tickets':['createdAt','complaintRecord.dateOfSale'],'jointinspectionreports':['dateOfSale','dateOfFailure'],'claims':['machineSaleDate','dateOfFailure'],'claimsftps':['machineSaleDate','failureDate','simpsonInvoiceDate'],'failedengineanalyses':['cutInEffectiveDate'],'internalcutins':['cutInDate']},
}
SERVICE={'tickets','jointinspectionreports','enginereplacements','partreplacements','floatengines','focs','oems','oemnames'}


def invalid(message='The saved graph cannot be used for this report.'):
    raise ApiFailure('BUSINESS_INTELLIGENCE_INVALID',message,422)


def check_graph(snapshot,graph):
    if graph.get('version_id')!=snapshot['version_id']:invalid('Graph and definition versions do not match.')
    ids={r['node_id'] for r in graph['records']}
    if len(ids)!=len(graph['records']):invalid('Saved graph identities are not unique.')
    for record in graph['records']:
        if sha256(canonical(record['fields']).encode()).hexdigest()!=record['record_sha256']:invalid('A saved record does not match its projected-field hash.')
    if any(e['source'] not in ids or e['target'] not in ids or e['classification'] not in ('source_reference','candidate') for e in graph['edges']):invalid('A saved graph edge is invalid.')
    try:reject_secrets(graph)
    except Exception:invalid('The saved graph contains unsupported sensitive content.')


def answer(snapshot,graph,body):
    if (not isinstance(body,dict) or set(body)!={'question_id','limit','offset'} or not isinstance(body['question_id'],str) or body['question_id'] not in QUESTIONS
        or type(body['limit']) is not int or not 1<=body['limit']<=50 or type(body['offset']) is not int or not 0<=body['offset']<=20000):
        invalid('Select a fixed snapshot question and a bounded result page.')
    check_graph(snapshot,graph)
    question=body['question_id'];rows=[]
    records={r['node_id']:r for r in graph['records']}
    associations={rid:sorted({e['classification'] for e in graph['edges'] if rid in (e['source'],e['target'])}) for rid in records}
    def row(record,field,value,state='value',qualification=None):
        return dict(node_id=record['node_id'] if record else None,collection=record['collection'] if record else 'snapshot',field=field,value=value,state=state,
            record_sha256=record['record_sha256'] if record else None,associations=associations[record['node_id']] if record else [],
            qualification=qualification or 'Literal source observation; association does not verify physical-engine identity or business meaning.',calendar_date=None,date_precision=None)
    def field_row(record,name):
        cell=next((c for c in record['fields'] if c['name']==name),None)
        qualification='Potential cause recorded by the source; not a confirmed root cause.' if name=='potentialCause' else 'Literal status/reason value; approval or rejection semantics are not established.' if name in ('status','reason') else None
        return row(record,name,cell['value'] if cell else None,cell['state'] if cell else 'not_projected',qualification)
    if question=='service_path':
        for record in graph['records']:
            if record['collection'] in SERVICE:rows.append(row(record,'record_identity',record['key'].get('_id')))
    elif question in FIELDS:
        for record in graph['records']:
            for name in FIELDS[question].get(record['collection'],[]):
                item=field_row(record,name)
                if question=='dated_observations' and item['state']=='value':
                    try:
                        value=item['value']
                        if not isinstance(value,str):raise ValueError()
                        if re.fullmatch(r'\d{4}-\d{2}-\d{2}',value):
                            parsed=date.fromisoformat(value);item.update(calendar_date=parsed.isoformat(),date_precision='date')
                        else:
                            if 'T' not in value:raise ValueError()
                            parsed=datetime.fromisoformat(value.replace('Z','+00:00'))
                            item.update(calendar_date=parsed.date().isoformat(),date_precision='datetime' if parsed.tzinfo else 'local_datetime')
                        item['qualification']='Recorded calendar date only; precision/timezone differences prevent asserting within-day order or causality.'
                    except (ValueError,TypeError,OverflowError):item.update(state='invalid_date',date_precision='invalid',qualification='Source value could not be parsed as a supported ISO date; it was not corrected or inferred.')
                rows.append(item)
        if question=='dated_observations':rows.sort(key=lambda r:(r['calendar_date'] is None,r['calendar_date'] or '',r['collection'],r['node_id'],r['field']))
    else:
        for record in graph['records']:
            for cell in record['fields']:
                if cell['state']!='value':rows.append(row(record,cell['name'],cell['value'],cell['state'],'Missing/unusable in this saved projection; population completeness is unknown.'))
        for outcome in graph['outcomes']:
            if outcome['status']!='matched' or outcome['truncated']:
                item=row(None,outcome['collection'],outcome['records'],'truncated' if outcome['truncated'] else outcome['status'],'Collection outcome describes this bounded search, not database-wide absence.')
                rows.append(item)
        for item in graph['validation']['issues']:
            record=next((r for r in graph['records'] if r['node_id'] in item['focus']),None)
            rows.append(row(record,item['path'],item['message'],'shape_violation','Violation applies to the explicit mapping and saved shapes, not an automatic business decision.'))
        for item in graph['validation']['conversion_issues']:
            rows.append(row(records.get(item['node_id']),item['field'],item['reason'],'conversion_issue','No missing or invalid value was imputed.'))
        for item in graph['unresolved']:
            rows.append(row(records.get(item['node_id']),item['field'],item['target_collection'],item['state'],'Unresolved association; no target was guessed.'))
        for module,questions in sorted(snapshot.get('questions',{}).items()):
            for text in questions:rows.append(row(None,module,text,'definition_question','Unresolved information retained in the saved definition version.'))
    total=len(rows);page=rows[body['offset']:body['offset']+body['limit']]
    caveats=['Only this immutable bounded graph is analyzed; no source database was queried by this report.',
        'Candidate links are not verified physical-engine identity; direct references establish record association, not business approval.',
        'Missing, not-projected, unsupported, invalid-date and truncated values are never imputed.',
        'Zero rows means no matching observations in this saved graph, not absence from company systems.']
    result=dict(version_id=snapshot['version_id'],graph_id=graph['graph_id'],question_id=question,report_version=REPORT_VERSION,title=QUESTIONS[question]['label'],description=QUESTIONS[question]['description'],
        result_state='observations' if page else 'no_matching_observations',rows=page,total_rows=total,offset=body['offset'],limit=body['limit'],has_more=body['offset']+len(page)<total,next_offset=body['offset']+len(page) if body['offset']+len(page)<total else None,
        summary=dict(source_records=len(graph['records']),service_records=sum(r['role']=='service' for r in graph['records']),quality_records=sum(r['role']=='quality' for r in graph['records']),
            direct_references=sum(e['classification']=='source_reference' for e in graph['edges']),candidate_edges=sum(e['classification']=='candidate' for e in graph['edges']),
            truncated_collections=sum(o['truncated'] for o in graph['outcomes']),mapped_instance_validation=graph['validation']['status']),
        limits=caveats,unavailable_conclusions=dict(warranty_eligibility='not_evaluated',confirmed_root_cause='not_evaluated',recurrence='unavailable',failure_rates='unavailable',change_effectiveness='unavailable'),
        provenance=dict(graph_created_at=graph['created_at'],source_revisions=graph['source_revisions'],graph_sha256=sha256(canonical(graph).encode()).hexdigest(),definition_sha256=sha256(canonical(snapshot).encode()).hexdigest()),
        company_queries=0,model_calls=0,rules_executed=False,business_policy_verified=False)
    result['report_sha256']=sha256(canonical(result).encode()).hexdigest()
    return result


class BusinessIntelligence:
    def __init__(self,ontology,graph):self.ontology=ontology;self.graph=graph
    def catalogue(self,auth,version_id,graph_id):
        snapshot=self.ontology.version(auth,version_id);graph=self.graph.get(auth,version_id,graph_id);check_graph(snapshot,graph)
        return dict(version_id=version_id,graph_id=graph_id,report_version=REPORT_VERSION,questions=[dict(question_id=key,**value) for key,value in QUESTIONS.items()])
    def run(self,auth,version_id,graph_id,body):
        snapshot=self.ontology.version(auth,version_id);graph=self.graph.get(auth,version_id,graph_id)
        return answer(snapshot,graph,body)
