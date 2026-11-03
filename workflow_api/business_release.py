"""Offline, scoped artifact recovery and release gaps; never release authority."""
from hashlib import sha256
from importlib.metadata import version,PackageNotFoundError
import json
import os
from pathlib import Path
import sqlite3
import subprocess
from registry.safety import reject_secrets
from .business_compiler import canonical,check_snapshot
from .business_intelligence import check_graph
from .business_monitoring import report as monitoring,calendar
from .business_policies import checked as checked_policy
from .security import deployment_mode
from .business_rule_execution import checked as checked_rule_evidence,scope_check as check_rule_scope

ROOT=Path(__file__).resolve().parents[1]
AUDIT_VERSION='simpson-release-audit-v1'
# Fixed schemas only: never execute SQL read from the input database.
TABLES={}
for suffix,key in [('workspaces','ontology_id'),('versions','version_id'),('events','event_id'),('documents','document_id')]:
    TABLES['business_ontology_'+suffix]=(f'workspace TEXT NOT NULL,owner TEXT NOT NULL,{key} TEXT NOT NULL,document TEXT NOT NULL,PRIMARY KEY(workspace,owner,{key})', ['workspace','owner',key,'document'])
TABLES.update({
 'business_ontology_jobs':('job_id TEXT PRIMARY KEY,workspace TEXT NOT NULL,owner TEXT NOT NULL,request_key TEXT NOT NULL,fingerprint TEXT NOT NULL,state TEXT NOT NULL,document TEXT NOT NULL,claim TEXT,deadline REAL,created REAL NOT NULL,UNIQUE(workspace,owner,request_key)', ['job_id','workspace','owner','request_key','fingerprint','state','document','claim','deadline','created']),
 'business_ontology_compilations':('workspace TEXT NOT NULL,owner TEXT NOT NULL,version_id TEXT NOT NULL,compiler_version TEXT NOT NULL,document TEXT NOT NULL,PRIMARY KEY(workspace,owner,version_id,compiler_version)', ['workspace','owner','version_id','compiler_version','document']),
 'business_ontology_graphs':('workspace TEXT NOT NULL,owner TEXT NOT NULL,version_id TEXT NOT NULL,graph_id TEXT NOT NULL,request_key TEXT NOT NULL,fingerprint TEXT NOT NULL,document TEXT NOT NULL,PRIMARY KEY(workspace,owner,graph_id),UNIQUE(workspace,owner,request_key)', ['workspace','owner','version_id','graph_id','request_key','fingerprint','document']),
 'business_ontology_reference_imports':('workspace TEXT NOT NULL,owner TEXT NOT NULL,request_key TEXT NOT NULL,fingerprint TEXT NOT NULL,version_id TEXT NOT NULL,PRIMARY KEY(workspace,owner,request_key)', ['workspace','owner','request_key','fingerprint','version_id']),
 'business_rule_evidence_heads':('workspace TEXT NOT NULL,owner TEXT NOT NULL,series_key TEXT NOT NULL,revision INTEGER NOT NULL,PRIMARY KEY(workspace,owner,series_key)', ['workspace','owner','series_key','revision']),
 'business_rule_evidence_versions':('workspace TEXT NOT NULL,owner TEXT NOT NULL,evidence_id TEXT NOT NULL,series_key TEXT NOT NULL,revision INTEGER NOT NULL,request_key TEXT NOT NULL,fingerprint TEXT NOT NULL,document TEXT NOT NULL,PRIMARY KEY(workspace,owner,evidence_id),UNIQUE(workspace,owner,series_key,revision),UNIQUE(workspace,owner,request_key)', ['workspace','owner','evidence_id','series_key','revision','request_key','fingerprint','document']),
 'business_policy_heads':('workspace TEXT NOT NULL,owner TEXT NOT NULL,policy_key TEXT NOT NULL,revision INTEGER NOT NULL,PRIMARY KEY(workspace,owner,policy_key)', ['workspace','owner','policy_key','revision']),
 'business_policy_versions':('workspace TEXT NOT NULL,owner TEXT NOT NULL,policy_id TEXT NOT NULL,policy_key TEXT NOT NULL,revision INTEGER NOT NULL,request_key TEXT NOT NULL,fingerprint TEXT NOT NULL,document TEXT NOT NULL,PRIMARY KEY(workspace,owner,policy_id),UNIQUE(workspace,owner,policy_key,revision),UNIQUE(workspace,owner,request_key)', ['workspace','owner','policy_id','policy_key','revision','request_key','fingerprint','document']),
})

