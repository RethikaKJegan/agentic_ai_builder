"""Immutable client knowledge configuration, shared preparation and mapped reads.

Packages are data. They cannot install Python/SQL, a connector, a permission or an
external action. Source providers are operator-injected, current-auth callables.
"""
from copy import deepcopy
from datetime import datetime, timezone
import json
import math
from .business_knowledge_model import digest, canonical
from .capability_contracts import SCHEMA, contract
from jsonschema import Draft202012Validator
from registry.safety import reject_secrets
from .investigation_graph import fail

PACKAGE_KEYS={'package_id','revision','client_id','domain','ontology_version','concepts','relationships',
              'source_mappings','evidence_requirements','capability_contracts','rules','resource_bindings','validation_requirements'}
PACKAGE_OPTIONAL={'process_definitions','memory_policy'}
PACKAGE_INPUT={'type':'object','additionalProperties':False,'required':['package_id','revision','capability_id'],
 'properties':{'package_id':{'type':'string'},'revision':{'type':'integer','minimum':1},'capability_id':{'type':'string'}}}
PACKAGE_OUTPUT={'type':'object','required':['version_id','knowledge_sha256','records','coverage'],
 'properties':{'version_id':{'type':'string'},'knowledge_sha256':{'type':'string'},'records':{'type':'array','items':{'type':'object'}},'coverage':{'type':'object','required':['state','conclusion_ready']}}}


def object_schema(required, properties):
    return dict(type='object',required=required,properties=properties)

from pathlib import Path
PACKAGE_SCHEMA=json.loads((Path(__file__).resolve().parents[1]/'shared/contracts/client-knowledge-package-v1.json').read_text())


