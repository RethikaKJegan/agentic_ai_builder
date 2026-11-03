"""Build an unpublished Simpsons ontology from saved evidence, without cloud I/O.

Writes only a new isolated application database and explicit output artifacts.
No approval, publication, workflow planning or record retrieval is performed.
"""
from __future__ import annotations

import argparse
from collections import Counter
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import sqlite3
import sys

ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
from registry.safety import reject_secrets
from workflow_api.data_source_adapters import stable_id
from workflow_api.data_sources import DataSources
from workflow_api.ontology_model import validate_record, graph_errors, select_concepts
from workflow_api.ontology_foundation import MAX_RECORDS
from workflow_api.service import ApiFailure
from workflow_api.storage import WorkflowStore

REVIEW=ROOT/'docs/ontology-review/simpsons'
DEFINITIONS=ROOT/'ontology/simpsons'
SCOPE=('local-workspace','local-builder')
AUTH=dict(subject=dict(workspace_id=SCOPE[0],subject_id=SCOPE[1]),permissions=['tools.read','tools.assign'],decision='allow')


class OfflineAdapter:
    def profile(self,*args,**kwargs):raise AssertionError('Company I/O is prohibited in the draft builder.')
    def test(self,*args,**kwargs):raise AssertionError('Company I/O is prohibited in the draft builder.')


def digest(path):
    result=hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda:stream.read(1024*1024),b''):result.update(block)
    return result.hexdigest()


def cid(slug):return 'simpsons:concept:'+slug


def evidence():
    manifest=json.loads((REVIEW/'evidence-manifest.json').read_text())
    for entry in manifest['evidence']:
        if digest(REVIEW/entry['file'])!=entry['sha256']:raise ValueError('Review source hash changed; preserve original evidence.')
        if entry['business_policy_approved']:raise ValueError('Builder expects unapproved application-behaviour evidence.')
    return manifest


def load_catalogue(source):
    catalogue={};connections=[];snapshots=[];profiles=[]
    with sqlite3.connect(source.resolve().as_uri()+'?mode=ro',uri=True) as db:
        for workspace,owner,raw in db.execute('SELECT workspace,owner,document FROM data_source_connections WHERE workspace=? AND owner=?',SCOPE):
            connection=json.loads(raw)
            if 'simpson' not in connection.get('name','').lower():continue
            row=db.execute('SELECT document FROM data_source_snapshots WHERE connection_id=? AND revision=?',(connection['connection_id'],connection['metadata_revision'])).fetchone()
            if not row:raise ValueError('Connected source lacks its saved snapshot.')
            snapshot=json.loads(row[0]);connections.append((workspace,owner,connection));snapshots.append((connection['connection_id'],snapshot))
            for dataset in snapshot['datasets']:
                if dataset['name'] in catalogue:raise ValueError('Ambiguous collection name; qualify the source before building.')
                catalogue[dataset['name']]=dict(dataset, connection_id=connection['connection_id'])
            row=db.execute('SELECT document FROM ontology_source_profiles WHERE connection_id=?',(connection['connection_id'],)).fetchone()
            if row:profiles.append((connection['connection_id'],json.loads(row[0])))
    if not catalogue:raise ValueError('No saved Simpsons metadata available.')
    return catalogue,connections,snapshots,profiles


