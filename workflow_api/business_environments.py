"""Owner-scoped immutable evidence releases and detailed connected scenarios."""
from copy import deepcopy
from datetime import date, timedelta
import json
from .business_knowledge_model import canonical,digest
from .business_coverage import coverage,FINGERPRINT,TASKS,DATA
from .business_ontology import identity
from .investigation_graph import fail

VERSION='business-evidence-environment-v1'
VARIANTS=('complete','negative_decision','rejected_authorization','expired_policy','missing_inspection','conflicting_identity','missing_exclusions','invalid_dates','ambiguous_policy','missing_authorization','conflicting_evidence','confirmed_exclusion')


def combined(evidences):
    result=deepcopy(evidences[0]);records={};edges={}
    for e in evidences:
        for r in e['records']:
            key=r['record_id']
            if key in records:
                for mid,value in r['values'].items():
                    if mid in records[key]['values'] and records[key]['values'][mid]!=value:raise ValueError('Conflicting source snapshots cannot be merged')
                    records[key]['values'][mid]=deepcopy(value)
                records[key]['fields'].update(deepcopy(r['fields']))
            else:records[key]=deepcopy(r)
        for edge in e.get('reference_edges',[]):edges[digest(edge)]=deepcopy(edge)
    result['records']=list(records.values());result['reference_edges']=list(edges.values())
    result['captured_requests']=list(dict.fromkeys(e['request_id'] for e in evidences))
    return result


