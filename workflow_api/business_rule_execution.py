"""Fixed reference-rule handlers and immutable source-cited input revisions."""
from copy import deepcopy
from datetime import date
from decimal import Decimal,localcontext
from hashlib import sha256
import json
from pathlib import Path
import re
import secrets
from registry.safety import reject_secrets
from .business_compiler import canonical,check_snapshot
from .business_documents import BusinessDocuments
from .business_intelligence import check_graph
from .business_monitoring import CHANGES
from .business_ontology import identity
from .business_warranty import parse_hours,observation
from .google_connections import now
from .service import ApiFailure

HANDLER_VERSION='simpson-reference-execution-v1'
ROOT=Path(__file__).resolve().parents[1]
SPECS={
 'failure:unconfirmed_similarity':dict(label='Check root-cause evidence',module='failure',facts={
  'suspected_cause':('Suspected or documented cause','text',[]),
  'finding_basis':('Finding basis','choice',['similarity_only','inspection','test_result']),
  'diagnosis':('Current case diagnosis','choice',['confirmed','inconclusive','ruled_out']),
  'finding_details':('Inspection or test finding','text',[])}),
 'effectivity:recurrence_needs_evidence':dict(label='Check post-change recurrence',module='effectivity',facts={
  'physical_identity':('Engine identity link','choice',['same_engine','different_engines']),
  'applicability':('Change applicability','choice',['applies','does_not_apply']),
  'incorporation':('Changed component incorporation','choice',['installed','not_installed']),
  'mechanism':('Failure mechanism comparison','choice',['same','different']),
  'root_cause':('Root-cause comparison','choice',['same','different']),
  'inspection_conclusion':('Current investigation conclusion','choice',['comparable_failure','no_comparable_failure']),
  'incorporation_date':('Actual incorporation date','date',[]),
  'failure_date':('Current failure date','date',[]),
  'post_change_hours':('Recorded post-change operating hours','hours',[]),
  'required_hours':('Required operating exposure','hours',[])}),
 'monitoring:rate_requires_exposure':dict(label='Calculate evidence-backed failure rate',module='monitoring',facts={
  'cohort':('Monitored cohort definition','text',[]),
  'period_start':('Cohort period start','date',[]),'period_end':('Cohort period end','date',[]),
  'coverage':('Cohort follow-up coverage','choice',['complete','incomplete']),
  'counting_basis':('Failure counting basis','choice',['distinct_first_failures','other_or_unconfirmed']),
  'confirmed_failures':('Confirmed failed engines','integer',[]),
  'population_engines':('Engines at risk','integer',[]),
  'exposure_hours':('Total at-risk engine operating hours','hours',[])})}


def fail(message,code='BUSINESS_RULE_EXECUTION_INVALID',status=422):raise ApiFailure(code,message,status)
def digest(value):return sha256(canonical(value).encode()).hexdigest()
def signature(rule):return digest({k:rule.get(k) for k in ['id','module_id','layer','inputs','conditions','outcome','basis','definition']})
def expected():
    kit=json.loads((ROOT/'ontology/business-reference/module-drafts.json').read_text())
    return {r['id']:dict(r,module_id=module) for module,values in kit['modules'].items() for r in values['rules'] if r['id'] in SPECS}
def availability(rule):
    known=expected().get(rule['id'])
    good=known is not None and signature(rule)==signature(known)
    return dict(available=good,handler_version=HANDLER_VERSION if good else None,reason=None if good else 'No reviewed handler matches this saved rule definition.')
def field_specs(rule_id):return [dict(field_id=k,label=v[0],kind=v[1],choices=v[2]) for k,v in SPECS[rule_id]['facts'].items()]


def scope_check(snapshot,graph,rule_id,subject,change):
    check_snapshot(snapshot)
    check_graph(snapshot,graph)
    rule=next((r for r in snapshot['rules'] if r['id']==rule_id),None)
    if not rule or not availability(rule)['available']:fail('This saved rule has no matching executable handler.','BUSINESS_RULE_UNSUPPORTED',409)
    if subject is not None and (not isinstance(subject,str) or not any(r['node_id']==subject and r['collection'] in ('tickets','enginedetails','jointinspectionreports','claims','claimsftps','failedengineanalyses','failedpartanalyses') for r in graph['records'])):fail('Select a supported subject record in this graph.')
    if change is not None and (not isinstance(change,str) or not any(r['node_id']==change and CHANGES.get(r['collection'])==r['role'] for r in graph['records'])):fail('Select a supported change record in this graph.')
    if rule_id!='effectivity:recurrence_needs_evidence' and change is not None:fail('This rule does not accept a change selection.')
    return rule