SUPPORT=[
 ('warranty-assessment','Coverage currently uses assessment date, not verified failure date; policy authority, identity and exclusion findings remain unmet.'),
 ('claim_fields','Literal reason/status fields do not establish a verified rejection decision.'),
 ('claim_fields','Bounded exact-serial records are not all claims for an OEM; identifiers and population scope remain unverified.'),
 ('inspection_findings','Source provenance and qualifiers do not establish verified findings.'),
 ('policy-comparison','Draft revisions do not establish which policy governed a real approval.'),
 ('service_path','Recorded engineer/reference fields do not verify investigator identity or a complete investigation path.'),
 ('inspection_findings','Projected inspection fields are a subset, not all inspection observations/documents.'),
 ('inspection_findings','Complaint/inspection associations and verified findings require acceptance.'),
 ('associations','Physical-engine identity and distinct dated failure history remain unresolved.'),
 ('quality_changes','Status vocabulary and complete investigation population are unverified.'),
 ('inspection_findings','Potential causes and defect labels are not confirmed comparable mechanisms or a complete engine population.'),
 ('service_path','Return-to-quality-issue associations and population scope are unverified.'),
 ('quality_changes','Root-cause confirmation and the complaint/evidence path are not established.'),
 ('quality_changes','Component identities and cross-model comparable confirmed failures are unverified.'),
 ('monitoring-readiness','Change applicability, eligible population and incorporation are not verified.'),
 ('monitoring-readiness','Scope, serial ordering, exceptions and authoritative boundaries are not verified.'),
 ('monitoring-readiness','Actual incorporation/configuration evidence is unavailable.'),
 ('monitoring-readiness','Confirmed comparable failures, incorporation and longitudinal exposure are unavailable.'),
 ('monitoring-readiness','Failure-rate numerator, cohort and exposure denominator are unavailable.'),
 ('claim_fields','Confirmed cause-to-replacement costs and comparable currency/valuation are not established.'),
 ('monitoring-readiness','Effectiveness criteria, implementation, cohort and exposure are unavailable.'),
 ('monitoring-readiness','Verified OEM recurrence cohorts and exposure denominators are unavailable.'),
]


def digest(value):return sha256(canonical(value).encode()).hexdigest()


def file_sha(path):
    value=sha256()
    with Path(path).open('rb') as stream:
        for chunk in iter(lambda:stream.read(1024*1024),b''):value.update(chunk)
    return value.hexdigest()


def read_owned(database,workspace,owner):
    result={};size=0
    with sqlite3.connect(Path(database).resolve().as_uri()+'?mode=ro',uri=True) as db:
        db.execute('PRAGMA query_only=ON');db.execute('BEGIN')
        for table,(_,columns) in TABLES.items():
            if not db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",(table,)).fetchone():continue
            if {r[1] for r in db.execute('PRAGMA table_info('+table+')')}!=set(columns):raise ValueError('Artifact schema changed; review recovery schema')
            result[table]=[]
            for row in db.execute('SELECT '+','.join(columns)+' FROM '+table+' WHERE workspace=? AND owner=? ORDER BY '+','.join(columns)+' LIMIT 2001',(workspace,owner)):
                if len(result[table])>=2000:raise ValueError('Artifact row bound exceeded')
                size+=len(canonical(row).encode())
                if size>64*1024*1024:raise ValueError('Artifact byte bound exceeded')
                result[table].append(dict(zip(columns,row)))
    if not result.get('business_ontology_workspaces'):raise ValueError('Owned workspace unavailable')
    return result


def competency_matrix():
    path=ROOT/'ontology/business-reference/competency-questions.json';catalogue=json.loads(path.read_text())
    if [q['id'] for q in catalogue['items']]!=[f'business_{i:02}' for i in range(1,23)]:raise ValueError('Competency catalogue changed; review acceptance mappings')
    return [dict(**q,acceptance='not_accepted',inspection_tool=tool,implementation_gap=gap) for q,(tool,gap) in zip(catalogue['items'],SUPPORT)]