def build_case(evidences,variant='complete',parameters=None):
    if variant not in VARIANTS:raise ValueError('Unknown case variant')
    merged=combined(evidences);tickets=[r for r in merged['records'] if r['collection']=='tickets'];reports=[r for r in merged['records'] if r['collection']=='jointinspectionreports']
    if len(tickets)!=1 or not reports:raise ValueError('Choose a source case with one complaint and a supported linked inspection')
    ticket=tickets[0];report=reports[0];source_id=ticket['record_id'];cid='case_'+digest([source_id,variant])[:20]
    def observed(mid):
        return next((v['value'] for r in merged['records'] for k,v in r.get('values',{}).items() if k=='mapping:'+mid and v.get('state')=='value'),None)
    serial=observed('ticket_serial')
    if not serial:raise ValueError('A source engine serial is required')
    observed_day=observed('inspection_date') or observed('inspection_failure_date')
    if not observed_day:raise ValueError('Choose a case with an interpretable source inspection day')
    assessment=date.fromisoformat(str(observed_day)[:10])+timedelta(days=1);day=assessment.isoformat();at=day+'T12:00:00+00:00'
    # Scenario assessment is explicitly after known commercial dates, not an
    # implicit replacement for any recorded complaint or failure date.
    for value in (observed('invoice_date'),observed('sale_date')):
        try:assessment=max(assessment,date.fromisoformat(str(value)[:10])+timedelta(days=1))
        except (TypeError,ValueError):pass
    day=assessment.isoformat();at=day+'T12:00:00+00:00'
    source_refs=[dict(record_id=source_id,source_reference=ticket['source_reference'],read_at=ticket['read_at'],sha256=digest(ticket)),dict(record_id=report['record_id'],source_reference=report['source_reference'],read_at=report['read_at'],sha256=digest(report))]
    source_refs.extend(dict(record_id=r['record_id'],source_reference=r['source_reference'],read_at=r['read_at'],sha256=digest(r)) for r in merged['records'] if r['collection']=='enginedetails')
    params=parameters or dict(sale_months=24,invoice_months=36,max_hours=2500)
    records=[]
    def add(kind,data,origin='generated',basis='Scenario event for unavailable business evidence'):
        item=dict(record_id=cid+':'+kind,case_id=cid,kind=kind,revision=1,observed_at=at,provenance=dict(kind=origin,basis=basis,source_references=deepcopy(source_refs)),data=data)
        records.append(item);return item
    # Valid retrieved invoice dates are retained. Missing dates are separate
    # generated observations, never corrections to original company values.
    inv_day=observed('invoice_date');sale_day=observed('sale_date')
    def usable(value):
        try:return date.fromisoformat(str(value)[:10]).isoformat()
        except (TypeError,ValueError):return None
    invoice_records=[r for r in merged['records'] if r['collection']=='enginedetails']
    source_invoice=next((r for r in invoice_records if all(r.get('values',{}).get('mapping:'+key,{}).get('state')=='value' for key in ('invoice_serial','invoice_date','sale_date')) and str(r['values']['mapping:invoice_serial']['value'])==str(serial) and usable(r['values']['mapping:invoice_date']['value'])==usable(inv_day) and usable(r['values']['mapping:sale_date']['value'])==usable(sale_day)),None)
    real_invoice=source_invoice is not None and len(invoice_records)==1 and bool(usable(inv_day) and usable(sale_day))
    inv=add('invoice',dict(engine_serial=str(serial),invoice_date=usable(inv_day) or (assessment-timedelta(days=100)).isoformat(),sale_date=usable(sale_day) or (assessment-timedelta(days=60)).isoformat()),'source' if real_invoice else 'generated','Normalized retrieved invoice dates' if real_invoice else 'Scenario invoice supplies unavailable or ambiguous association/date evidence; original candidates are retained')
    ident=add('identity',dict(engine_serial=str(serial),complaint_id=source_id,inspection_ids=[report['record_id']],invoice_id=inv['record_id'],oem=str(observed('complaint_oem') or ticket['fields'].get('oemOrg') or 'scenario-oem'),model=str(ticket['fields'].get('engineModal') or 'scenario-model'),confirmed=True))
    policy=add('policy',dict(policy_key='scenario-coverage',revision=1,effective_from=(assessment-timedelta(days=365)).isoformat(),effective_to=(assessment+timedelta(days=365)).isoformat(),oems=[ident['data']['oem']],models=[ident['data']['model']],coverage_mode='sale_invoice_and_hours',sale_months=params['sale_months'],invoice_months=params['invoice_months'],max_hours=params['max_hours'],exclusions=['misuse','service_noncompliance']))
    engineer_id=next((r['record_id'] for r in merged['records'] if r['collection']=='users'),cid+':scenario-engineer')
    technical=add('technical_decision',dict(engine_serial=str(serial),inspection_id=report['record_id'],disposition='engine_replacement',reason='Scenario technical disposition linked to the recorded inspection; not an official Simpson diagnosis.',engineer_id=engineer_id,decided_at=day,diagnosis_verified=False))
    auth=add('authorization',dict(engine_serial=str(serial),technical_id=technical['record_id'],decision='approved',payment_category='goodwill',authority_role='scenario-commercial-authority',required_role='scenario-commercial-authority',decided_at=day,valid_until=(assessment+timedelta(days=30)).isoformat(),revoked=False))
    exclusion=add('exclusion_assessment',dict(engine_serial=str(serial),policy_id=policy['record_id'],assessed_at=day,checks=[dict(exclusion=name,applies=False,evidence='Recorded scenario review result for '+name) for name in policy['data']['exclusions']]))
    inputs=dict(assessment_date=day,policy_id=policy['record_id'])
    if variant in ('negative_decision','rejected_authorization'):auth['data']['decision']='rejected'
    if variant=='negative_decision':technical['data']['disposition']='no_replacement'
    if variant=='expired_policy':policy['data']['effective_to']=(assessment-timedelta(days=1)).isoformat()
    if variant=='missing_inspection':
        merged['records']=[r for r in merged['records'] if r['collection']!='jointinspectionreports'];merged['reference_edges']=[]
    if variant=='conflicting_identity':ident['data']['engine_serial']='conflicting-'+str(serial)
    if variant=='missing_exclusions':records.remove(exclusion)
    if variant=='invalid_dates':
        inv['data']['invoice_date']='2025-99-99';inv['provenance'].update(kind='generated',basis='Deliberately invalid scenario date; original invoice observations remain unchanged')
    if variant=='ambiguous_policy':
        extra=deepcopy(policy);extra['record_id']+=':alternative';extra['data']['max_hours']+=1;records.append(extra);inputs.pop('policy_id')
    if variant=='missing_authorization':records.remove(auth)
    if variant=='conflicting_evidence':
        extra=deepcopy(auth);extra['record_id']+=':conflicting';extra['data']['decision']='rejected';records.append(extra)
    if variant=='confirmed_exclusion':exclusion['data']['checks'][0]['applies']=True
    expected={task:'ready' for task in TASKS}
    if variant=='missing_inspection':expected={task:'insufficient_evidence' for task in TASKS}
    if variant=='conflicting_identity':expected.update(warranty='conflicting_evidence',replacement='conflicting_evidence')
    if variant=='missing_exclusions':expected['warranty']='insufficient_evidence'
    if variant=='invalid_dates':expected.update(warranty='insufficient_evidence',replacement='insufficient_evidence')
    if variant=='ambiguous_policy':expected['warranty']='conflicting_evidence'
    if variant=='missing_authorization':expected['replacement']='insufficient_evidence'
    if variant=='conflicting_evidence':expected['replacement']='conflicting_evidence'
    return dict(case_id=cid,label=variant.replace('_',' ').title()+' · '+str(ticket['fields'].get('_id',source_id)),variant=variant,source_identifiers=dict(complaint_id=str(ticket['fields']['_id'])),evidence=merged,business_records=records,inputs=inputs,expected=expected,provenance=dict(kind='mixed_scenario',source_references=source_refs,generated_records=[r['record_id'] for r in records if r['provenance']['kind']=='generated']))


