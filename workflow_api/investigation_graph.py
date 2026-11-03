"""Versioned read-only investigation capabilities and typed DAG validation."""
from copy import deepcopy
import re
from jsonschema import Draft202012Validator
from .business_knowledge_model import digest
from .business_evidence import REGISTRY_SHA256
from .service import ApiFailure

VERSION='simpson-investigation-v1'
LIMITS=dict(max_nodes=32,max_parallel=3,max_seconds=240,max_model_calls=6,max_agent_tokens=14000,max_agent_seconds=45,max_agent_cost_usd=0.25,max_evidence_bytes=500000,max_run_bytes=2500000,max_retries=1)
TYPES=['context','evidence','analysis','gap','control','report','bundle']
NODE_TYPES=['start','retrieval','deterministic','agent','condition','parallel','join','human_input','end']
PREDICATES=['complaint_found','inspection_available','facts_present','identity_supported','evidence_truncated','source_value_valid','authorization_present','assessment_inputs_complete']


def fail(message,code='INVESTIGATION_INVALID',status=422):raise ApiFailure(code,message,status)


def object_schema(properties,required=None):
    return dict(type='object',additionalProperties=False,properties=properties,required=list(properties) if required is None else required)


REF_SCHEMA=object_schema({'record_id':{'type':'string'},'mapping_id':{'type':'string'}})
FINDING_SCHEMA=object_schema({'kind':{'type':'string','enum':['agreement','discrepancy','observation','limitation','unverified']},'statement':{'type':'string','minLength':1,'maxLength':1500},'references':{'type':'array','maxItems':12,'items':REF_SCHEMA}})
ANALYSIS_SCHEMA=object_schema({'summary':{'type':'string','maxLength':3000},'findings':{'type':'array','maxItems':16,'items':FINDING_SCHEMA},'missing_information':{'type':'array','maxItems':24,'items':{'type':'string','maxLength':500}}})
EVIDENCE_SCHEMA={'type':'object','required':['version_id','knowledge_sha256','records','missing','completeness']}
CONTEXT_SCHEMA=object_schema({'identifiers':object_schema({'complaint_id':{'type':'string','maxLength':128},'serial':{'type':'string','maxLength':128}},[]),'assessment_date':{'type':'string'},'policy_id':{'type':'string'}},['identifiers'])


def capability(cid,name,kind,task=None,required=(),optional=(),concepts=()):
    return dict(id=cid,name=name,purpose=name,kind=kind,retrieval_task=task,
                input_schema=object_schema({k:{'type':'object'} for k in (*required,*optional)},list(required)),
                input_types={k:('context' if k=='context' else 'evidence' if k=='evidence' else 'bundle') for k in (*required,*optional)},
                output_schema=EVIDENCE_SCHEMA if kind=='retrieval' else ANALYSIS_SCHEMA if kind=='agent' else {'type':'object'},
                output_type='evidence' if kind=='retrieval' else 'analysis' if kind=='agent' else 'gap',
                required_ontology=list(concepts),required_evidence=list(required),implementation='phase2_retrieval' if kind=='retrieval' else 'bounded_crewai' if kind=='agent' else 'backend_missing_information',
                permissions=['tools.read','workspace:read'],limits=deepcopy(LIMITS),retry_policy=dict(max_retries=1 if kind=='retrieval' else 0,retryable_codes=['BUSINESS_SOURCE_UNAVAILABLE'] if kind=='retrieval' else []),read_only=True)