def apply_field_verification(catalogue,connections,snapshots,path):
    """Enrich only cloned local metadata; never approve semantics or source joins."""
    report=json.loads(Path(path).read_text())
    if report.get('business_policy_approved') is not False or report.get('source_writes')!=0 or report.get('ontology_published') is not False:
        raise ValueError('Expected unapproved read-only field verification evidence.')
    proofs={};changed=set()
    bson_types={'string':'string','int':'integer','long':'integer','double':'number','decimal':'number','bool':'boolean','date':'datetime','array':'array','object':'object','null':'null','objectId':'ObjectId'}
    definitions=json.loads((DEFINITIONS/'definitions.json').read_text())
    bindings=json.loads((DEFINITIONS/'field-bindings.json').read_text())
    allowed={(definitions['concepts'][slug][0],name) for slug,fields in bindings.items() for name in fields}
    for field in report['fields']:
        if field['status']!='observed_field':continue
        name,key=field['collection'],field['field']
        if (name,key) not in allowed or name not in catalogue:raise ValueError('Verification field is outside the draft scope.')
        if not 1<=field['matching_sample_count']<=25 or not field['observed_bson_types'] or any(t not in bson_types for t in field['observed_bson_types']):raise ValueError('Verification lacks bounded type evidence.')
        d=catalogue[name]
        if any(f['name']==key for f in d['fields']):raise ValueError('A verified field already has saved metadata; reconcile explicitly.')
        metadata=dict(field_id=stable_id(d['connection_id'],d['dataset_id'],key),name=key,
            types=sorted({bson_types[t] for t in field['observed_bson_types']}),discovery_method='sampled')
        d['fields'].append(metadata);changed.add(d['connection_id'])
        proofs[(name,key)]=dict(file=str(Path(path).resolve().relative_to(ROOT)),sha256=digest(path),
            checked_at=report['checked_at'],method=report['method'],matching_sample_count=field['matching_sample_count'],
            observed_bson_types=field['observed_bson_types'],reference_target_verified=False,business_policy_approved=False)
    for connection_id,snapshot in snapshots:
        if connection_id not in changed:continue
        snapshot['revision']+=1
        for d in snapshot['datasets']:
            if d['name'] in catalogue:d['fields']=deepcopy(catalogue[d['name']]['fields'])
        for _,_,connection in connections:
            if connection['connection_id']==connection_id:connection['metadata_revision']=snapshot['revision']
    return proofs