def case_coverage(case,task,inputs=None,revoked=()):
    configured={**case['inputs'],**(inputs or {})}
    result=coverage(task,case['evidence'],configured,case['business_records'],case['case_id'],revoked)
    if task not in TASKS and task!='complaints':result.update(state='unsupported',conclusion_ready=False)
    return result


def build_release(cases,knowledge):
    if not cases or len(cases)>60 or len({c['case_id'] for c in cases})!=len(cases):raise ValueError('Choose 1–60 distinct connected cases')
    validations=[]
    for case in cases:
        for task in TASKS:
            result=case_coverage(case,task);actual=result['state'];expected=case['expected'][task]
            if (expected=='ready' and actual not in ('ready','ready_with_limitations')) or expected!='ready' and expected!=actual:
                raise ValueError('Unexpected coverage for '+case['case_id']+'/'+task+': '+actual+' expected '+expected)
            validations.append(dict(case_id=case['case_id'],task=task,state=actual,expected=expected,passed=True,mandatory_gaps=[g['fact_id'] for g in result['blocking_requirements']],outcomes=result['business_outcomes']))
    manifest=dict(schema_version=VERSION,ontology_version=knowledge['version_id'],ontology_sha256=knowledge['knowledge_sha256'],mapping_version=digest(knowledge['knowledge']['source_mappings']),provider_fingerprint=FINGERPRINT,task_contract_version='business-coverage-v1',policy_revisions=[dict(record_id=r['record_id'],revision=r['revision'],sha256=digest(r)) for c in cases for r in c['business_records'] if r['kind']=='policy'],case_ids=[c['case_id'] for c in cases],supported_tasks=list(TASKS),validation_results=validations,coverage_status='validated_for_declared_cases_and_tasks',provenance='mixed_source_and_generated_scenario',known_limitations=['Generated records are scenario evidence, not company approvals or verified physical identity.','Snapshot observations preserve their original read times; they do not claim current company state.','QA, corrective actions and recurrence remain outside this release.'])
    result=dict(manifest=manifest,cases=deepcopy(cases));result['dataset_id']='dataset_'+digest(result)[:24];result['sha256']=digest(result)
    return result