def inspect(data,start,end):
    versions={r['version_id']:json.loads(r['document']) for r in data.get('business_ontology_versions',[])}
    for table,rows in data.items():
        for row in rows:
            if 'document' in row:reject_secrets(json.loads(row['document']))
    for key,doc in versions.items():
        if doc['version_id']!=key:raise ValueError('Definition identity mismatch')
        if doc['kind']=='draft':check_snapshot(doc)
    for row in data.get('business_ontology_documents',[]):
        doc=json.loads(row['document'])
        if row['document_id']!=doc['source_id'] or sha256(doc['text'].encode()).hexdigest()!=doc['sha256']:raise ValueError('Source document integrity failed')
    for row in data.get('business_policy_versions',[]):
        doc=checked_policy(json.loads(row['document']))
        if row['policy_id']!=doc['policy_id'] or row['policy_key']!=doc['policy_key'] or row['revision']!=doc['revision']:raise ValueError('Policy identity mismatch')
    heads={r['policy_key']:r['revision'] for r in data.get('business_policy_heads',[])}
    latest={}
    for row in data.get('business_policy_versions',[]):latest[row['policy_key']]=max(latest.get(row['policy_key'],0),row['revision'])
    if heads!=latest:raise ValueError('Policy history/head mismatch')
    rule_graphs={r['graph_id']:json.loads(r['document']) for r in data.get('business_ontology_graphs',[])}
    rule_heads={r['series_key']:r['revision'] for r in data.get('business_rule_evidence_heads',[])};rule_latest={}
    for row in data.get('business_rule_evidence_versions',[]):
        doc=checked_rule_evidence(json.loads(row['document']))
        if row['evidence_id']!=doc['evidence_id'] or row['revision']!=doc['revision']:raise ValueError('Rule evidence identity mismatch')
        if doc['version_id'] not in versions:raise ValueError('Rule evidence version missing')
        if doc['graph_id'] not in rule_graphs:raise ValueError('Rule evidence graph missing')
        if row['series_key']!=digest([doc['graph_id'],doc['rule_id'],doc['subject_node_id'],doc['change_node_id']]):raise ValueError('Rule evidence series mismatch')
        check_rule_scope(versions[doc['version_id']],rule_graphs[doc['graph_id']],doc['rule_id'],doc['subject_node_id'],doc['change_node_id'])
        rule_latest[row['series_key']]=max(rule_latest.get(row['series_key'],0),row['revision'])
    if rule_heads!=rule_latest:raise ValueError('Rule evidence history/head mismatch')
    compilations=[]
    for row in data.get('business_ontology_compilations',[]):
        doc=json.loads(row['document'])
        if doc['version_id']!=row['version_id'] or doc['compiler_version']!=row['compiler_version'] or doc['input_sha256']!=digest(versions[row['version_id']]):raise ValueError('Compilation input mismatch')
        expected={'ontology.ttl','ontology.rdf','instance-shapes.ttl','definition-shapes.ttl','validation-report.ttl','validation-report.json'}
        if len(doc['artifacts'])!=6 or {a['name'] for a in doc['artifacts']}!=expected:raise ValueError('Compilation exports missing or duplicated')
        for artifact in doc['artifacts']:
            if sha256(artifact['content'].encode()).hexdigest()!=artifact['sha256']:raise ValueError('Compilation artifact integrity failed')
            if artifact['name']=='validation-report.json' and json.loads(artifact['content'])!=doc['report']:raise ValueError('Compilation report mismatch')
        compilations.append(dict(version_id=row['version_id'],status=doc['report']['status']))
    graphs=[]
    for row in data.get('business_ontology_graphs',[]):
        graph=json.loads(row['document']);snapshot=versions[row['version_id']]
        if graph['graph_id']!=row['graph_id']:raise ValueError('Graph identity mismatch')
        check_graph(snapshot,graph)
        result=monitoring(snapshot,graph,dict(change_node_id=None,period_start=start,period_end=end,limit=50,offset=0))
        graphs.append(dict(graph_id=graph['graph_id'],version_id=snapshot['version_id'],graph_sha256=digest(graph),monitoring_report_sha256=result['report_sha256'],records=len(graph['records']),instance_validation=graph['validation']['status']))
    return dict(versions=len(versions),drafts=sum(d['kind']=='draft' for d in versions.values()),compilations=compilations,graphs=graphs,policy_revisions=len(data.get('business_policy_versions',[])),rule_evidence_revisions=len(data.get('business_rule_evidence_versions',[])))