class Draft:
    def __init__(self,catalogue,manifest,technical_proofs=None):
        self.technical_proofs=technical_proofs or {}
        self.catalogue=catalogue;self.manifest=manifest;self.records=[];self.provenance={};self.gaps=[]
        self.definitions=json.loads((DEFINITIONS/'definitions.json').read_text())
        self.bindings=json.loads((DEFINITIONS/'field-bindings.json').read_text())
        self.source_coverage={};self.attributes={}

    def add(self,r,questions=(),classification='documented_current_application_behaviour',**details):
        validate_record(r);reject_secrets(r)
        if any(other['id']==r['id'] for other in self.records):raise ValueError('Duplicate stable record identity.')
        self.records.append(r)
        self.provenance[r['id']]=dict(classification=classification,source_questions=list(questions),
            review_evidence=[dict(file=x['file'],sha256=x['sha256']) for x in self.manifest['evidence']],
            independent_code_verification=False,record_level_reference_validation=False,business_policy_approved=False,**details)
        return r['id']

    @staticmethod
    def record(rid,kind,label,definition,layer='organization',refs=(),deps=(),domain=None,**properties):
        return dict(id=rid,kind=kind,layer=layer,domain=domain,label=label,definition=definition,
            dependencies=list(deps),source_refs=sorted(set(refs)),evidence_class='unverified_hypothesis',
            properties=dict(method='documented_current_application_behaviour',risk='high',**properties))

    def collection(self,slug):
        name=self.definitions['concepts'][slug][0]
        return self.catalogue.get(name) if name else None

    def field(self,slug,name):
        dataset=self.collection(slug)
        return next((f for f in dataset['fields'] if f['name']==name),None) if dataset else None

    def ref(self,slug,name=None):
        d=self.collection(slug);f=self.field(slug,name) if name else None
        return f['field_id'] if f else d['dataset_id'] if d else None

    def construct(self):
        for slug,definition in self.definitions['common'].items():
            self.add(self.record('simpsons:common:'+slug,'concept',slug.replace('_',' ').title(),definition,layer='common'),classification='ontology_design_definition')
        for slug,(domain,parent,definition) in self.definitions['domains'].items():
            self.add(self.record('simpsons:domain:'+slug,'concept',slug.replace('_',' ').title(),definition,layer='domain',domain=domain,deps=['simpsons:common:'+parent]),classification='provisional_domain_definition')
        for slug,(collection,parent,label,definition,questions) in self.definitions['concepts'].items():
            dataset=self.collection(slug)
            if collection and not dataset:raise ValueError('A mapped collection was not observed: '+collection)
            self.add(self.record(cid(slug),'concept',label,definition,refs=[dataset['dataset_id']] if dataset else [],deps=['simpsons:domain:'+parent]),questions,
                source_collection=collection,source_database=dataset.get('database') if dataset else None,source_binding='observed_collection' if dataset else 'logical_concept_without_resolved_physical_identity')
            if collection:self.source_coverage[collection]='business_concept'
        for slug,fields in self.bindings.items():
            questions=self.definitions['concepts'][slug][4]
            for name,meaning in fields.items():
                observed=self.field(slug,name);rid='simpsons:attribute:'+slug+':'+name
                types=set(observed['types'])-{'null'} if observed else set()
                datatype=next(iter(types)) if len(types)==1 else 'unknown'
                aliases={'text':'string','timestamp':'datetime','ObjectId':'string'}
                datatype=aliases.get(datatype,datatype)
                if datatype not in {'string','integer','number','boolean','date','datetime','object','array'}:datatype='unknown'
                refs=[observed['field_id']] if observed else []
                if not observed:
                    self.gaps.append(dict(record_id=rid,collection=self.definitions['concepts'][slug][0],field=name,status='not_observed_in_saved_sample',reason='Code-reported meaning is retained; no source field ID, type or matching value is invented.'))
                    meaning+=' Source field was not observed in the saved sample; binding remains unresolved.'
                proof=self.technical_proofs.get((self.definitions['concepts'][slug][0],name))
                if proof:
                    meaning=meaning.split('; not observed')[0].split('; absent from')[0].replace(' absent from current saved field sample.','.').replace(' not observed in current saved field sample.','.')
                    meaning+=' Field presence and type were observed by a targeted read-only probe; business interpretation and reference integrity remain unapproved.'
                self.add(self.record(rid,'attribute',name,meaning,refs=refs,source=cid(slug),datatype=datatype),questions,
                    source_collection=self.definitions['concepts'][slug][0],source_field=name,field_binding='observed_field' if observed else 'unresolved_code_report',observed_types=observed['types'] if observed else [],source_field_id=observed['field_id'] if observed else None,technical_verification=proof)
                self.attributes[(slug,name)]=rid
        for slug,(collection,parent,label,definition,questions) in self.definitions['concepts'].items():
            self.add(self.record('simpsons:mapping:'+slug,'mapping',label+' domain mapping',
                'Provisional interpretation linking the organization concept to a reusable domain definition; not a source join or approved business equivalence.',
                refs=[self.ref(slug)] if self.ref(slug) else [],source=cid(slug),target='simpsons:domain:'+parent),questions,classification='provisional_domain_mapping')
        for slug,source,target,predicate,label,method,left,right,questions in json.loads((DEFINITIONS/'relationships.json').read_text()):
            a=self.field(source,left) if left else None;b=self.field(target,right) if right else None
            refs=[x for x in (self.ref(source,left),self.ref(target,right)) if x]
            pairs=[dict(source_field_id=a['field_id'],target_field_id=b['field_id'])] if a and b else []
            definition=label+'. This is '+method.replace('_',' ')+', not an executable join grant. Business approval and record-level reference integrity are unconfirmed.'
            self.add(self.record('simpsons:relationship:'+slug,'relationship',label,definition,refs=refs,source=cid(source),target=cid(target),predicate=predicate,field_pairs=pairs),questions,
                reference_kind=method,source_field=left,target_field=right,field_pair_observed=bool(a and b),join_authorized=False)
        self.constraints()
        errors=graph_errors(self.records)
        if errors:raise ValueError('Draft graph validation failed: '+json.dumps(errors))
        if len(self.records)>MAX_RECORDS:raise ValueError('Draft exceeds native ontology record bound.')
        return self

    def constraint(self,slug,source,label,definition,questions,attribute=None,values=None,payload=None,**details):
        props=dict(source=cid(source));deps=[]
        if attribute:
            props['attribute']=self.attributes[(source,attribute)]
        if values is not None:props.update(rule='allowed_values',allowed_values=values)
        rid='simpsons:constraint:'+slug
        self.add(self.record(rid,'constraint',label,definition,refs=[self.ref(source)] if self.ref(source) else [],deps=deps,**props),questions,
            enforcement='documented_only_not_executable_policy',rule_payload=payload,**details)

    def constraints(self):
        dataset=self.collection('engine_invoice')
        observed=any(i.get('unique') and [c['name'] for c in i.get('columns',[])]==['oem','engineSerialNumber'] for i in dataset.get('indexes',[]))
        if not observed:raise ValueError('Required compound-index evidence was not found in saved metadata.')
        self.constraint('invoice_identity','engine_invoice','Invoice compound identity','Saved metadata has a unique index on billed-to company plus serial; this does not establish global serial uniqueness or unique physical identity.',[1],payload=dict(fields=['oem','engineSerialNumber'],source_index_observed=True,physical_engine_identity_resolved=False))
        self.constraint('ticket_status','ticket','Documented ticket statuses','Application status values; no approved transition policy is inferred.',[8,9,10],attribute='status',values=['OPENED','RESOLVED','CLOSED','REOPENED'])
        workflow=['ENTER_ENGINE_DETAILS','OUT_OF_WARRANTY','ASSIGN_SE','WAITING_FOR_SE_ACKNOWLEDGEMENT','ADD_INSPECTION_DATE','SUBMIT_JIR','UPDATE_ACTION_CODE','ACTION_CODE_UPDATED','PARTS_REPLACEMENT','PARTS_REPLACEMENT_REQ_SUBMITTED','ENGINE_REPLACEMENT_REQ_SUBMITTED','APPROVER_ASSIGNED','ENGINE_REPLACEMENT_APPROVED','ENGINE_REPLACEMENT_REJECTED']
        timeline=['REASSIGN_SE','UPDATE_DEFECT_CODE','ENGINE_REPLACEMENT','COMMENT','TICKET_UPDATED','ATTACHMENT','JIR_CREATED','FOC_CREATED','FOC_UPDATED','COMPLAINT_FORM_SUBMITTED','NO_STAGE']
        self.constraint('stage_categories','ticket','Workflow stages versus event labels','14 reported workflow-stage labels, 11 timeline-only labels and two unused labels. Not 27 sequential steps and not a fully verified transition graph.',[8],attribute='stage',payload=dict(workflow_labels=workflow,timeline_only=timeline,unused=['UNDER_WARRANTY','COMPLAINT_FORM_UPDATED'],transition_policy_complete=False))
        self.constraint('open_ticket_attempt','ticket','Attempted one-open-ticket check','Serial-only check for OPENED/REOPENED; races, admin submission and reopening can bypass it. Never assert guaranteed global uniqueness.',[10,11],payload=dict(match='serial_exact_text',blocking_statuses=['OPENED','REOPENED'],guaranteed=False))
        self.constraint('unregistered_serial','ticket','Unregistered serial path','A missing invoice-master match can enter ENTER_ENGINE_DETAILS and send an alert. Missing metadata does not prove a nonexistent physical engine.',[5])
        self.constraint('creator_ambiguity','ticket','Ambiguous actual creator','createdBy may contain a staff-account or OEM-account identifier. Do not pick an actor namespace or merge emails without evidence.',[14,43],attribute='createdBy')
        self.constraint('company_history','ticket','Historical ticket company','Ticket company is copied at creation and can differ from the account current company; current company must not rewrite ticket history.',[7],attribute='oemOrg')
        self.constraint('fiscal_year','ticket','Documented fiscal year basis','April–March fiscal year uses ticket creation date; replacement report uses this value rather than approval date. Timezone/boundary implementation remains unverified.',[50],attribute='financialYear',payload=dict(start_month=4,end_month=3,basis='ticket_creation',approved_business_policy=False))
        self.constraint('resolve_close_durations','ticket','Documented elapsed-day metrics','mttr/mttc are per-ticket whole days since creation to resolve/close and cleared on reopen. Do not treat field names alone as verified aggregate mean statistics.',[9,44])
        self.constraint('jir_single_record','jir','Documented single JIR','One JIR per ticket according to supplied code review; edits overwrite. Source index/record consistency is not independently verified here.',[18],attribute='status',values=['DRAFTED','PUBLISHED'])
        self.constraint('foc_status','foc','Documented FOC statuses','Reported form statuses; acronym and intended business meaning remain unconfirmed.',[19],attribute='focStatus',values=['SUBMITTED','REJECTED','COMPLETED'])
        self.constraint('replacement_serial_lineage','dispatch','Replacement serial lineage','Old serial is on the ticket and new serial on dispatch. Neither updating the invoice master nor choosing the correct later-ticket serial is guaranteed.',[22])
        self.constraint('dispatch_status','dispatch','Documented dispatch statuses','Reported dispatch statuses used by the supplied example; source record coverage is not a verified current dispatch result.',[50],attribute='status',values=['YET_TO_DISPATCH','ENGINE_DISPATCHED'])
        self.constraint('stock_condition','float_stock','Documented stock conditions','Reported stock condition labels, distinct from availability and ticket status.',[40],attribute='status',values=['NEW','DEFECTIVE','REPAIRED'])
        self.constraint('claim_separation','sap_claim','SAP and manual claims are not reconciled','Dashboards use SAP claims; source collections are never deduplicated by current application code. No cross-source equivalence is asserted.',[25,26,41])
        self.constraint('code_types','code','Documented controlled-code types','Current active code types; old unopened code connections are not valid automatic fallback sources.',[32],attribute='codeType',values=['COMPLAINT','DEFECT','ACTION'])
        self.constraint('cutin_comparison_defect','bulletin','Cut-in comparison is not trusted policy','Lexical serial comparison, inconsistent compared fields and first-plant-only logic are implementation limitations. Ordering and complete applicability must be validated before answering.',[2,33,50],payload=dict(serial_ordering='unconfirmed',current_lexical_comparison_is_defect=True,company_model_list_plant_scope_required=True))
        self.constraint('manual_effectiveness','manual','No verified effective-document selection','Newest release, approval status and archive are separate. Do not equate newest with approved/effective or infer supersession.',[35])
        self.constraint('faq_not_approved','faq','Editable FAQ is not approved guidance','No review fields; staff edits are not business validation of content.',[36])
        self.constraint('mis_not_live','mis','MIS denominator is not live sales','Unused zero fields and hardcoded sales do not provide live source-backed sales or verified performance metrics.',[41])
        self.constraint('training_participants','booking','Participants are not accounts','Participant names/details are entered independently; COMPLETED plus certificates implies attendance without an explicit attendance fact.',[38])
        self.constraint('role_visibility','role_flags','Documented role visibility, not access grants','OEM: own tickets; company admin: company tickets; primary engineer: assigned tickets; approver: assigned approvals; admin/float manager/quality admin: all tickets. Exposed endpoints are defects, never ontology access entitlements.',[17,48,49],payload=dict(business_policy_approved=False,existing_api_authorization_unchanged=True))
        self.constraint('warranty_code_only','engine_invoice','Documented warranty calculation, not approved policy','All three reported limits apply to ticket creation date; depot/dealer stock bypasses the check. Operators, month arithmetic, missing-value handling, label matching and physical-engine resolution remain unconfirmed. This is not executable policy.',[1,48],payload=dict(classification='documented_current_application_behaviour',reference_date='ticket_creation',requires_all_conditions=True,bypass=['depot_stock','dealer_stock'],thresholds=[dict(oem='TAFE',invoice_months=27,sale_months=24,hmr=2000),dict(oem='CNH',invoice_months=24,sale_months=21,hmr=2000),dict(oem='TEREX / Manitou',invoice_months=24,sale_months=18,hmr=2000),dict(oem='other',invoice_months=15,sale_months=12,hmr=1500)],operators=None,month_arithmetic=None,executable=False))
        for slug in ['engine_invoice','advance_dispatch','dispatch','manual_claim','float_stock','inventory']:
            self.constraint('currency_'+slug,slug,'Currency and amounts unresolved','No currency field is provided. Preserve stored numeric/text types; do not invent currency, implicit parsing, conversions or tax-inclusive totals.',[27])
        self.constraint('replacement_approval','replacement_request','Documented replacement approval','Single approver assigned by an admin; no amount/plant hierarchy is reported. This does not grant tools or assert an approved ontology policy. Written PENDING is reported outside the source allowed list.',[28,29],payload=dict(required_role='approver',assigned_by='admin',written_pending_enum_conflict=True,policy_approved=False))
        self.constraint('cross_connection_resolution','manual_revision','Explicit cross-connection lookup needed','Supplied review says matching UUID targets exist, but default same-connection population does not resolve them. Availability, access and actual record matches must be validated; no grant or verified link is inferred.',[43])
        self.constraint('quality_approval','part_analysis','Documented named quality approver','Named quality approver participates in current application flow. Actual actor lookup, governance and empty-schema fields remain unverified.',[28,43])
        self.constraint('freshness','inventory','No approved freshness threshold','Application polling schedules exist; acceptable source age is not business-defined. The foundation heuristic freshness window is not an approved staleness policy.',[47])


