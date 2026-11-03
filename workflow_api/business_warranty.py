"""Warranty input preparation on saved evidence; no eligibility execution."""
from datetime import date,datetime
from decimal import Decimal,InvalidOperation
from hashlib import sha256
import re

from .business_compiler import canonical
from .business_intelligence import check_graph
from .service import ApiFailure

READINESS_VERSION='simpson-warranty-inputs-v2'
DATE_PATTERN=r'[0-9]{4}-[0-9]{2}-[0-9]{2}(?:T[0-9]{2}:[0-9]{2}:[0-9]{2}(?:\.[0-9]{1,6})?(?:Z|[+-](?:[01][0-9]|2[0-3]):[0-5][0-9])?)?'


def parse_hours(value):
    if type(value) not in (int,float,str):return None
    text=str(value).strip()
    if len(text)>64 or not re.fullmatch(r'[0-9]+(?:\.[0-9]+)?',text):return None
    try:
        result=Decimal(text)
        if not result.is_finite() or result<0:return None
        # Plain decimal string avoids floating point rounding and exponent notation.
        normalized=format(result,'f')
        return normalized.rstrip('0').rstrip('.') if '.' in normalized else normalized
    except InvalidOperation:return None


def parse_date(value):
    if not isinstance(value,str) or not re.fullmatch(DATE_PATTERN,value):return None
    try:
        if len(value)==10:return dict(calendar_date=date.fromisoformat(value).isoformat(),precision='date')
        parsed=datetime.fromisoformat(value.replace('Z','+00:00'))
        return dict(calendar_date=parsed.date().isoformat(),precision='datetime' if parsed.tzinfo else 'local_datetime')
    except (ValueError,OverflowError):return None


def observation(record,field,kind,label):
    cell=next((f for f in record['fields'] if f['name']==field),None)
    state=cell['state'] if cell else 'not_projected';value=cell['value'] if cell else None
    normalized=None;precision=None;usable=False
    if state=='value':
        if kind=='hours':normalized=parse_hours(value);usable=normalized is not None
        elif kind=='date':
            parsed=parse_date(value)
            if parsed:normalized=parsed['calendar_date'];precision=parsed['precision'];usable=True
        elif kind=='identifier':usable=type(value) in (str,int) and (bool(value.strip()) if isinstance(value,str) else True);normalized=value if usable else None
        if not usable:state='invalid_value'
    return dict(label=label,node_id=record['node_id'],collection=record['collection'],field=field,kind=kind,source_state=cell['state'] if cell else 'not_projected',state=state,value=value,normalized=normalized,date_precision=precision,syntactically_usable=usable,record_sha256=record['record_sha256'])


def comparison(left,right):
    if not left['syntactically_usable'] or not right['syntactically_usable']:return 'unavailable'
    # No string/number coercion and no comparison of normalized values.
    return 'exact_match' if type(left['value']) is type(right['value']) and left['value']==right['value'] else 'different'