CAPABILITIES=[
 capability('retrieve_complaint','Retrieve complaint evidence','retrieval','complaints',('context',),concepts=('complaints:warranty_ticket',)),
 capability('retrieve_inspection','Retrieve linked inspection evidence','retrieval','inspection',('context',),concepts=('inspection:joint_inspection',)),
 capability('retrieve_warranty','Collect warranty assessment inputs','retrieval','warranty',('context',),concepts=('warranty:warranty_assessment',)),
 capability('retrieve_replacement','Review replacement evidence','retrieval','replacement',('context',),concepts=('replacement:replacement_case',)),
 capability('retrieve_history','Retrieve complaint, invoice and QA history','retrieval','history',('context',),concepts=('engines:engine_invoice_record',)),
 capability('retrieve_recurrence','Review effectiveness evidence and prerequisites','retrieval','recurrence',('context',),concepts=('monitoring:recurrence_event',)),
 capability('compare_inspection','Compare complaint and inspection observations','agent',required=('evidence',)),
 capability('warranty_readiness','Review pinned warranty readiness and gaps','agent',required=('evidence',)),
 capability('prepare_summary','Prepare source-backed investigation summary','agent',required=('bundle',)),
 capability('request_missing','Identify missing information','deterministic',optional=('bundle',)),
]
CATALOGUE={c['id']:c for c in CAPABILITIES}
CATALOGUE_HASH=digest([CAPABILITIES,REGISTRY_SHA256])

BINDING_SCHEMA=object_schema({'name':{'type':'string','enum':['context','evidence','bundle']},'source':{'type':'string','pattern':'^[a-z][a-z0-9_]{0,63}$'},'type':{'type':'string','enum':TYPES}})
NODE_SCHEMA=object_schema({'id':{'type':'string','pattern':'^[a-z][a-z0-9_]{0,63}$'},'type':{'type':'string','enum':NODE_TYPES},
 'capability':{'type':['string','null'],'enum':[None,*CATALOGUE]},'predicate':{'type':['string','null'],'enum':[None,*PREDICATES]},
 'inputs':{'type':'array','maxItems':4,'items':BINDING_SCHEMA},'output_type':{'type':'string','enum':TYPES},
 'constraints':object_schema({'max_attempts':{'type':'integer','minimum':1,'maximum':2},'timeout_seconds':{'type':'integer','minimum':1,'maximum':45}}),
 'on_error':{'type':'string','enum':['stop','continue']},'join_mode':{'type':'string','enum':['all_selected','none']}})
EDGE_SCHEMA=object_schema({'id':{'type':'string','pattern':'^[a-z][a-z0-9_]{0,63}$'},'source':{'type':'string'},'target':{'type':'string'},'outcome':{'type':['string','null'],'enum':[None,'true','false','unknown']}})
GRAPH_SCHEMA=object_schema({'schema_version':{'type':'string','const':VERSION},'nodes':{'type':'array','minItems':3,'maxItems':32,'items':NODE_SCHEMA},'edges':{'type':'array','maxItems':80,'items':EDGE_SCHEMA}})


def requirements(objective):
    if not isinstance(objective,str) or not 1<=len(objective.strip())<=4000:fail('Provide an objective of 1–4000 characters.')
    q=objective.lower()
    # Excluded clauses must not add capabilities just because they name them.
    # Keep subsequent positive clauses ("but", "however", "instead") separate.
    q=re.sub(r"\b(?:do not|don't|don’t|must not|should not|without)\b(?:(?!\b(?:but|however|instead)\b)[^.;\n])*",' ',q)
    if re.search(r'\b(delete|update|approve|authorize|insert|modify|send|email|notify|dispatch an? engine|schedule a meeting)\b',q):fail('Operational actions are not investigation capabilities.','INVESTIGATION_UNSUPPORTED')
    evidence_review=bool(re.search(r'\b(recurrence|effectiveness|corrective.action)\b',q) and re.search(r'\b(evidence|readiness)\b',q))
    if re.search(r'\b(count|percentage|rate|average|rank|trend|cut.in)\b',q) or re.search(r'\brecurrence\b',q) and not evidence_review:fail('Population metrics and operational recurrence workflows are outside this investigation scope.','INVESTIGATION_UNSUPPORTED')
    result=dict(inspection=bool(re.search(r'\b(inspect\w*|compare|joint|jir)\b',q)),warranty=bool(re.search(r'\b(warranty|eligib\w*|coverage)\b',q)),replacement=bool(re.search(r'\b(replacement|replace)\b',q)),history=bool(re.search(r'\b(history|historical|qa|quality)\b',q)),summary=True)
    result['recurrence']=evidence_review
    if not re.search(r'\b(complaint|complaints|ticket|engine|motor|investigat\w*|service issue|inspection|warranty|replacement)\b',q):fail('No supported Simpson investigation objective was identified.','INVESTIGATION_UNSUPPORTED')
    return result