def manifest():
    paths={ROOT/'requirements.txt',ROOT/'workflow_api/security.py',ROOT/'frontend/package.json',ROOT/'frontend/package-lock.json',ROOT/'frontend/src/api/client.ts',ROOT/'frontend/src/api/business-ontology.ts'}
    for pattern in ['workflow_api/business_*.py','ontology/business-reference/*.json','scripts/check_business_*.py','frontend/src/features/data-sources/Business*.tsx','frontend/src/features/data-sources/SimpsonBusinessOntology.tsx','tests/test_business_*.py','docs/simpson-business-ontology/*.md','openspec/changes/simpson-business-ontology/*.md']:
        paths.update(ROOT.glob(pattern))
    files={str(p.relative_to(ROOT)):file_sha(p) for p in sorted(paths)}
    packages={}
    for name in ['rdflib','pyshacl','fastapi','openai']:
        try:packages[name]=version(name)
        except PackageNotFoundError:packages[name]=None
    commit=subprocess.run(['git','rev-parse','HEAD'],cwd=ROOT,capture_output=True,text=True,check=True,timeout=10).stdout.strip()
    dirty=subprocess.run(['git','status','--porcelain','-z'],cwd=ROOT,capture_output=True,check=True,timeout=10).stdout
    return dict(files=files,files_sha256=digest(files),installed_packages=packages,git_commit=commit,working_tree_dirty=bool(dirty),scope='Current working-tree files, not a committed release bundle or a dependency vulnerability audit.')


def restore(data,path):
    fd=os.open(path,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600);os.close(fd)
    with sqlite3.connect(path) as db:
        for table,rows in data.items():
            schema,columns=TABLES[table];db.execute('CREATE TABLE '+table+' ('+schema+')')
            db.executemany('INSERT INTO '+table+' ('+','.join(columns)+') VALUES ('+','.join('?' for _ in columns)+')',[[r[c] for c in columns] for r in rows])
        if 'business_ontology_jobs' in data:
            db.execute("CREATE UNIQUE INDEX business_ontology_active_job ON business_ontology_jobs(workspace,owner) WHERE state IN ('queued','running')")


def run(database,directory,workspace,owner,period_start,period_end):
    database=Path(database);directory=Path(directory)
    if directory.exists():raise ValueError('Output must be fresh')
    if calendar(period_end)<calendar(period_start):raise ValueError('Reversed period')
    before=file_sha(database);data=read_owned(database,workspace,owner);original=inspect(data,period_start,period_end)
    directory.mkdir(mode=0o700,parents=True,exist_ok=False)
    recovered=directory/'ontology-artifacts.sqlite3';restore(data,recovered)
    restored=read_owned(recovered,workspace,owner)
    if digest(restored)!=digest(data) or inspect(restored,period_start,period_end)!=original:raise ValueError('Recovery verification failed')
    if file_sha(database)!=before or digest(read_owned(database,workspace,owner))!=digest(data):raise ValueError('Input changed during audit')
    try:deployment_mode('production');auth_status='not_verified'
    except ValueError:auth_status='blocked_by_current_code'
    active=[r['state'] for r in data.get('business_ontology_jobs',[]) if r['state'] in ('queued','running')]
    result=dict(audit_version=AUDIT_VERSION,public_release_status='not_ready',period_start=period_start,period_end=period_end,
        table_inventory={t:dict(present=t in data,owned_rows=len(data.get(t,[])),sha256=digest(data[t]) if t in data else None) for t in TABLES},artifact_checks=original,
        recovery=dict(status='passed',scope='Owned Business Ontology artifacts only; not a full application/credential backup.',snapshot_sha256=digest(data),restored_sha256=digest(restored),database_sha256=file_sha(recovered),job_states_preserved=True,active_jobs=len(active),workers_started=0,model_jobs_replayed=0),
        release_gates=[dict(gate_id='production_authentication',status=auth_status,reason='Current production admission requires trusted login; a frontend shared access cookie is not individual backend production identity.'),
            dict(gate_id='business_competencies',status='not_accepted',reason='All 22 require actual business evidence/production acceptance; inspection tools are not accepted answers.'),
            dict(gate_id='live_https_roles_and_scope',status='not_run',reason='Target deployment and individual viewer/manager/foreign workspace tests are not verified.'),
            dict(gate_id='production_workers',status='not_run',reason='Generation interruption/recovery and per-user authority must be verified on the target; no uncertain model job may replay automatically.'),
            dict(gate_id='full_application_recovery',status='not_run',reason='This drill excludes source credentials, encryption keys, login configuration and other application tables.'),
            dict(gate_id='target_storage',status='not_run',reason='This audit covers SQLite artifacts only; production PostgreSQL or multi-replica acceptance is not inferred.')],
        competency_matrix=competency_matrix(),accepted_business_answers=0,source_manifest=manifest(),input_store_unchanged=True,company_queries=0,company_writes=0,model_calls=0,input_store_writes=0,services_started=0)
    result['report_sha256']=digest(result)
    path=directory/'report.json';path.write_text(json.dumps(result,indent=2)+'\n');path.chmod(0o600)
    return result
