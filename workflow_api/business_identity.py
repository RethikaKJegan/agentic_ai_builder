"""Typed saved-record associations; no physical-engine identity invention."""
from hashlib import sha256
from pathlib import Path
import re
from .business_compiler import canonical
from .business_intelligence import check_graph
from .business_warranty import observation
from .service import ApiFailure

RESOLVER_VERSION='simpson-associations-v1'
BASIS=Path(__file__).resolve().parents[1]/'ontology/business-reference/identity-basis.json'
REFERENCE_FIELDS={('tickets','oems'):'oem',('tickets','oemnames'):'oemOrg',('oems','oemnames'):'oemNameId',('enginedetails','oemnames'):'oem',
 ('jointinspectionreports','tickets'):'ticketId',('enginereplacements','tickets'):'ticket',('partreplacements','tickets'):'ticket',('floatengines','tickets'):'ticketId',('focs','tickets'):'ticket'}
CANDIDATES={'enginedetails':('engineSerialNumber','engineModel'),'claims':('engineSerialNumber',None),'claimsftps':('engineSerialNumber',None),'failedengineanalyses':('engineSerialNumber','engineModel')}


def evidence(record,field,label=None):
    item=observation(record,field,'identifier',label or field)
    cell=next((f for f in record['fields'] if f['name']==field),{})
    item['native_token']=cell.get('native_token');return item


def compare_fields(left,right):
    if not left['syntactically_usable'] or not right['syntactically_usable']:return 'unavailable'
    if left['native_token'] and right['native_token']:
        return 'match' if left['native_token']==right['native_token'] else 'different'
    if type(left['value']) is not type(right['value']) or left['value']!=right['value']:return 'different'
    return 'public_match_unverified_types'