def validate_facts(rule_id,facts,source):
    specs=SPECS[rule_id]['facts']
    if not isinstance(facts,dict) or set(facts)!=set(specs):fail('Provide the exact cited input fields; unknown values and quotes must both be null.')
    for key,(_,kind,choices) in specs.items():
        cell=facts[key]
        if not isinstance(cell,dict) or set(cell)!={'value','quote'}:fail('Invalid cited input.')
        value,quote=cell['value'],cell['quote']
        if value is None:
            if quote is not None:fail('Unknown inputs cannot have a quotation.')
            continue
        if not isinstance(quote,str) or not 4<=len(quote)<=1200 or len(' '.join(quote.split()))<4 or ' '.join(quote.split()) not in ' '.join(source['text'].split()):fail('Each known input needs an exact supporting source quotation.')
        if kind=='text' and (not isinstance(value,str) or not 1<=len(value.strip())<=1200):fail('Use bounded nonblank text.')
        if kind=='choice' and (not isinstance(value,str) or value not in choices):fail('Select a declared input value.')
        if kind=='integer' and (type(value) is not int or not 0<=value<=1000000000):fail('Use a nonnegative whole-number count.')
        if kind=='hours' and (not isinstance(value,str) or parse_hours(value) is None):fail('Use nonnegative plain-decimal hours.')
        if kind=='date':
            try:
                if not isinstance(value,str) or not re.fullmatch(r'[0-9]{4}-[0-9]{2}-[0-9]{2}',value):raise ValueError()
                date.fromisoformat(value)
            except ValueError:fail('Use valid ISO calendar dates.')
    if not any(c['value'] is not None for c in facts.values()):fail('Supply at least one cited fact or run without an evidence revision.')
    try:reject_secrets(facts)
    except Exception:fail('Remove credentials from rule inputs.','SENSITIVE_DATA_DETECTED')


