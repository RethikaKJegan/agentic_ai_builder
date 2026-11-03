"""Immutable cited policy interpretations, never authoritative executable policy."""
from copy import deepcopy
from datetime import date
from hashlib import sha256
import json
import re
import secrets
from registry.safety import reject_secrets
from .business_compiler import canonical
from .business_documents import BusinessDocuments
from .business_ontology import identity
from .business_warranty import parse_date,parse_hours,prepare,observation
from .google_connections import now
from .service import ApiFailure

POLICY_SCHEMA='simpson-policy-draft-v2'
COMPARISON_VERSION='simpson-policy-comparison-v1'
CLAUSES={
 'source_version':('Source policy version','text',[]),
 'effective_from':('Effective from','date',[]),'effective_to':('Effective through','date',[]),
 'oem_references':('OEM reference values','list',[]),'models':('Engine model values','list',[]),
 'date_basis':('Effective-date basis','choice',['assessment_date','sale_date','invoice_date']),
 'effective_bounds':('Effective-date boundaries','choice',['inclusive','exclusive']),
 'sale_months':('Sale coverage months','integer',[]),'invoice_months':('Invoice coverage months','integer',[]),
 'max_hours':('Operating-hour limit','hours',[]),
 'coverage_boundaries':('Coverage boundary conventions','text',[]),'exclusions':('Exclusions and handling','text',[]),
 'coverage_mode':('Required coverage checks','choice',['sale_and_hours','invoice_and_hours','sale_invoice_and_hours']),
 'coverage_date_basis':('Coverage date basis','choice',['assessment_date']),
 'period_method':('Coverage month calculation','choice',['calendar_month_anniversary_clamped','calendar_month_difference']),
 'period_boundary':('Coverage period boundary','choice',['inclusive','exclusive']),
 'hours_boundary':('Operating-hour boundary','choice',['inclusive','exclusive']),
 'exclusion_mode':('Exclusion interpretation','choice',['checks_required','none_declared']),
 'exclusion_checks':('Required exclusion codes','list',[]),
}


def fail(message='Provide bounded policy clauses and exact supporting quotations.',code='BUSINESS_POLICY_INVALID',status=422):raise ApiFailure(code,message,status)
def digest(value):return sha256(canonical(value).encode()).hexdigest()
def specs():return [dict(clause_id=key,label=v[0],kind=v[1],choices=v[2]) for key,v in CLAUSES.items()]