def resolve(snapshot,graph,body):
    if not isinstance(body,dict) or set(body)!={'ticket_node_id'} or not isinstance(body['ticket_node_id'],str) or not 1<=len(body['ticket_node_id'])<=100:
        raise ApiFailure('BUSINESS_IDENTITY_INVALID','Select one saved complaint without identity overrides.',422)
    check_graph(snapshot,graph)
    if any('native_token' in f and (not isinstance(f['native_token'],str) or not re.fullmatch(r'[a-f0-9]{64}',f['native_token'])) for record in graph['records'] for f in record['fields']):
        raise ApiFailure('BUSINESS_IDENTITY_INVALID','Saved native identifier evidence is invalid.',422)
    records={r['node_id']:r for r in graph['records']}
    ticket=records.get(body['ticket_node_id'])
    if not ticket or ticket['collection']!='tickets' or ticket['role']!='service':raise ApiFailure('BUSINESS_IDENTITY_TICKET','The selected service complaint is unavailable.',422)
    direct=[];rejected=[]
    for edge in graph['edges']:
        if edge['classification']!='source_reference':continue
        source=records[edge['source']];target=records[edge['target']];field=REFERENCE_FIELDS.get((source['collection'],target['collection']))
        if not field or source['role']!='service' or target['role']!='service' or source['connection_id']!=target['connection_id'] or edge.get('source_field',field)!=field:
            rejected.append(dict(source=edge['source'],target=edge['target'],reason='unsupported_reference_path'));continue
        left=evidence(source,field);right=evidence(target,'_id');comparison=compare_fields(left,right)
        if comparison=='different':rejected.append(dict(source=edge['source'],target=edge['target'],reason='reference_field_conflict'));continue
        # Legacy saved edges were established by the original typed builder but
        # lack tokens to recheck here. Keep the distinction visible.
        direct.append(dict(source=edge['source'],target=edge['target'],source_field=field,source_collection=source['collection'],target_collection=target['collection'],
            verification='native_reference_checked' if comparison=='match' else 'saved_reference_unverified_types',evidence=[left,right]))
    def targets(node,collection):return {e['target'] for e in direct if e['source']==node and e['target_collection']==collection}
    company_direct=targets(ticket['node_id'],'oemnames');accounts=targets(ticket['node_id'],'oems')
    account_companies=set().union(*(targets(a,'oemnames') for a in accounts)) if accounts else set()
    conflicts=[]
    if len(company_direct)>1 or len(account_companies)>1 or company_direct and account_companies and company_direct!=account_companies:
        conflicts.append(dict(code='COMPANY_PATH_CONFLICT',message='Complaint company and account-to-company paths disagree or are ambiguous. No company was selected.'))
    companies=company_direct|account_companies
    serial=evidence(ticket,'engineNo','Complaint serial');model=evidence(ticket,'engineModal','Complaint model');candidates=[]
    for record in graph['records']:
        if record['collection'] not in CANDIDATES:continue
        serial_field,model_field=CANDIDATES[record['collection']];serial_value=evidence(record,serial_field);model_value=evidence(record,model_field) if model_field else None
        serial_check=compare_fields(serial,serial_value);model_check=compare_fields(model,model_value) if model_value else 'unavailable'
        org='unresolved_cross_source' if record['role']!='service' else 'unavailable'
        if record['collection']=='enginedetails' and record['role']=='service':
            invoice_companies=targets(record['node_id'],'oemnames')
            if companies and invoice_companies:org='same_company_record' if companies==invoice_companies and len(companies)==1 else 'different_company_record'
        qualified=record['collection']=='enginedetails' and serial_check=='match' and org=='same_company_record' and model_check!='different' and not conflicts
        candidates.append(dict(node_id=record['node_id'],collection=record['collection'],role=record['role'],serial_comparison=serial_check,model_comparison=model_check,company_alignment=org,
            classification='scope_supported_candidate' if qualified else 'unresolved_candidate',company_associations=[e for e in direct if e['source']==record['node_id'] and e['target_collection']=='oemnames'],evidence=[serial_value]+([model_value] if model_value else [])+[evidence(record,'oem','Source OEM observation')],record_sha256=record['record_sha256'],selected=False))
    children={e['source'] for e in direct if e['target']==ticket['node_id']};relevant={ticket['node_id']}|accounts|companies|children|{c['node_id'] for c in candidates}
    associated=[e for e in direct if e['source']==ticket['node_id'] or e['target']==ticket['node_id'] or e['source'] in accounts]
    replacements=[dict(node_id=node,observation=evidence(records[node],'replacementEngineNumber','Replacement dispatch serial'),identity='separate_observation') for node in sorted(children) if records[node]['collection']=='floatengines']
    supported=[c['node_id'] for c in candidates if c['classification']=='scope_supported_candidate']
    invoice_status='no_saved_invoices' if not any(c['collection']=='enginedetails' for c in candidates) else 'company_conflict' if conflicts else 'multiple_scope_supported_candidates' if len(supported)>1 else 'single_scope_supported_candidate' if supported else 'no_scope_supported_candidate'
    review=['Physical-engine identity remains unresolved. A source record reference or scoped serial candidate is not a permanent physical-engine identifier.',
        'Supplied code declares invoice uniqueness by OEM company and serial, but deployed index enforcement and historical identity are not verified.',
        'Cross-source claims and QA remain separate candidates; replacement serials are not merged with original engines.']
    if any(o['truncated'] for o in graph['outcomes']):review.append('Source rows or search domains were truncated; candidate coverage is incomplete.')
    if any(c['serial_comparison']=='public_match_unverified_types' for c in candidates):review.append('This snapshot lacks native identifier evidence for some comparisons; rebuild explicitly to collect it.')
    result=dict(resolver_version=RESOLVER_VERSION,version_id=snapshot['version_id'],graph_id=graph['graph_id'],ticket_node_id=ticket['node_id'],status='requires_review',physical_engine_identity='unresolved',eligibility='not_evaluated',
        ticket_evidence=[serial,model,evidence(ticket,'oem','OEM account reference'),evidence(ticket,'oemOrg','OEM company reference')],
        company_paths=dict(direct_company_nodes=sorted(company_direct),account_nodes=sorted(accounts),account_company_nodes=sorted(account_companies)),
        direct_associations=associated,rejected_references=rejected,candidates=candidates,invoice_resolution=invoice_status,scope_supported_invoice_nodes=supported,selected_invoice_node_id=None,
        conflicts=conflicts,replacement_context=replacements,unresolved_references=[u for u in graph['unresolved'] if u['node_id'] in relevant],source_outcomes=graph['outcomes'],review_reasons=review,
        provenance=dict(reference_basis_sha256=sha256(BASIS.read_bytes()).hexdigest(),graph_created_at=graph['created_at'],source_revisions=graph['source_revisions'],graph_sha256=sha256(canonical(graph).encode()).hexdigest(),definition_sha256=sha256(canonical(snapshot).encode()).hexdigest()),
        company_queries=0,model_calls=0,identity_merges=0,rules_executed=False)
    result['report_sha256']=sha256(canonical(result).encode()).hexdigest();return result


class BusinessIdentity:
    def __init__(self,ontology,graph):self.ontology=ontology;self.graph=graph
    def run(self,auth,version_id,graph_id,body):
        return resolve(self.ontology.version(auth,version_id),self.graph.get(auth,version_id,graph_id),body)