def evaluate(rule_id,values):
    """Complete deterministic branches; source qualification is added by caller."""
    checks=[];calculations={}
    def check(key,condition,message):
        value=values.get(key);status='unknown' if value is None else 'passed' if condition(value) else 'failed'
        checks.append(dict(check_id=key,status=status,observed=value,message=message))
    if rule_id=='failure:unconfirmed_similarity':
        check('suspected_cause',lambda v:bool(v.strip()),'A cause must be explicitly stated; no cause is inferred from similar symptoms.')
        check('finding_basis',lambda v:v in ('inspection','test_result'),'Similarity alone cannot confirm a root cause.')
        check('diagnosis',lambda v:v in ('confirmed','ruled_out'),'A current-case conclusion must be documented.')
        check('finding_details',lambda v:bool(v.strip()),'The current inspection/test finding must be stated.')
        if values.get('finding_basis')=='similarity_only' or values.get('diagnosis')=='inconclusive':outcome='hypothesis_only'
        elif any(c['status']=='unknown' for c in checks):outcome='insufficient_evidence'
        elif all(c['status']=='passed' for c in checks):outcome='documented_root_cause' if values['diagnosis']=='confirmed' else 'cause_ruled_out'
        else:outcome='hypothesis_only'
    elif rule_id=='effectivity:recurrence_needs_evidence':
        for key,required in [('physical_identity','same_engine'),('applicability','applies'),('incorporation','installed'),('mechanism','same'),('root_cause','same'),('inspection_conclusion','comparable_failure')]:check(key,lambda v,r=required:v==r,'Required cited condition: '+required.replace('_',' ')+'.')
        for key in ['incorporation_date','failure_date','post_change_hours','required_hours']:check(key,lambda v:True,'Explicit source input required.')
        start,end=values.get('incorporation_date'),values.get('failure_date')
        checks.append(dict(check_id='post_change_chronology',status='unknown' if start is None or end is None else 'passed' if end>=start else 'failed',observed=dict(incorporation_date=start,failure_date=end),message='Failure must be on/after documented incorporation; calendar-day precision only.'))
        observed,required=values.get('post_change_hours'),values.get('required_hours')
        checks.append(dict(check_id='sufficient_exposure',status='unknown' if observed is None or required is None else 'passed' if Decimal(observed)>=Decimal(required) else 'failed',observed=dict(hours=observed,required=required),message='Recorded post-change hours must meet the cited minimum; no threshold is invented.'))
        outcome='insufficient_evidence' if any(c['status']=='unknown' for c in checks) else 'recurrence_supported' if all(c['status']=='passed' for c in checks) else 'recurrence_not_established'
    else:
        for key in ['cohort','period_start','period_end']:check(key,lambda v:True,'Explicit cohort and common observation period required.')
        check('coverage',lambda v:v=='complete','Incomplete cohort follow-up cannot establish this rate.')
        check('counting_basis',lambda v:v=='distinct_first_failures','Numerator must count distinct engines with a confirmed first failure.')
        check('confirmed_failures',lambda v:v>=0,'Zero is valid only as a documented confirmed count.')
        check('population_engines',lambda v:v>0,'At-risk population must be positive.')
        check('exposure_hours',lambda v:Decimal(v)>0,'Total at-risk engine-hours must be positive; one complaint hour reading is not a cohort denominator.')
        n,p=values.get('confirmed_failures'),values.get('population_engines');start,end=values.get('period_start'),values.get('period_end')
        checks.append(dict(check_id='count_consistency',status='unknown' if n is None or p is None else 'passed' if n<=p else 'failed',observed=dict(failures=n,population=p),message='Distinct failed engines cannot exceed the at-risk engine population.'))
        checks.append(dict(check_id='period_consistency',status='unknown' if start is None or end is None else 'passed' if start<=end else 'failed',observed=dict(start=start,end=end),message='Cohort period start cannot follow period end.'))
        outcome='insufficient_evidence' if any(c['status']=='unknown' for c in checks) else 'rate_calculated' if all(c['status']=='passed' for c in checks) else 'rate_not_calculable'
        if outcome=='rate_calculated':
            with localcontext() as ctx:
                ctx.prec=128
                def number(v):return format(v.quantize(Decimal('0.000001')),'f')
                calculations=dict(failed_engine_percentage=number(Decimal(n)*100/Decimal(p)),first_failures_per_1000_engine_hours=number(Decimal(n)*1000/Decimal(values['exposure_hours'])),percentage_formula='confirmed failed engines / engines at risk × 100',incidence_formula='confirmed first failures / total at-risk engine-hours × 1000',rounding='six decimal places, half-even',cohort=values['cohort'],period_start=start,period_end=end)
    return dict(outcome=outcome,checks=checks,calculations=calculations)


def checked(doc):
    if doc.get('sha256')!=digest({k:v for k,v in doc.items() if k!='sha256'}) or sha256(doc['source']['text'].encode()).hexdigest()!=doc['source']['sha256']:fail('Saved rule evidence failed integrity checks.','BUSINESS_RULE_EVIDENCE_INTEGRITY',409)
    validate_facts(doc['rule_id'],doc['facts'],doc['source']);return doc