class BusinessEnvironments:
    def __init__(self,service):
        self.service,self.store=service,service.store
        self._cache={}
        with self.store.transaction() as db:
            db.execute('CREATE TABLE IF NOT EXISTS business_evidence_environments (workspace TEXT NOT NULL,owner TEXT NOT NULL,dataset_id TEXT NOT NULL,document TEXT NOT NULL,PRIMARY KEY(workspace,owner,dataset_id))')
            db.execute('CREATE TABLE IF NOT EXISTS business_evidence_revocations (workspace TEXT NOT NULL,owner TEXT NOT NULL,dataset_id TEXT NOT NULL,record_id TEXT NOT NULL,reason TEXT NOT NULL,PRIMARY KEY(workspace,owner,dataset_id,record_id))')
    def install(self,auth,release):
        auth,scope=self.service.authorize(auth)
        if 'workflow.edit' not in auth.get('permissions',[]) or 'workspace:write' not in auth.get('scopes',[]):fail('Environment installation requires workflow.edit and workspace write.','INVESTIGATION_DENIED',403)
        from registry.safety import reject_secrets
        reject_secrets(release)
        expected=build_release(release['cases'],self.service.ontology.version(auth,release['manifest']['ontology_version']))
        if expected!=release:fail('Coverage release does not reproduce its manifest.','EVIDENCE_RELEASE_INVALID',422)
        for case in release['cases']:
            snapshots=[]
            for rid in case['evidence'].get('captured_requests',[]):
                saved=self.service.retrieval.inspect(auth,rid)
                if saved['version_id']!=release['manifest']['ontology_version'] or 'evidence' not in saved:fail('Owned source evidence is unavailable.','EVIDENCE_SOURCE_INVALID',422)
                snapshots.append(saved['evidence'])
            if not snapshots:fail('A release requires owned captured source requests.','EVIDENCE_SOURCE_INVALID',422)
            original=combined(snapshots);allowed={r['record_id']:r for r in original['records']}
            if any(r!=allowed.get(r['record_id']) for r in case['evidence']['records']):fail('Scenario changed an original source observation.','EVIDENCE_SOURCE_INVALID',422)
            if any(e not in original['reference_edges'] for e in case['evidence'].get('reference_edges',[])):fail('Unsupported source relationship.','EVIDENCE_SOURCE_INVALID',422)
            for record in case['business_records']:
                for ref in record['provenance']['source_references']:
                    if ref.get('record_id') not in allowed or digest(allowed[ref['record_id']])!=ref.get('sha256'):fail('Evidence provenance is not bound to the captured case.','EVIDENCE_SOURCE_INVALID',422)
                if record['provenance']['kind']=='source':
                    if record['kind']!='invoice':fail('No registered source mapping for this business record kind.','EVIDENCE_SOURCE_INVALID',422)
                    linked=[r for r in original['records'] if r['collection']=='enginedetails' and all(r.get('values',{}).get('mapping:'+mid,{}).get('state')=='value' and str(r['values']['mapping:'+mid]['value'])[:10 if key.endswith('date') else None]==str(record['data'][key]) for key,mid in [('invoice_date','invoice_date'),('sale_date','sale_date'),('engine_serial','invoice_serial')])]
                    if len(linked)!=1:fail('A source invoice must resolve to one complete native record.','EVIDENCE_SOURCE_INVALID',422)
                    for key,mid in [('invoice_date','invoice_date'),('sale_date','sale_date'),('engine_serial','invoice_serial')]:
                        observed={str(r['values']['mapping:'+mid]['value'])[:10] if key.endswith('date') else str(r['values']['mapping:'+mid]['value']) for r in original['records'] if r.get('values',{}).get('mapping:'+mid,{}).get('state')=='value'}
                        if str(record['data'][key]) not in observed:fail('Source-qualified invoice value differs from captured evidence.','EVIDENCE_SOURCE_INVALID',422)
        with self.store.transaction() as db:
            db.execute('INSERT INTO business_evidence_environments VALUES (?,?,?,?) ON CONFLICT(workspace,owner,dataset_id) DO NOTHING',(*scope,release['dataset_id'],canonical(release)))
        return self.get(auth,release['dataset_id'])['manifest']
    def get(self,auth,dataset_id,internal=False):
        auth,scope=self.service.authorize(auth)
        with self.store.transaction(write=False) as db:row=db.execute('SELECT document FROM business_evidence_environments WHERE workspace=? AND owner=? AND dataset_id=?',(*scope,dataset_id)).fetchone()
        if not row:fail('Evidence environment not found.','EVIDENCE_ENVIRONMENT_NOT_FOUND',404)
        cached=self._cache.get((*scope,dataset_id))
        if cached and cached[0]==row[0]:return cached[1] if internal else deepcopy(cached[1])
        release=json.loads(row[0]);stored=release.pop('sha256')
        if digest(release)!=stored:fail('Environment integrity check failed.','EVIDENCE_ENVIRONMENT_CHANGED',409)
        release['sha256']=stored
        if release['manifest']['provider_fingerprint']!=FINGERPRINT:fail('Coverage provider changed; prepare a new release.','EVIDENCE_ENVIRONMENT_STALE',409)
        if len(self._cache)>=8:self._cache.clear()
        self._cache[(*scope,dataset_id)]=(row[0],release)
        return release if internal else deepcopy(release)
    def list(self,auth):
        auth,scope=self.service.authorize(auth)
        with self.store.transaction(write=False) as db:rows=db.execute('SELECT document FROM business_evidence_environments WHERE workspace=? AND owner=? ORDER BY rowid DESC',scope).fetchall()
        releases=[json.loads(row[0]) for row in rows]
        return dict(items=[dict(dataset_id=r['dataset_id'],manifest=r['manifest'],cases=[dict(**{k:c[k] for k in ('case_id','label','source_identifiers','inputs','variant')},policy_candidates=[dict(policy_id=p['record_id'],title='Scenario policy · '+p['data']['policy_key']+' · revision '+str(p['revision'])) for p in c['business_records'] if p['kind']=='policy']) for c in r['cases']]) for r in releases if r['manifest']['provider_fingerprint']==FINGERPRINT])
    def selected(self,auth,context):
        if not isinstance(context,dict) or set(context)!={'dataset_id','case_id'}:fail('Select dataset_id and case_id only.')
        release=self.get(auth,context['dataset_id'],internal=True);case=next((c for c in release['cases'] if c['case_id']==context['case_id']),None)
        if not case:fail('Case is outside the selected environment.','EVIDENCE_CASE_NOT_FOUND',404)
        return release,case
    def revoked(self,auth,dataset_id):
        _,scope=self.service.authorize(auth)
        with self.store.transaction(write=False) as db:return [r[0] for r in db.execute('SELECT record_id FROM business_evidence_revocations WHERE workspace=? AND owner=? AND dataset_id=?',(*scope,dataset_id)).fetchall()]
    def revoke(self,auth,dataset_id,record_id,reason):
        auth,scope=self.service.authorize(auth)
        if 'workflow.edit' not in auth.get('permissions',[]) or 'workspace:write' not in auth.get('scopes',[]):fail('Revocation requires workflow.edit and workspace write.','INVESTIGATION_DENIED',403)
        release=self.get(auth,dataset_id)
        if not any(record_id==r['record_id'] for c in release['cases'] for r in c['business_records']):fail('Record not found.','EVIDENCE_RECORD_NOT_FOUND',404)
        if not isinstance(reason,str) or not 1<=len(reason)<=500:fail('Provide a revocation reason.')
        with self.store.transaction() as db:db.execute('INSERT INTO business_evidence_revocations VALUES (?,?,?,?,?) ON CONFLICT(workspace,owner,dataset_id,record_id) DO UPDATE SET reason=excluded.reason',(*scope,dataset_id,record_id,reason))
        return dict(record_id=record_id,revoked=True)