def validate(body,source):
    policy=body.get('policy') if isinstance(body,dict) else None
    if (not isinstance(body,dict) or set(body)!={'request_key','expected_revision','policy'}
        or not isinstance(body['request_key'],str) or not re.fullmatch(r'[A-Za-z0-9_-]{8,100}',body['request_key'])
        or type(body['expected_revision']) is not int or not 0<=body['expected_revision']<40
        or not isinstance(policy,dict) or set(policy)!={'policy_key','title','source_id','clauses'}
        or not isinstance(policy['policy_key'],str) or not re.fullmatch(r'[a-z][a-z0-9_-]{2,59}',policy['policy_key'])
        or not isinstance(policy['title'],str) or not 1<=len(policy['title'].strip())<=160
        or not isinstance(policy['source_id'],str) or not 1<=len(policy['source_id'])<=160
        or not isinstance(policy['clauses'],dict) or set(policy['clauses'])!=set(CLAUSES)):fail()
    if not source or source['kind'] not in ('policy','application_code') or 'warranty' not in source['module_ids']:fail('Select an owned warranty policy or supplied application-code document.','BUSINESS_POLICY_SOURCE',403)
    if sha256(source['text'].encode()).hexdigest()!=source['sha256']:fail('Policy source hash mismatch.','BUSINESS_POLICY_SOURCE',409)
    try:reject_secrets(body)
    except Exception:fail('Remove credentials from policy inputs.','SENSITIVE_DATA_DETECTED')
    for key,(_,kind,choices) in CLAUSES.items():
        cell=policy['clauses'][key]
        if not isinstance(cell,dict) or set(cell)!={'value','quote'}:fail()
        value=cell['value'];quote=cell['quote']
        if value is None:
            if quote is not None:fail('An unknown clause must have null value and quotation.')
            continue
        if not isinstance(quote,str) or not 4<=len(quote)<=1200 or len(' '.join(quote.split()))<4 or ' '.join(quote.split()) not in ' '.join(source['text'].split()):fail('A clause quotation could not be matched to its policy document.')
        if kind=='text' and (not isinstance(value,str) or not 1<=len(value.strip())<=1200):fail()
        if kind=='date' and (not isinstance(value,str) or not re.fullmatch(r'[0-9]{4}-[0-9]{2}-[0-9]{2}',value) or not parse_date(value)):fail('Use an ISO calendar date for policy effectivity.')
        if kind=='choice' and (not isinstance(value,str) or value not in choices):fail()
        if kind=='integer' and (type(value) is not int or not 0<=value<=1200):fail('Month-limit draft values must be integers from 0 to 1200.')
        if kind=='hours' and (not isinstance(value,str) or parse_hours(value) is None):fail('Use a nonnegative plain-decimal hour-limit string.')
        if kind=='list' and (not isinstance(value,list) or not 1<=len(value)<=20 or any(not isinstance(v,str) or not 1<=len(v.strip())<=160 for v in value) or len(set(value))!=len(value) or any(v.strip()=='*' for v in value)):fail('Use distinct exact scope values, without wildcards or inferred aliases.')
    values={key:cell['value'] for key,cell in policy['clauses'].items()}
    if values['exclusion_checks'] is not None and any(not re.fullmatch(r'[a-z][a-z0-9_]{0,59}',code) for code in values['exclusion_checks']):fail('Use bounded lowercase exclusion codes, one per line.')
    if values['exclusion_mode']=='none_declared' and values['exclusion_checks'] is not None:fail('A no-exclusions declaration cannot include required exclusion checks.')
    if all(v is None for v in values.values()):fail('Supply at least one cited clause; leave other clauses explicitly unknown.')
    if values['effective_from'] and values['effective_to'] and values['effective_from']>values['effective_to']:fail('Effective start must not follow effective end.')
    return deepcopy(policy)


def checked(document):
    if document.get('sha256')!=digest({k:v for k,v in document.items() if k!='sha256'}) or sha256(document['source']['text'].encode()).hexdigest()!=document['source']['sha256']:
        fail('Saved policy evidence failed integrity validation.','BUSINESS_POLICY_INTEGRITY',409)
    return document