def validate_graph(graph,required=None):
    errors=[]
    violations=list(Draft202012Validator(GRAPH_SCHEMA).iter_errors(graph))
    if violations:return dict(valid=False,errors=[dict(code='SCHEMA_INVALID',path=list(e.absolute_path),message=e.message[:300]) for e in violations[:12]])
    nodes={n['id']:n for n in graph['nodes']};edges=graph['edges']
    def issue(code,node=None):errors.append(dict(code=code,node_id=node))
    if len(nodes)!=len(graph['nodes']):issue('DUPLICATE_NODE')
    if len({e['id'] for e in edges})!=len(edges):issue('DUPLICATE_EDGE')
    if len({(e['source'],e['target'],e['outcome']) for e in edges})!=len(edges):issue('DUPLICATE_PATH')
    if any(e['source'] not in nodes or e['target'] not in nodes for e in edges):return dict(valid=False,errors=[dict(code='MISSING_NODE_REFERENCE')])
    starts=[n for n in nodes.values() if n['type']=='start'];ends=[n for n in nodes.values() if n['type']=='end']
    if len(starts)!=1 or len(ends)!=1:return dict(valid=False,errors=[dict(code='START_END_REQUIRED')])
    incoming={nid:[e for e in edges if e['target']==nid] for nid in nodes};outgoing={nid:[e for e in edges if e['source']==nid] for nid in nodes}
    pending=set(nodes);order=[]
    while pending:
        ready=sorted(nid for nid in pending if all(e['source'] in order for e in incoming[nid]))
        if not ready:issue('CYCLE');break
        order.extend(ready);pending.difference_update(ready)
    ancestors={}
    for nid in order:
        ancestors[nid]=set().union(*({e['source']}|ancestors[e['source']] for e in incoming[nid])) if incoming[nid] else set()
    start,end=starts[0]['id'],ends[0]['id']
    if start!='start' or end!='end':issue('STABLE_TERMINAL_IDS')
    humans=[n for n in nodes.values() if n['type']=='human_input']
    if len(humans)!=1 or humans[0]['id']!='anchor':issue('ANCHOR_REQUIRED')
    if incoming[start] or outgoing[end]:issue('INVALID_TERMINAL_EDGES')
    for nid,n in nodes.items():
        ins,outs=incoming[nid],outgoing[nid]
        if nid!=start and start not in ancestors.get(nid,set()):issue('UNREACHABLE_NODE',nid)
        if nid!=end and nid not in ancestors.get(end,set()):issue('NO_END_PATH',nid)
        if nid!=start and not ins:issue('MISSING_DEPENDENCY',nid)
        if n['type']=='condition':
            if not n['predicate'] or len(outs)!=3 or {e['outcome'] for e in outs}!={'true','false','unknown'}:issue('BRANCH_COVERAGE',nid)
        elif n['predicate'] or any(e['outcome'] is not None for e in outs):issue('UNSUPPORTED_CONDITION',nid)
        if n['type']=='parallel' and len(outs)<2:issue('PARALLEL_REQUIRES_BRANCHES',nid)
        if n['type']=='join':
            if n['join_mode']!='all_selected' or len(ins)<2:issue('INVALID_JOIN',nid)
        elif n['join_mode']!='none':issue('UNSUPPORTED_JOIN_MODE',nid)
        cap=CATALOGUE.get(n['capability']);names=[b['name'] for b in n['inputs']]
        if len(set(names))!=len(names):issue('DUPLICATE_INPUT',nid)
        if n['type'] in ('retrieval','agent','deterministic'):
            if not cap or n['type']!=cap['kind'] or n['output_type']!=cap['output_type']:issue('CAPABILITY_TYPE',nid)
            elif set(names)!=set(cap['input_schema']['required']) and not (set(cap['input_schema']['required'])<=set(names)<=set(cap['input_types'])):issue('REQUIRED_INPUTS',nid)
            elif any(cap['input_types'][b['name']]!=b['type'] for b in n['inputs']):issue('INPUT_TYPE',nid)
            if cap and n['constraints']['max_attempts']>cap['retry_policy']['max_retries']+1:issue('CAPABILITY_RETRY_LIMIT',nid)
        elif cap:issue('CONTROL_CAPABILITY',nid)
        if n['on_error']=='continue' and n['type'] not in ('agent','retrieval'):issue('UNSUPPORTED_ERROR_CONTINUATION',nid)
        for b in n['inputs']:
            if b['source'] not in ancestors.get(nid,set()):issue('INPUT_NOT_UPSTREAM',nid)
            elif nodes[b['source']]['output_type']!=b['type']:issue('BINDING_TYPE',nid)
        if n['type']=='condition' and (len(n['inputs'])!=1 or n['inputs'][0]['type']!='evidence'):issue('CONDITION_INPUT',nid)
        if n['type']=='human_input' and n['inputs']!=[dict(name='context',source='start',type='context')]:issue('ANCHOR_INPUT',nid)
        if n['type']=='retrieval' and n['inputs']!=[dict(name='context',source='anchor',type='context')]:issue('RETRIEVAL_CONTEXT',nid)
        expected={'start':'context','human_input':'context','parallel':'control','condition':'control','join':'bundle','end':'report'}
        if n['type'] in expected and n['output_type']!=expected[n['type']]:issue('CONTROL_OUTPUT_TYPE',nid)
    caps={n['capability'] for n in nodes.values()}
    if required:
        must={'prepare_summary','retrieve_complaint'}
        if required['inspection']:must|={'retrieve_inspection','compare_inspection'}
        if required['warranty']:must|={'retrieve_warranty','warranty_readiness'}
        if required['replacement']:must.add('retrieve_replacement')
        if required['history']:must.add('retrieve_history')
        if required.get('recurrence'):must.add('retrieve_recurrence')
        if not must<=caps:issue('MISSING_REQUIRED_CAPABILITY')
        allowed=must|{'request_missing'}
        if caps-{None}-allowed:issue('UNRELATED_CAPABILITY')
    return dict(valid=not errors,errors=errors,topological_order=order)