def question_previews(draft):
    specifications=[
      dict(id='engine_service_history',question='Full service history of engine X?',seeds=['engine','engine_invoice','ticket','oem_company','oem_account','timeline','comment','jir','foc','replacement_request','part_replacement','dispatch','manual_claim','sap_claim'],
        paths=['engine_invoice --billed_to--> oem_company','ticket --has_candidate_serial_match--> engine_invoice','timeline/jir/foc/replacements/dispatch --ticket ID--> ticket','claims --candidate serial text--> ticket'],
        guards=['Require an explicit authorized company/source scope. Do not reproduce cross-company past-history exposure.','Return candidate invoice identities rather than select the first serial match. Physical identity is unresolved.','Claims are unverified serial associations and must not be silently merged into verified service events.','Company billed at invoice is not current owner. Replacement serial differs from original complaint serial.']),
      dict(id='approved_replacements_dispatch',question='Engine replacements approved for company Y this financial year, and dispatch status?',seeds=['ticket','oem_company','oem_account','replacement_request','dispatch'],
        paths=['ticket.oemOrg --> company','ticket.engineReplacementStatus = APPROVED (code-reported field)','ticket.financialYear based on creation (April–March)','dispatch.ticketId --> ticket; dispatch.status'],
        guards=['engineReplacementStatus was not observed in the saved metadata sample; exact field binding must be verified.','Do not replace historical approval with current workflow stage as an assumed equivalent.','Use creation-based fiscal year for the documented application interpretation; approval-date policy is not confirmed.','No current counts or dispatch outcomes are computed.']),
      dict(id='open_tickets_before_bulletin_cutin',question='Which open tickets on model Z fall before a service-bulletin cut-in?',seeds=['ticket','oem_company','engine_model','bulletin','cut_in','code'],
        paths=['ticket status OPENED/REOPENED','bulletin company/model/list/plant scope versus ticket values','per-plant cut-in --> candidate ticket serial comparison'],
        guards=['Serial ordering is unconfirmed; plain text comparison is a documented defect. Do not compute a before/after answer.','Do not apply only the first plant cut-in. Company/model/list/plant mappings require validation.','Preserve field spellings and do not assume engineModal/model/engineModel or listNo/listNumber are interchangeable.','This preview identifies required evidence; no company records are retrieved.'])]
    results=[]
    for spec in specifications:
        chosen=select_concepts(draft.records,[cid(s) for s in spec.pop('seeds')])
        ids={r['id'] for r in chosen}
        if ('tickets','engineReplacementStatus') in draft.technical_proofs and spec['id']=='approved_replacements_dispatch':
            spec['guards'][0]='Field presence and string type were observed in a targeted read-only probe. Actual approval meaning and reference integrity are not thereby approved.'
        gaps=[g for g in draft.gaps if g['record_id'] in ids]
        results.append(dict(**spec,preview_only=True,publication_status='unpublished_draft',business_policy_approved=False,
            execution_ready=False,records_retrieved=0,workflow_executed=False,record_ids=sorted(ids),record_count=len(ids),
            layers=dict(Counter(r['layer'] for r in chosen)),mapping_gaps=gaps,
            semantic_relationships=[dict(id=r['id'],source=r['properties']['source'],predicate=r['properties']['predicate'],target=r['properties']['target'],reference_kind=draft.provenance[r['id']].get('reference_kind')) for r in chosen if r['kind']=='relationship']))
    return results