class BusinessPolicies:
    def __init__(self,ontology,graph,resolve):
        self.ontology=ontology;self.store=ontology.store;self.graph=graph;self.resolve=resolve
        with self.store.transaction() as db:
            db.execute('CREATE TABLE IF NOT EXISTS business_policy_heads (workspace TEXT NOT NULL,owner TEXT NOT NULL,policy_key TEXT NOT NULL,revision INTEGER NOT NULL,PRIMARY KEY(workspace,owner,policy_key))')
            db.execute('CREATE TABLE IF NOT EXISTS business_policy_versions (workspace TEXT NOT NULL,owner TEXT NOT NULL,policy_id TEXT NOT NULL,policy_key TEXT NOT NULL,revision INTEGER NOT NULL,request_key TEXT NOT NULL,fingerprint TEXT NOT NULL,document TEXT NOT NULL,PRIMARY KEY(workspace,owner,policy_id),UNIQUE(workspace,owner,policy_key,revision),UNIQUE(workspace,owner,request_key))')
    def authority(self,auth):
        scope=identity(auth,True);current=self.resolve(*scope) if self.resolve else auth
        if not current or current['subject']!=auth['subject']:fail('Current policy write authority is unavailable.','OPERATION_NOT_AUTHORIZED',403)
        identity(current,True);return scope
    def list(self,auth):
        scope=identity(auth)
        with self.store.transaction(write=False) as db:
            rows=db.execute('SELECT document FROM business_policy_versions WHERE workspace=? AND owner=? ORDER BY policy_key,revision DESC',scope).fetchall()
            sources=[{k:d[k] for k in ('source_id','title','sha256','kind')} for d in BusinessDocuments.rows(db,scope) if d['kind'] in ('policy','application_code') and 'warranty' in d['module_ids']]
        items=[]
        for row in rows:
            doc=checked(json.loads(row[0]));item={k:doc[k] for k in ('policy_id','policy_key','title','revision','created_at','sha256','missing_clauses','status')}
            item.update(interpretation_basis=doc.get('interpretation_basis','policy_statement'),implementation_reference=doc.get('implementation_reference'),coverage_limits={k:doc['clauses'][k]['value'] for k in ('invoice_months','sale_months','max_hours')});items.append(item)
        return dict(items=items,sources=sources,clause_specs=specs(),business_policy_verified=False)
    def get(self,auth,policy_id):
        scope=identity(auth)
        with self.store.transaction(write=False) as db:
            row=db.execute('SELECT document FROM business_policy_versions WHERE workspace=? AND owner=? AND policy_id=?',(*scope,policy_id)).fetchone()
        if not row:fail('Policy revision not found.','BUSINESS_POLICY_NOT_FOUND',404)
        return checked(json.loads(row[0]))
    def save(self,auth,body):
        scope=self.authority(auth)
        # Validate basic request shape before using fields in queries.
        if not isinstance(body,dict) or not isinstance(body.get('policy'),dict) or not isinstance(body['policy'].get('source_id'),str) or not isinstance(body.get('request_key'),str):fail()
        with self.store.transaction() as db:return self._save(db,auth,scope,body)
    def _save(self,db,auth,scope,body,reference=None):
        fingerprint=digest(body)
        existing=db.execute('SELECT fingerprint,document FROM business_policy_versions WHERE workspace=? AND owner=? AND request_key=?',(*scope,body['request_key'])).fetchone()
        if existing:
            if existing[0]!=fingerprint:fail('This request key belongs to another policy submission.','IDEMPOTENCY_KEY_REUSED',409)
            return checked(json.loads(existing[1]))
        if not self.ontology.document(db,scope):fail('Create the business foundation first.','BUSINESS_FOUNDATION_REQUIRED',409)
        sources={d['source_id']:d for d in BusinessDocuments.rows(db,scope)};source=sources.get(body['policy']['source_id'])
        policy=validate(body,source)
        total=db.execute('SELECT COUNT(*) FROM business_policy_versions WHERE workspace=? AND owner=?',scope).fetchone()[0]
        head=db.execute('SELECT revision FROM business_policy_heads WHERE workspace=? AND owner=? AND policy_key=?',(*scope,policy['policy_key'])).fetchone()
        count=db.execute('SELECT COUNT(*) FROM business_policy_heads WHERE workspace=? AND owner=?',scope).fetchone()[0]
        if total>=80 or not head and count>=12:fail('Policy draft storage limit reached.','BUSINESS_POLICY_LIMIT',409)
        db.execute('INSERT INTO business_policy_heads VALUES (?,?,?,0) ON CONFLICT DO NOTHING',(*scope,policy['policy_key']))
        changed=db.execute('UPDATE business_policy_heads SET revision=revision+1 WHERE workspace=? AND owner=? AND policy_key=? AND revision=?',(*scope,policy['policy_key'],body['expected_revision'])).rowcount
        if not changed:
            prior=db.execute('SELECT fingerprint,document FROM business_policy_versions WHERE workspace=? AND owner=? AND request_key=?',(*scope,body['request_key'])).fetchone()
            if prior and prior[0]==fingerprint:return checked(json.loads(prior[1]))
            fail('A newer policy revision exists; refresh before saving.','BUSINESS_POLICY_REVISION',409)

        self.authority(auth)
        doc=dict(**policy,policy_id='bop_'+secrets.token_hex(16),revision=body['expected_revision']+1,created_at=now(),schema_version=POLICY_SCHEMA,status='draft',
            source=deepcopy(source),interpretation_basis='descriptive_implementation' if source['kind']=='application_code' else 'policy_statement',**(dict(implementation_reference=reference) if reference else {}),missing_clauses=[key for key,cell in policy['clauses'].items() if cell['value'] is None],business_policy_verified=False,executable=False)
        doc['sha256']=digest(doc)
        inserted=db.execute('INSERT INTO business_policy_versions VALUES (?,?,?,?,?,?,?,?) ON CONFLICT DO NOTHING RETURNING policy_id',(*scope,doc['policy_id'],policy['policy_key'],doc['revision'],body['request_key'],fingerprint,json.dumps(doc))).fetchone()
        if not inserted:fail('The request key or revision was concurrently used; refresh before saving.','BUSINESS_POLICY_REVISION',409)
        db.execute('INSERT INTO business_ontology_events VALUES (?,?,?,?)',(*scope,'boe_'+secrets.token_hex(16),json.dumps(dict(action='save_policy_draft',policy_id=doc['policy_id'],revision=doc['revision'],at=doc['created_at']))))
        return doc
    def import_implementation(self,auth,body):
        scope=self.authority(auth)
        if body!={}:fail('Implementation import accepts an empty object.')
        from .business_warranty_reference import SOURCE_SHA256,interpretations
        with self.store.transaction() as db:
            source=next((d for d in BusinessDocuments.rows(db,scope) if d['kind']=='application_code' and d['sha256']==SOURCE_SHA256 and 'warranty' in d['module_ids']),None)
            if not source:fail('The reviewed supplied warranty code must be saved as an owned warranty source.','BUSINESS_IMPLEMENTATION_SOURCE',409)
            try:plans=interpretations(source,CLAUSES)
            except ValueError:fail('The warranty implementation source changed.','BUSINESS_IMPLEMENTATION_SOURCE',409)
            saved=[]
            for plan in plans:
                request=dict(request_key='implementation_'+SOURCE_SHA256[:20]+'_'+plan['implementation_reference']['branch'],expected_revision=0,policy={k:plan[k] for k in ('policy_key','title','clauses')})
                request['policy']['source_id']=source['source_id']
                saved.append(self._save(db,auth,scope,request,reference=plan['implementation_reference']))
        return self.list(auth)

    def compare(self,auth,version_id,graph_id,body):
        if (not isinstance(body,dict) or set(body)!={'policy_id','ticket_node_id','assessment_at','invoice_node_id'} or not isinstance(body['policy_id'],str)
            or not isinstance(body['assessment_at'],str) or len(body['assessment_at'])>40 or not (body['invoice_node_id'] is None or isinstance(body['invoice_node_id'],str))):fail('Select a saved policy, complaint, explicit timestamp and optional invoice.')
        parsed=parse_date(body['assessment_at'])
        if not parsed or parsed['precision']!='datetime':fail('Assessment timestamp must be ISO datetime with an explicit timezone.')
        policy=self.get(auth,body['policy_id']);snapshot=self.ontology.version(auth,version_id);graph=self.graph.get(auth,version_id,graph_id)
        return compare(policy,snapshot,graph,body)

    def assess(self,auth,version_id,graph_id,body):
        if isinstance(body,dict) and body.get('policy_id','absent') is None:
            if (set(body)!={'policy_id','ticket_node_id','assessment_at','invoice_node_id'} or not isinstance(body['assessment_at'],str) or len(body['assessment_at'])>40
                or not (body['invoice_node_id'] is None or isinstance(body['invoice_node_id'],str))):fail('Select a saved complaint, explicit timestamp and optional invoice.')
            parsed=parse_date(body['assessment_at'])
            if not parsed or parsed['precision']!='datetime':fail('Assessment timestamp requires an explicit timezone.')
            from .business_assessment import missing_policy
            return missing_policy(self.ontology.version(auth,version_id),self.graph.get(auth,version_id,graph_id),body)
        comparison=self.compare(auth,version_id,graph_id,body)
        policy=self.get(auth,body['policy_id']);snapshot=self.ontology.version(auth,version_id);graph=self.graph.get(auth,version_id,graph_id)
        from .business_assessment import assess
        return assess(policy,snapshot,graph,body,comparison)