def template(required):
    """Explicit offline structural planner and bounded model example, not execution."""
    nodes=[];edges=[]
    def node(nid,kind,cap=None,predicate=None,inputs=(),output=None):
        c=CATALOGUE.get(cap,{})
        nodes.append(dict(id=nid,type=kind,capability=cap,predicate=predicate,inputs=[dict(name=name,source=src,type=typ) for name,src,typ in inputs],output_type=output or c.get('output_type','control'),constraints=dict(max_attempts=2 if kind=='retrieval' else 1,timeout_seconds=45),on_error='stop',join_mode='all_selected' if kind=='join' else 'none'))
    def edge(a,b,outcome=None):edges.append(dict(id='edge_'+str(len(edges)+1),source=a,target=b,outcome=outcome))
    node('start','start',output='context');node('anchor','human_input',inputs=[('context','start','context')],output='context');edge('start','anchor')
    node('complaint','retrieval','retrieve_complaint',inputs=[('context','anchor','context')]);edge('anchor','complaint')
    node('found','condition',predicate='complaint_found',inputs=[('evidence','complaint','evidence')]);edge('complaint','found')
    node('not_found','deterministic','request_missing');edge('found','not_found','false')
    node('uncertain_complaint','deterministic','request_missing');edge('found','uncertain_complaint','unknown')
    tasks=[name for name in ('inspection','warranty','replacement','history','recurrence') if required.get(name)]
    node('work','parallel' if len(tasks)>1 else 'deterministic',None if len(tasks)>1 else 'request_missing',output='control' if len(tasks)>1 else None);edge('found','work','true')
    tails=[]
    for task in tasks:
        cap={'inspection':'retrieve_inspection','warranty':'retrieve_warranty','replacement':'retrieve_replacement','history':'retrieve_history','recurrence':'retrieve_recurrence'}[task]
        node(task,'retrieval',cap,inputs=[('context','anchor','context')]);edge('work',task)
        if task=='inspection':
            node('has_inspection','condition',predicate='inspection_available',inputs=[('evidence',task,'evidence')]);edge(task,'has_inspection')
            node('compare','agent','compare_inspection',inputs=[('evidence',task,'evidence')]);edge('has_inspection','compare','true')
            node('no_inspection','deterministic','request_missing');edge('has_inspection','no_inspection','false')
            node('unknown_inspection','deterministic','request_missing');edge('has_inspection','unknown_inspection','unknown')
            node('inspection_join','join',output='bundle')
            for n in ('compare','no_inspection','unknown_inspection'):edge(n,'inspection_join')
            tails.append('inspection_join')
        elif task=='warranty':
            node('warranty_review','agent','warranty_readiness',inputs=[('evidence',task,'evidence')]);edge(task,'warranty_review');tails.append('warranty_review')
        else:tails.append(task)
    if not tails:tails=['work']
    node('results','join',output='bundle')
    for nid in [*tails,'not_found','uncertain_complaint']:edge(nid,'results')
    node('summary','agent','prepare_summary',inputs=[('bundle','results','bundle')]);edge('results','summary')
    node('end','end',inputs=[('bundle','results','bundle')],output='report');edge('summary','end')
    return dict(schema_version=VERSION,nodes=nodes,edges=edges)