def build(source,output_database,output_dir,field_verification=None):
    source=Path(source).resolve();target=Path(output_database).resolve();out=Path(output_dir).resolve()
    allowed=(ROOT/'.local/ontology-foundation').resolve()
    if not target.is_relative_to(allowed) or target==source or target.exists():raise ValueError('Use a new database inside .local/ontology-foundation; existing databases are never replaced.')
    if not out.is_relative_to(ROOT) or out.exists():raise ValueError('Use a new artifact directory inside this repository.')
    source_before=digest(source)
    catalogue,connections,snapshots,profiles=load_catalogue(source)
    proofs=apply_field_verification(catalogue,connections,snapshots,field_verification) if field_verification else {}
    draft=Draft(catalogue,evidence(),proofs).construct();previews=question_previews(draft)
    # Source references must all resolve to real saved metadata IDs.
    source_ids={d['dataset_id'] for d in catalogue.values()}|{f['field_id'] for d in catalogue.values() for f in d['fields']}
    if any(set(r['source_refs'])-source_ids for r in draft.records):raise ValueError('A draft source reference is invented or unavailable.')
    target.parent.mkdir(parents=True,exist_ok=True)
    target.touch(mode=0o600,exist_ok=False)
    manager=DataSources(WorkflowStore(target),{},adapter=OfflineAdapter());foundation=manager.ontology_foundation
    used_fields={f['field_id'] for d in catalogue.values() for f in d['fields'] if f['field_id'] in {x for r in draft.records for x in r['source_refs']}}
    with manager.store.transaction() as db:
        for workspace,owner,c in connections:
            db.execute('INSERT INTO data_source_connections (connection_id,workspace,owner,secret,document) VALUES (?,?,?,?,?)',(c['connection_id'],workspace,owner,None,json.dumps(c)))
        for connection_id,snapshot in snapshots:db.execute('INSERT INTO data_source_snapshots (connection_id,revision,document) VALUES (?,?,?)',(connection_id,snapshot['revision'],json.dumps(snapshot)))
        for connection_id,profile in profiles:
            profile=deepcopy(profile)
            for d in profile.get('profiles',{}).values():
                d['fields']={k:v for k,v in d.get('fields',{}).items() if k in used_fields}
                d['composite_keys']=[]
            db.execute('INSERT INTO ontology_source_profiles (connection_id,document) VALUES (?,?)',(connection_id,json.dumps(profile)))
        refs,_=foundation.sources(db,SCOPE)
        for record in draft.records:
            foundation.import_record(db,SCOPE,deepcopy(record),refs,'simpsons_documented_behaviour_draft',evidence=draft.provenance[record['id']])
        stored=foundation.rows(db,'records',SCOPE)
        if graph_errors(stored) or any(r['status']!='draft' for r in stored):raise ValueError('Persisted draft validation failed.')
        if foundation.rows(db,'versions',SCOPE) or foundation.rows(db,'selections',SCOPE):raise ValueError('Draft must not be published or create approved selection manifests.')
    try:foundation.publish(AUTH,dict(revision=foundation.get(AUTH)['revision']))
    except ApiFailure as exc:
        if exc.code!='ONTOLOGY_INVALID':raise
    else:raise AssertionError('A draft-only graph was incorrectly published.')
    try:foundation.select(AUTH,dict(version_id='unpublished_simpsons_draft',concept_ids=[cid('ticket')]))
    except ApiFailure as exc:
        if exc.code!='ONTOLOGY_NOT_FOUND':raise
    else:raise AssertionError('Approved selection unexpectedly consumed a draft.')
    if digest(source)!=source_before:raise AssertionError('The saved input database changed during isolated construction.')
    coverage=[]
    operational={'backup_logs','filecheckers','jirlogs','ticketidcounters','mailinglists','tokens'}
    for name,d in sorted(catalogue.items()):
        classification=draft.source_coverage.get(name,'operational_metadata' if name in operational else 'unresolved_scope')
        coverage.append(dict(collection=name,database=d.get('database'),classification=classification,field_count=len(d['fields'])))
    report=dict(status='unpublished_descriptive_draft',business_policy_approved=False,source_database=str(source.relative_to(ROOT)),
        isolated_database=str(target.relative_to(ROOT)),source_database_sha256_before=source_before,source_database_sha256_after=digest(source),
        live_application_database_accessed=False,source_connections=len(connections),source_collections=len(catalogue),
        technically_verified_bindings=len(proofs),technical_field_evidence=[dict(collection=c,field=f,**p) for (c,f),p in sorted(proofs.items())],
        record_count=len(draft.records),kinds=dict(Counter(r['kind'] for r in draft.records)),layers=dict(Counter(r['layer'] for r in draft.records)),
        graph_errors=[],mapping_gaps=draft.gaps,source_coverage=coverage,preview_counts={p['id']:p['record_count'] for p in previews},
        published_versions=0,approved_records=0,calibration_labels_created=0,company_reads=0,company_writes=0,workflow_executions=0,
        credentials_copied=False,approved_api_rejects_draft=True,
        unresolved_business_topics=['physical_engine_identity','serial_normalization_and_ordering','account_person_or_shared_identity','intended_lifecycle_and_visibility','undefined_acronyms_and_measures','currency_and_tax_interpretation','warranty_boundary_operators_and_approval','effective_document_selection','freshness_limits','ontology_approver'])
    # Output only the curated schema/definitions, provenance and previews: no business rows or profile hashes.
    out.mkdir(parents=True,exist_ok=False)
    bundle=dict(schema_version=1,bundle_id='simpsons-draft-'+hashlib.sha256(json.dumps(draft.records,sort_keys=True).encode()).hexdigest()[:24],
        status='draft',classification='documented_current_application_behaviour',business_policy_approved=False,
        records=draft.records,provenance=draft.provenance,review_evidence=draft.manifest['evidence'])
    for filename,value in [('ontology.json',bundle),('question-previews.json',previews),('validation.json',report)]:
        (out/filename).write_text(json.dumps(value,indent=2,allow_nan=False)+'\n')
    write_readme(out,bundle,previews,report)
    return report