def compare(policy,snapshot,graph,body):
    checked(policy);readiness=prepare(snapshot,graph,dict(ticket_node_id=body['ticket_node_id']))
    ticket=next(r for r in graph['records'] if r['node_id']==body['ticket_node_id']);fields={i['field']:i for i in readiness['inputs']}
    invoices=readiness['invoice_candidates'];invoice=next((i for i in invoices if i['node_id']==body['invoice_node_id']),None)
    if body['invoice_node_id'] is not None and not invoice:fail('Selected invoice is not a saved service invoice in this graph.')
    model=observation(ticket,'engineModal','identifier','Complaint engine model');clauses=policy['clauses'];checks=[]
    for key,item in [('oem_references',fields['oem']),('models',model)]:
        scope=clauses[key]['value'];state='unavailable' if scope is None or not item['syntactically_usable'] else 'match' if type(item['value']) is str and item['value'] in scope else 'different'
        checks.append(dict(check_id=key,status=state,expected=scope,observed=item['value'],evidence=[item],clause_ids=[key]))
    basis=clauses['date_basis']['value'];observed=None;date_evidence=[]
    if basis=='assessment_date':observed=parse_date(body['assessment_at'])['calendar_date']
    elif basis=='sale_date':observed=fields['complaintRecord.dateOfSale']['normalized'];date_evidence=[fields['complaintRecord.dateOfSale']]
    elif basis=='invoice_date' and invoice:observed=invoice['observations'][2]['normalized'];date_evidence=[invoice['observations'][2]]
    start=clauses['effective_from']['value'];end=clauses['effective_to']['value'];bounds=clauses['effective_bounds']['value']
    state='unavailable'
    if observed is not None and start is not None and end is not None and bounds is not None:
        state='match' if (start<=observed<=end if bounds=='inclusive' else start<observed<end) else 'different'
    checks.append(dict(check_id='effective_dates',status=state,expected=dict(start=start,end=end,bounds=bounds,basis=basis),observed=observed,evidence=date_evidence,clause_ids=['effective_from','effective_to','effective_bounds','date_basis']))
    reasons=['Policy clauses are saved draft interpretations; quotation matching does not verify business authority or meaning.',
        'Physical-engine identity and selected invoice applicability remain unresolved.',
        'Coverage limits, boundary notes and exclusions were not executed; no eligibility decision is available.']
    if policy['missing_clauses']:reasons.append('Unknown policy clauses: '+', '.join(policy['missing_clauses'])+'.')
    if any(c['status']!='match' for c in checks):reasons.append('One or more saved scope/date comparisons differ or are unavailable; they do not establish applicability or claim denial.')
    if invoice is not None:reasons.append('Invoice selection identifies a saved candidate only; it does not confirm engine identity.')
    if any(o['truncated'] for o in graph['outcomes']):reasons.append('The saved source graph contains truncated collections.')
    result=dict(comparison_version=COMPARISON_VERSION,version_id=snapshot['version_id'],graph_id=graph['graph_id'],policy_id=policy['policy_id'],policy_key=policy['policy_key'],policy_revision=policy['revision'],ticket_node_id=ticket['node_id'],invoice_node_id=body['invoice_node_id'],assessment_at=body['assessment_at'],
        status='requires_review',eligibility='not_evaluated',policy_clauses=deepcopy(clauses),policy_source=dict(source_id=policy['source']['source_id'],title=policy['source']['title'],sha256=policy['source']['sha256']),checks=checks,review_reasons=reasons,missing_clauses=policy['missing_clauses'],
        candidate_comparison='all_observed_checks_match' if all(c['status']=='match' for c in checks) else 'differences_or_unknowns',
        limits=['Only selected saved evidence is compared; no company or model call occurred.','Scope checks use exact public scalar values, not inferred aliases or original BSON types.','Dates use recorded calendar days and the selected draft basis; no current-date default or threshold calculation is applied.','Unknown effective end is not unbounded. A matching scope/date comparison is not verified policy applicability.'],
        provenance={**readiness['provenance'],'policy_sha256':policy['sha256'],'policy_source_sha256':policy['source']['sha256']},business_policy_verified=False,company_queries=0,model_calls=0,rules_executed=False)
    result['report_sha256']=digest(result);return result