class BusinessRuleExecution:
    def __init__(self,ontology,graph,resolve):
        self.ontology=ontology;self.graph=graph;self.store=ontology.store;self.resolve=resolve
        with self.store.transaction() as db:
            db.execute('CREATE TABLE IF NOT EXISTS business_rule_evidence_heads (workspace TEXT NOT NULL,owner TEXT NOT NULL,series_key TEXT NOT NULL,revision INTEGER NOT NULL,PRIMARY KEY(workspace,owner,series_key))')
            db.execute('CREATE TABLE IF NOT EXISTS business_rule_evidence_versions (workspace TEXT NOT NULL,owner TEXT NOT NULL,evidence_id TEXT NOT NULL,series_key TEXT NOT NULL,revision INTEGER NOT NULL,request_key TEXT NOT NULL,fingerprint TEXT NOT NULL,document TEXT NOT NULL,PRIMARY KEY(workspace,owner,evidence_id),UNIQUE(workspace,owner,series_key,revision),UNIQUE(workspace,owner,request_key))')
    def context(self,auth,vid,gid):
        snapshot=self.ontology.version(auth,vid);graph=self.graph.get(auth,vid,gid);check_graph(snapshot,graph);return snapshot,graph
    def catalogue(self,auth,vid,gid):
        scope=identity(auth);snapshot,graph=self.context(auth,vid,gid)
        with self.store.transaction(write=False) as db:
            docs=[{k:d[k] for k in ('source_id','title','sha256','module_ids')} for d in BusinessDocuments.rows(db,scope) if d['kind']=='evidence']
            versions=[checked(json.loads(r[0])) for r in db.execute('SELECT document FROM business_rule_evidence_versions WHERE workspace=? AND owner=? ORDER BY series_key,revision DESC',scope)]
        return dict(version_id=vid,graph_id=gid,handler_version=HANDLER_VERSION,rules=[dict(rule_id=r['id'],label=SPECS[r['id']]['label'],module_id=r['module_id'],**availability(r),fact_specs=field_specs(r['id'])) for r in snapshot['rules'] if r['id'] in SPECS],sources=docs,evidence=[{k:d[k] for k in ('evidence_id','rule_id','graph_id','subject_node_id','change_node_id','revision','created_at','sha256','source_id')} for d in versions if d['graph_id']==gid])
    def get(self,auth,eid):
        scope=identity(auth)
        with self.store.transaction(write=False) as db:row=db.execute('SELECT document FROM business_rule_evidence_versions WHERE workspace=? AND owner=? AND evidence_id=?',(*scope,eid)).fetchone()
        if not row:fail('Rule evidence not found.','BUSINESS_RULE_EVIDENCE_NOT_FOUND',404)
        return checked(json.loads(row[0]))
    def authority(self,auth):
        scope=identity(auth,True);current=self.resolve(*scope) if self.resolve else auth
        if not current or current['subject']!=auth['subject']:fail('Current write authority unavailable.','OPERATION_NOT_AUTHORIZED',403)
        identity(current,True);return scope
    def save(self,auth,vid,gid,body):
        scope=self.authority(auth)
        if (not isinstance(body,dict) or set(body)!={'request_key','expected_revision','rule_id','subject_node_id','change_node_id','source_id','facts'} or not isinstance(body['request_key'],str) or not re.fullmatch(r'[A-Za-z0-9_-]{8,100}',body['request_key']) or type(body['expected_revision']) is not int or not 0<=body['expected_revision']<32 or not isinstance(body['rule_id'],str) or not isinstance(body['source_id'],str)):fail('Provide exact rule evidence inputs and revision.')
        snapshot,graph=self.context(auth,vid,gid);scope_check(snapshot,graph,body['rule_id'],body['subject_node_id'],body['change_node_id'])
        if body['rule_id']!='monitoring:rate_requires_exposure' and body['subject_node_id'] is None:fail('Select a saved subject before recording case evidence.')
        if body['rule_id']=='effectivity:recurrence_needs_evidence' and body['change_node_id'] is None:fail('Select a saved change before recording recurrence evidence.')
        fingerprint=digest([vid,gid,body]);series=digest([gid,body['rule_id'],body['subject_node_id'],body['change_node_id']])
        with self.store.transaction() as db:
            old=db.execute('SELECT fingerprint,document FROM business_rule_evidence_versions WHERE workspace=? AND owner=? AND request_key=?',(*scope,body['request_key'])).fetchone()
            if old:
                if old[0]!=fingerprint:fail('Request key has different inputs.','IDEMPOTENCY_KEY_REUSED',409)
                return checked(json.loads(old[1]))
            source=next((d for d in BusinessDocuments.rows(db,scope) if d['source_id']==body['source_id']),None)
            if not source or source['kind']!='evidence' or SPECS[body['rule_id']]['module'] not in source['module_ids']:fail('Select an owned evidence document for this rule module.')
            if sha256(source['text'].encode()).hexdigest()!=source['sha256']:fail('Evidence source integrity failed.')
            validate_facts(body['rule_id'],body['facts'],source)
            head=db.execute('SELECT revision FROM business_rule_evidence_heads WHERE workspace=? AND owner=? AND series_key=?',(*scope,series)).fetchone();revision=head[0] if head else 0
            if revision!=body['expected_revision']:fail('Evidence revision changed; refresh before saving.','BUSINESS_RULE_EVIDENCE_CHANGED',409)
            total=db.execute('SELECT COUNT(*) FROM business_rule_evidence_versions WHERE workspace=? AND owner=?',scope).fetchone()[0];heads=db.execute('SELECT COUNT(*) FROM business_rule_evidence_heads WHERE workspace=? AND owner=?',scope).fetchone()[0]
            if total>=200 or (not head and heads>=24):fail('Rule evidence storage limit reached.',status=409)
            self.authority(auth)
            if head:
                changed=db.execute('UPDATE business_rule_evidence_heads SET revision=? WHERE workspace=? AND owner=? AND series_key=? AND revision=?',(revision+1,*scope,series,revision)).rowcount
                if changed!=1:fail('Evidence revision changed.','BUSINESS_RULE_EVIDENCE_CHANGED',409)
            else:db.execute('INSERT INTO business_rule_evidence_heads VALUES (?,?,?,?)',(*scope,series,1))
            doc=dict(evidence_id='bre_'+secrets.token_hex(16),version_id=vid,graph_id=gid,rule_id=body['rule_id'],subject_node_id=body['subject_node_id'],change_node_id=body['change_node_id'],revision=revision+1,created_at=now(),source_id=source['source_id'],source=deepcopy(source),facts=deepcopy(body['facts']),qualification='Source-cited assertions entered by a workspace manager; not independently verified by the application.')
            doc['sha256']=digest(doc)
            db.execute('INSERT INTO business_rule_evidence_versions VALUES (?,?,?,?,?,?,?,?)',(*scope,doc['evidence_id'],series,revision+1,body['request_key'],fingerprint,json.dumps(doc)))
            db.execute('INSERT INTO business_ontology_events VALUES (?,?,?,?)',(*scope,'boe_'+secrets.token_hex(16),json.dumps(dict(action='save_rule_evidence',evidence_id=doc['evidence_id'],rule_id=doc['rule_id'],graph_id=gid,revision=doc['revision'],at=doc['created_at']))))
        return doc
    def run(self,auth,vid,gid,body):
        identity(auth)
        if not isinstance(body,dict) or set(body)!={'rule_id','subject_node_id','change_node_id','evidence_id'} or not isinstance(body['rule_id'],str) or not (body['evidence_id'] is None or isinstance(body['evidence_id'],str)):fail('Select one saved rule, subject/change and optional evidence revision.')
        snapshot,graph=self.context(auth,vid,gid);rule=scope_check(snapshot,graph,body['rule_id'],body['subject_node_id'],body['change_node_id'])
        evidence=self.get(auth,body['evidence_id']) if body['evidence_id'] is not None else None
        if evidence and any(evidence[key]!=value for key,value in [('version_id',vid),('graph_id',gid),('rule_id',body['rule_id']),('subject_node_id',body['subject_node_id']),('change_node_id',body['change_node_id'])]):fail('Evidence belongs to different rule/case/change inputs.')
        values={key:evidence['facts'][key]['value'] if evidence else None for key in SPECS[body['rule_id']]['facts']}
        result=evaluate(body['rule_id'],values)
        if body['rule_id']!='monitoring:rate_requires_exposure' and body['subject_node_id'] is None:
            result['checks'].append(dict(check_id='saved_subject',status='unknown',observed=None,message='Select the saved engine/case subject.'));result['outcome']='insufficient_evidence'
        if body['rule_id']=='effectivity:recurrence_needs_evidence' and body['change_node_id'] is None:
            result['checks'].append(dict(check_id='saved_change',status='unknown',observed=None,message='Select a saved change record.'));result['outcome']='insufficient_evidence'
        observed=[]
        for record in graph['records']:
            if record['node_id'] not in (body['subject_node_id'],body['change_node_id']):continue
            for name in ['potentialCause','defect','defectCode','status','engineNo','engineSerialNumber','cutInEsn','engineCutInNumber']:
                if any(f['name']==name for f in record['fields']):observed.append(observation(record,name,'identifier',name))
        report=dict(**result,rule_id=body['rule_id'],label=SPECS[body['rule_id']]['label'],handler_version=HANDLER_VERSION,version_id=vid,graph_id=gid,subject_node_id=body['subject_node_id'],change_node_id=body['change_node_id'],evidence_id=body['evidence_id'],facts=evidence['facts'] if evidence else {},source={k:evidence['source'][k] for k in ('source_id','title','sha256')} if evidence else None,observations=observed,
            qualification='Computed from the selected saved source-cited assertions. The application validates structure/citations, not independent truth. No diagnosis, claim decision or source record is changed.',
            limits=['No graph record count is used as a cohort denominator.','Source labels, similarity and serial order never confirm root cause, incorporation or recurrence.','Results apply only to the selected case/change or explicitly defined external cohort and period.'],
            provenance=dict(definition_sha256=digest(rule),graph_sha256=digest(graph),evidence_sha256=evidence['sha256'] if evidence else None),rules_executed=True,company_queries=0,model_calls=0,source_writes=0,independently_verified=False)
        report['report_sha256']=digest(report);return report