def write_readme(out,bundle,previews,report):
    by_id={r['id']:r for r in bundle['records']}
    lines=['# Simpsons ontology draft','', '**Status: unpublished, documented application behaviour; business policy is not approved.**','',
        'Built from saved metadata, the supplied review answers and any separately recorded read-only technical field evidence. This construction performs no company query or write. No workflow was planned or run.','',
        f"Records: {report['record_count']}. Layers: {report['layers']}. Collection coverage: {report['source_collections']}.",'',
        '## Business concepts','', '| Concept | Collection | Meaning |','| --- | --- | --- |']
    for r in bundle['records']:
        if r['kind']=='concept' and r['layer']=='organization':
            provenance=bundle['provenance'][r['id']]
            lines.append('| '+r['label']+' | '+str(provenance.get('source_collection') or 'Logical concept; no verified source identity')+' | '+r['definition']+' |')
    lines+=['','## Main relationships','', 'These arrows describe the draft meaning, not approved joins or access grants.','', '```mermaid','flowchart LR',
        '  Account[OEM login account] -->|belongs to| Company[OEM company]',
        '  Invoice[Engine invoice record] -->|billed to| Company',
        '  Ticket[Service ticket] -->|filed under| Account',
        '  Ticket -->|company at creation| Company',
        '  Ticket -.->|candidate serial match only| Invoice',
        '  Timeline[Timeline event] -->|ticket ID| Ticket',
        '  JIR[Inspection report] -->|ticket ID| Ticket',
        '  FOC[FOC form] -->|ticket ID| Ticket',
        '  Request[Replacement request] -->|ticket ID| Ticket',
        '  Dispatch[Replacement dispatch] -->|ticket ID| Ticket',
        '  Claim[Claim line] -.->|unverified serial match| Ticket','```','',
        '## Three question previews','', 'These demonstrate concept/dependency selection only. They are not record answers, runtime manifests or published ontology versions.']
    for p in previews:
        labels=[by_id[rid]['label'] for rid in p['record_ids'] if by_id[rid]['kind']=='concept' and by_id[rid]['layer']=='organization']
        lines+=['','### '+p['question'],'',f"Selected {p['record_count']} records. Business concepts: "+', '.join(labels)+'.','', 'Required checks:']
        lines+=['','\n'.join('- '+g for g in p['guards'])]
        if p['mapping_gaps']:lines+=['', 'Unobserved source fields: '+', '.join(g['collection']+'.'+g['field'] for g in p['mapping_gaps'])+'.']
    lines+=['','## Unresolved bindings','', 'A missing sampled field is not proof that the source schema lacks it. Code-reported fields remain explicit unresolved bindings; no source IDs or types are invented.','',
        '| Collection | Field | Status |','| --- | --- | --- |']
    lines+=['| '+g['collection']+' | '+g['field']+' | '+g['status']+' |' for g in report['mapping_gaps']]
    lines+=['','## Artifacts','', '- `ontology.json`: native records and per-record review/source provenance.','- `question-previews.json`: the three bounded ontology-only previews.','- `validation.json`: validation, source coverage, unresolved bindings and isolation evidence.','',
        'The isolated database path is recorded in validation.json. It has no copied connector credentials. Approved ontology APIs still reject use/publication of these draft records. Business review, actual reference integrity, calibration and approved publication remain separate gates.','']
    (out/'README.md').write_text('\n'.join(lines))


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--field-verification',type=Path,help='Optional bounded technical evidence; does not approve business semantics.')
    parser.add_argument('--source',type=Path,default=ROOT/'.local/ontology-foundation/simpsons-check.sqlite3')
    parser.add_argument('--database',type=Path,default=ROOT/'.local/ontology-foundation/simpsons-domain-draft.sqlite3')
    parser.add_argument('--output',type=Path,default=ROOT/'docs/ontology-review/simpsons/draft')
    args=parser.parse_args()
    print(json.dumps(build(args.source,args.database,args.output,args.field_verification),indent=2))


if __name__=='__main__':main()