class ClientPackages:
    def __init__(self,store,providers=None,*,max_package_bytes=100000):
        self.store=store;self.providers=providers or {}
        # Trusted operator provisioning may need a larger metadata manifest.
        # Callers cannot increase this through package/request JSON. Execution
        # permissions, record bounds and the 100 KB evidence limit are unchanged.
        if type(max_package_bytes) is not int or not 1<=max_package_bytes<=300000:
            raise ValueError('Use a bounded operator package metadata allowance.')
        self.max_package_bytes=max_package_bytes
        with store.transaction() as db:
            db.execute('CREATE TABLE IF NOT EXISTS client_knowledge_packages (workspace TEXT NOT NULL, owner TEXT NOT NULL, package_id TEXT NOT NULL, revision INTEGER NOT NULL, document TEXT NOT NULL, PRIMARY KEY(workspace,owner,package_id,revision))')

    @staticmethod
    def scope(auth,manage=False):
        from runtime.service import RuntimeService
        RuntimeService.authorize(auth,'workflow.edit' if manage else 'workflow.plan',{'admin','builder'})
        return auth['subject']['workspace_id'],auth['subject']['subject_id']

    def register_source(self,auth,source_id,provider):
        """Trusted application configuration, never a model/package operation."""
        scope=self.scope(auth,True)
        if 'tools.manage' not in auth['permissions'] or not isinstance(source_id,str) or not 1<=len(source_id)<=128 or not callable(provider):fail('Source registration requires an operator and an executable adapter.','CLIENT_SOURCE_DENIED',403)
        self.providers[(*scope,source_id)]=provider

    def publish(self,auth,body):
        scope=self.scope(auth,True)
        if not isinstance(body,dict) or not PACKAGE_KEYS<=set(body) or set(body)-(PACKAGE_KEYS|PACKAGE_OPTIONAL):fail('Supply the complete client knowledge manifest.','CLIENT_PACKAGE_INVALID',422)
        if list(Draft202012Validator(PACKAGE_SCHEMA).iter_errors(body)):fail('Client package does not satisfy its schema.','CLIENT_PACKAGE_INVALID',422)
        reject_secrets(body)
        if len(canonical(body).encode())>self.max_package_bytes:fail('Client package is too large.','CLIENT_PACKAGE_INVALID',422)
        for k in ('package_id','client_id','domain','ontology_version'):
            if not isinstance(body[k],str) or not 1<=len(body[k])<=128:fail('Invalid package identity.','CLIENT_PACKAGE_INVALID',422)
        if type(body['revision']) is not int or body['revision']<1:fail('Use a positive package revision.','CLIENT_PACKAGE_INVALID',422)
        for k in ('concepts','relationships','source_mappings','evidence_requirements','rules','validation_requirements'):
            if not isinstance(body[k],list):fail('Package knowledge sections must be lists.','CLIENT_PACKAGE_INVALID',422)
        if not {'acyclic_dependencies','mapped_evidence','current_source_authority'}<=set(body['validation_requirements']) or set(body['validation_requirements'])-{'acyclic_dependencies','mapped_evidence','current_source_authority'}:fail('Unsupported or missing package validation requirements.','CLIENT_PACKAGE_INVALID',422)
        if not isinstance(body['resource_bindings'],dict) or not isinstance(body['capability_contracts'],dict):fail('Use typed contracts and resource bindings.','CLIENT_PACKAGE_INVALID',422)
        try:
            ids=[c['id'] for c in body['concepts']]
            if len(set(ids))!=len(ids) or any(c.get('parent') and c['parent'] not in ids for c in body['concepts']):raise ValueError()
            for c in body['concepts']:
                seen={c['id']};parent=c.get('parent')
                while parent:
                    if parent in seen:raise ValueError()
                    seen.add(parent);parent=next(x for x in body['concepts'] if x['id']==parent).get('parent')
            if any(r['source'] not in ids or r['target'] not in ids for r in body['relationships']):raise ValueError()
            mids=[m['id'] for m in body['source_mappings']]
            if len(set(mids))!=len(mids):raise ValueError()
            for m in body['source_mappings']:
                if m['concept'] not in ids or not all(isinstance(m[k],str) and m[k] for k in ('id','field','source')):raise ValueError()
            for cid,c in body['capability_contracts'].items():
                if list(Draft202012Validator(SCHEMA).iter_errors(c)) or cid!=c['capability_id']:raise ValueError()
                if c['side_effect'] not in ('none','read') or c['retrieval_task'] is not None:raise ValueError()
                if set(c['required_ontology'])-set(ids):raise ValueError()
                if set(c['preconditions'])-set(body['capability_contracts']):raise ValueError()
                if c['kind']=='tool':
                    if c['allowed_tool_operations']!=['business.retrieve_package_evidence'] or c['input_schema']!=PACKAGE_INPUT or c['output_schema']!=PACKAGE_OUTPUT:raise ValueError()
                    binding=body['resource_bindings'][cid]
                    if any(mid not in mids for mid in binding['mapping_ids']):raise ValueError()
                    if not binding['mapping_ids'] or any(next(m for m in body['source_mappings'] if m['id']==mid)['source']!=binding['source_id'] for mid in binding['mapping_ids']):raise ValueError()
            for r in body['rules']:
                if r['operator'] not in ('lt','lte','eq','gt','gte') or r['left_mapping'] not in mids or r['right_mapping'] not in mids:raise ValueError()
            for r in body['evidence_requirements']:
                if r['capability_id'] not in body['capability_contracts'] or r['mapping_id'] not in mids:raise ValueError()
            process_ids=set()
            for process in body.get('process_definitions',[]):
                from .business_cases import BusinessCases
                BusinessCases.validate_definition(process)
                identity=(process['process_definition_id'],process['version'])
                if identity in process_ids or process['client_id']!=body['client_id'] or process['domain_id']!=body['domain']:raise ValueError()
                process_ids.add(identity)
                for stage in process['stages']:
                    if set(stage['required_capabilities'])-(set(body['capability_contracts'])|{'business.report'}):raise ValueError()
                    if set(stage['required_ontology_concepts'])-set(ids):raise ValueError()
                    for spec in list(stage['required_inputs'].values())+list(stage['optional_inputs'].values()):
                        if spec.get('evidence_mapping') and spec['evidence_mapping'] not in mids:raise ValueError()
            from .capability_contracts import validate_tasks
            # A catalog lists available operations, not one executable workflow.
            # Each actual workflow retains validate_tasks' default 16-task limit.
            validate_tasks([dict(task_id=k,capability_id=k,depends_on=c['preconditions']) for k,c in body['capability_contracts'].items()],body['capability_contracts'],max_tasks=128)
        except (KeyError,TypeError,ValueError,StopIteration):fail('Package references, schemas or dependencies are invalid.','CLIENT_PACKAGE_INVALID',422)
        document=deepcopy(body);document['sha256']=digest(body)
        with self.store.transaction() as db:
            row=db.execute('SELECT document FROM client_knowledge_packages WHERE workspace=? AND owner=? AND package_id=? AND revision=?',(*scope,body['package_id'],body['revision'])).fetchone()
            if row and json.loads(row[0])!=document:fail('Package revisions are immutable.','CLIENT_PACKAGE_CONFLICT',409)
            if not row:db.execute('INSERT INTO client_knowledge_packages VALUES (?,?,?,?,?)',(*scope,body['package_id'],body['revision'],canonical(document)))
        return document

    def install_processes(self,auth,package_id,revision,cases):
        package=self.get(auth,package_id,revision)
        return [cases.publish(auth,p) for p in package.get('process_definitions',[])]

    def listing(self,auth):
        scope=self.scope(auth)
        with self.store.transaction(write=False) as db:
            rows=db.execute('SELECT document FROM client_knowledge_packages WHERE workspace=? AND owner=? ORDER BY package_id,revision DESC LIMIT 100',scope).fetchall()
        return dict(items=[{k:d[k] for k in ('package_id','revision','client_id','domain','ontology_version')} for d in (json.loads(r[0]) for r in rows)])

    def get(self,auth,package_id,revision):
        scope=self.scope(auth)
        if not isinstance(package_id,str) or not 1<=len(package_id)<=128 or type(revision) is not int or revision<1:fail('An exact package ID and revision are required.','CLIENT_PACKAGE_INVALID',422)
        with self.store.transaction(write=False) as db:
            row=db.execute('SELECT document FROM client_knowledge_packages WHERE workspace=? AND owner=? AND package_id=? AND revision=?',(*scope,package_id,revision)).fetchone()
        if not row:fail('Client package not found in this scope.','CLIENT_PACKAGE_NOT_FOUND',404)
        doc=json.loads(row[0]);sha=doc.pop('sha256')
        if digest(doc)!=sha:fail('Client package integrity failed.','CLIENT_PACKAGE_CHANGED',409)
        return dict(**doc,sha256=sha)

    def prepare(self,auth,package_id,revision,objective):
        p=self.get(auth,package_id,revision)
        # Capability selection belongs to the existing planner, not domain keywords.
        concepts={c['id']:c for c in p['concepts']};tasks={}
        for cid,c in p['capability_contracts'].items():
            names=set(c['required_ontology']);pending=list(names)
            while pending:
                parent=concepts[pending.pop()].get('parent')
                if parent and parent not in names:names.add(parent);pending.append(parent)
            mids=p['resource_bindings'].get(cid,{}).get('mapping_ids',[])
            tasks[cid]=dict(concepts=[deepcopy(concepts[x]) for x in sorted(names)],relationships=[r for r in p['relationships'] if r['source'] in names and r['target'] in names],mappings=[m for m in p['source_mappings'] if m['id'] in mids],rules=deepcopy(p['rules']),dependency_resolution={'complete':True})
        pins=dict(ontology_version=p['ontology_version'],knowledge_sha256=p['sha256'],mapping_sha256=digest(p['source_mappings']),package_sha256=p['sha256'],package_id=package_id,revision=revision)
        return dict(package=p,tasks=tasks,pins=pins,objective=objective)

    def read(self,auth,inputs):
        p=self.get(auth,inputs['package_id'],inputs['revision'])
        from runtime.service import RuntimeService
        RuntimeService.authorize(auth,'workflow.execute',{'admin','builder'})
        if 'tools.read' not in auth['permissions']:fail('Mapped reads require current source permission.','CLIENT_SOURCE_DENIED',403)
        binding=p['resource_bindings'].get(inputs['capability_id'])
        provider=self.providers.get((*self.scope(auth),binding['source_id'])) if binding else None
        if not binding or provider is None:fail('An authorized source adapter is required.','CLIENT_SOURCE_UNAVAILABLE',503)
        # The operator-provided source adapter must check current source ownership;
        # the package alone is not a credential or a source access grant.
        rows=provider(auth,deepcopy(binding))
        if not isinstance(rows,list) or len(rows)>1000:fail('Source read exceeded its configured bound.','CLIENT_SOURCE_INVALID',422)
        mappings=[m for m in p['source_mappings'] if m['id'] in binding['mapping_ids']]
        records=[];missing=[];outcomes=[];seen={};conflicting=False
        if not rows:missing=[r['mapping_id'] for r in p['evidence_requirements'] if r['capability_id']==inputs['capability_id']]
        stamp=datetime.now(timezone.utc).isoformat()
        for row in rows:
            if not isinstance(row,dict) or not isinstance(row.get('id'),str):fail('Source rows require stable identifiers.','CLIENT_SOURCE_INVALID',422)
            values={m['id']:row[m['field']] for m in mappings if m['field'] in row}
            for r in p['evidence_requirements']:
                if r['capability_id']==inputs['capability_id'] and (r['mapping_id'] not in values or values[r['mapping_id']] is None):missing.append(r['mapping_id'])
            if row['id'] in seen and seen[row['id']]!=values:conflicting=True
            seen[row['id']]=deepcopy(values)
            record=dict(record_id=row['id'],collection=binding['source_id'],source_reference=binding['source_id'],read_at=stamp,values=values)
            records.append(record)
            for rule in p['rules']:
                left=values.get(rule['left_mapping']);right=values.get(rule['right_mapping'])
                if type(left) not in (int,float) or type(right) not in (int,float) or not math.isfinite(left) or not math.isfinite(right):
                    missing.append(rule['id']);continue
                operators={'lt':lambda a,b:a<b,'lte':lambda a,b:a<=b,'eq':lambda a,b:a==b,'gt':lambda a,b:a>b,'gte':lambda a,b:a>=b}
                outcomes.append(dict(rule_id=rule['id'],record_id=row['id'],matched=operators[rule['operator']](left,right),classification='configured_rule_result'))
        evidence=dict(request_id='package_'+digest([p['sha256'],inputs])[:24],version_id=p['ontology_version'],knowledge_sha256=p['sha256'],records=records,
                      coverage=dict(state='conflicting_evidence' if conflicting else 'needs_input' if missing else 'ready',conclusion_ready=not missing and not conflicting,blocking_requirements=[{'fact_id':m} for m in sorted(set(missing))]),rule_results=outcomes)
        if 'row_budget_bytes' in binding:
            evidence['coverage'].update(basis='bounded_snapshot_sample',complete_dataset=False,
                returned_rows=len(records),max_rows=binding['limit'],
                conclusion_ready_scope='Only the returned projected records; not exhaustive findings or totals.')
        reject_secrets(evidence)
        if len(canonical(evidence).encode())>100000:fail('Mapped evidence is too large.','CLIENT_SOURCE_INVALID',422)
        graph=getattr(self,'account_graph',None)
        if graph:evidence['account_graph_pin']=graph.sync_package(auth,self,p,evidence,inputs['capability_id'])
        return evidence