def predicate(name,evidence):
    """No model calls; missing/limited evidence yields explicit uncertainty."""
    if name not in PREDICATES:fail('Unknown backend predicate.')
    if evidence.get('error') or not isinstance(evidence.get('records'),list):return 'unknown'
    records=evidence['records'];steps=evidence.get('executed_steps',[])
    incomplete=any(s.get('truncated') or s.get('unresolved') for s in steps)
    if name=='evidence_truncated':return 'true' if any(s.get('truncated') for s in steps) else 'false'
    if name in ('complaint_found','inspection_available'):
        collection='tickets' if name=='complaint_found' else 'jointinspectionreports'
        if any(r['collection']==collection for r in records):return 'true'
        scoped=[s for s in steps if s.get('collection')==collection]
        if scoped:return 'unknown' if any(s.get('truncated') or s.get('unresolved') for s in scoped) else 'false'
        if incomplete:return 'unknown'
        if any(m.get('reason') in ('no_supported_anchored_path','reference_or_projection_unavailable') for m in evidence.get('missing',[])):return 'unknown'
        # A completed empty exact collection read is evidence of no linked match.
        return 'false'
    if name=='identity_supported':return 'true' if evidence.get('physical_engine_identity')=='verified' else 'unknown'
    if name=='source_value_valid':return 'false' if evidence.get('conversion_issues') else 'unknown' if not records else 'true'
    if name=='authorization_present':return 'unknown'  # Recorded replacement mode is not authorization.
    if name in ('facts_present','assessment_inputs_complete'):
        return 'unknown' if evidence.get('missing') or evidence.get('conversion_issues') or incomplete or not records else 'true'
    return 'unknown'