def prepare(snapshot,graph,body):
    if (not isinstance(body,dict) or set(body)!={'ticket_node_id'} or not isinstance(body['ticket_node_id'],str) or not 1<=len(body['ticket_node_id'])<=100):
        raise ApiFailure('BUSINESS_WARRANTY_INVALID','Select one saved complaint record; no policy or input overrides are accepted.',422)
    check_graph(snapshot,graph)
    ticket=next((r for r in graph['records'] if r['node_id']==body['ticket_node_id'] and r['collection']=='tickets' and r['role']=='service'),None)
    if not ticket:raise ApiFailure('BUSINESS_WARRANTY_TICKET_UNAVAILABLE','The selected complaint is not in this saved graph.',422)
    inputs=[observation(ticket,*item) for item in [
        ('engineNo','identifier','Complaint engine serial'),('oem','identifier','Complaint OEM account reference'),('oemOrg','identifier','Complaint OEM company reference'),
        ('complaintRecord.dateOfSale','date','Complaint sale date'),('complaintRecord.hmr','hours','Reported complaint hours'),
        ('hmr','hours','Alternate ticket hours'),('createdAt','date','Ticket creation date'),
    ]]
    by_field={i['field']:i for i in inputs}
    invoices=[]
    for record in graph['records']:
        if record['collection']!='enginedetails' or record['role']!='service':continue
        values=[observation(record,*item) for item in [
            ('engineSerialNumber','identifier','Invoice engine serial'),('oem','identifier','Invoice OEM reference'),('invoiceDate','date','Invoice date')]]
        invoices.append(dict(node_id=record['node_id'],collection=record['collection'],record_sha256=record['record_sha256'],observations=values,
            serial_comparison=comparison(by_field['engineNo'],values[0]),oem_comparison=comparison(by_field['oemOrg'],values[1]),identity='candidate_only',selected=False))
    reasons=[]
    def block(code,message):reasons.append(dict(code=code,message=message))
    block('POLICY_NOT_CONFIGURED','No complete applicable structured warranty policy is configured for this saved case. Policy version, effective dates, OEM/model scope, time basis, limits and exclusion handling remain required.')
    block('IDENTITY_UNRESOLVED','The complaint and invoice must be tied to the same physical engine with verified scope. Serial and OEM comparisons alone do not establish identity.')
    block('ASSESSMENT_TIME_UNSPECIFIED','An explicit assessment timestamp and policy date basis are required. Ticket creation time and today are not used by default.')
    for field,code,label in [('complaintRecord.dateOfSale','SALE_DATE','Complaint sale date'),('complaintRecord.hmr','COMPLAINT_HOURS','Reported complaint hours'),('engineNo','ENGINE_SERIAL','Complaint engine serial'),('oem','OEM_REFERENCE','Complaint OEM account reference'),('oemOrg','COMPANY_REFERENCE','Complaint OEM company reference')]:
        item=by_field[field]
        if not item['syntactically_usable']:block(code+'_UNUSABLE',label+' is '+item['state'].replace('_',' ')+' in this saved projection.')
    alternate=by_field['hmr'];primary=by_field['complaintRecord.hmr']
    if primary['syntactically_usable'] and alternate['syntactically_usable'] and Decimal(primary['normalized'])!=Decimal(alternate['normalized']):
        block('HOUR_OBSERVATIONS_DIFFER','Complaint and alternate ticket hours differ; they remain separate observations without choosing a replacement input.')
    if not invoices:block('NO_SAVED_INVOICE','No invoice record is available in this bounded graph; this is not database-wide absence.')
    if len(invoices)>1:block('MULTIPLE_INVOICE_CANDIDATES','Several saved invoices exist; none was selected automatically.')
    if invoices and not any(i['serial_comparison']=='exact_match' and i['oem_comparison']=='exact_match' for i in invoices):
        block('NO_EXACT_INVOICE_SCOPE','No saved invoice has an exact saved-value match for both the complaint serial and OEM company reference (oemOrg).')
    if invoices and not any(i['observations'][2]['syntactically_usable'] for i in invoices):block('INVOICE_DATES_UNUSABLE','No saved invoice has a parseable ISO invoice date; no date was inferred.')
    if any(o['truncated'] for o in graph['outcomes']):block('SOURCE_GRAPH_TRUNCATED','One or more source collections were truncated; candidate coverage is incomplete.')
    if graph['validation']['status']=='failed':block('MAPPING_VALIDATION_FAILED','The saved graph has mapping/shape violations; structural checks do not establish business validity.')
    if graph['validation']['status']=='not_run':block('MAPPING_VALIDATION_NOT_RUN','No mapped-instance validation was run for this saved graph.')
    policy_sources=[dict(source_id=s['source_id'],title=s['title'],sha256=s['sha256'],kind=s['kind'],authority='not_established') for s in snapshot.get('sources',[]) if s['kind']=='policy' and 'warranty' in s['module_ids']]
    result=dict(version_id=snapshot['version_id'],graph_id=graph['graph_id'],ticket_node_id=ticket['node_id'],readiness_version=READINESS_VERSION,
        status='requires_review',status_label='Requires Review',eligibility='not_evaluated',business_policy_verified=False,
        inputs=inputs,invoice_candidates=invoices,selected_invoice_node_id=None,policy_sources=policy_sources,review_reasons=reasons,
        assessment_timestamp=None,policy_version=None,
        source_outcomes=[o for o in graph['outcomes'] if o['collection'] in ('tickets','enginedetails','claims','claimsftps')],
        limits=['Saved evidence only; no source database or model was queried.',
            'Syntactic input checks do not establish event accuracy, policy applicability or physical-engine identity. Identifier comparisons use saved public values; original BSON field types are not reconstructed.',
            'Complaint hours, alternate ticket hours and claim/inspection hours are separate observations; no fallback substitution is applied.',
            'Policy-kind documents are evidence references, not a configured or verified complete policy. Stored warranty flags and implementation limits are not policy authority.',
            'No threshold comparison, warranty exclusion evaluation or eligibility rule was executed. No record or decision was written.'],
        next_evidence=['Applicable policy version with effective period, OEM/model scope, coverage limits, time basis, boundary conventions and exclusion rules.',
            'Verified complaint-to-physical-engine and invoice association, including ambiguous or replaced engine handling.',
            'Explicit assessment timestamp and required sale/invoice/operating-hour observations with provenance.'],
        provenance=dict(graph_created_at=graph['created_at'],source_revisions=graph['source_revisions'],graph_sha256=sha256(canonical(graph).encode()).hexdigest(),definition_sha256=sha256(canonical(snapshot).encode()).hexdigest()),
        company_queries=0,model_calls=0,rules_executed=False)
    result['report_sha256']=sha256(canonical(result).encode()).hexdigest()
    return result


class BusinessWarranty:
    def __init__(self,ontology,graph):self.ontology=ontology;self.graph=graph
    def run(self,auth,version_id,graph_id,body):
        snapshot=self.ontology.version(auth,version_id);graph=self.graph.get(auth,version_id,graph_id)
        return prepare(snapshot,graph,body)