def package_tool_definition():
    from .business_preparation import retrieval_tool_definition
    tool=retrieval_tool_definition();tool.update(tool_id='client_package_read',capability='business.retrieve_package_evidence',description='Read authorized mapped client-package evidence and evaluate configured scalar comparison rules.',input_schema=deepcopy(PACKAGE_INPUT),output_schema=deepcopy(PACKAGE_OUTPUT))
    return tool


class PackageEvidenceConnector:
    external_write=False
    retry_safe=True
    timeout=45
    def __init__(self,packages,auth=None,pin=None):self.packages,self.auth,self.pin=packages,auth,pin
    def reservation(self,grant):return dict(tool_calls=1,tokens=0,llm_calls=0,estimated_cost_usd=0)
    def bind_context(self,workflow,run,auth,node):
        pin=workflow['metadata'].get('client_package_pin')
        if not pin:fail('Use a pinned client package.','CLIENT_PACKAGE_CHANGED',422)
        p=self.packages.get(auth,pin['package_id'],pin['revision'])
        if p['sha256']!=pin['package_sha256']:fail('Pinned client package changed.','CLIENT_PACKAGE_CHANGED',409)
        return PackageEvidenceConnector(self.packages,deepcopy(auth),deepcopy(pin))
    def invoke(self,grant,inputs,effect_id):
        if (not self.auth or not self.pin or inputs.get('package_id')!=self.pin['package_id'] or inputs.get('revision')!=self.pin['revision'] or grant.get('tool_id')!='client_package_read'):
            fail('Read is outside its workflow-bound package.','CLIENT_SOURCE_DENIED',403)
        return self.packages.read(self.auth,inputs)
