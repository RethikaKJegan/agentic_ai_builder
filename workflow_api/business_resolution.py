"""Pure, saved-knowledge prompt resolution. No database records or model I/O."""
from collections import deque
from copy import deepcopy
import re
from .business_knowledge_model import digest, fail
from .kg_retrieval import terms

VERSION = 'simpson-retrieval-v1'
SUPPORT_MAPPINGS = {
 'complaints':['code_value','code_description','code_type','code_active'],
 'inspection':['code_value','code_description','code_type','code_active','engineer_name','engineer_active','timeline_stage','timeline_description','timeline_created'],
 'history':['code_value','code_description','code_type','code_active','timeline_stage','timeline_description','timeline_created','invoice_company_reference','invoice_list'],
 'warranty':['invoice_company_reference','invoice_list'],
}
TASKS = {
    'complaints': ('complaints:warranty_ticket', ['ticket_serial','ticket_id','complaint_symptom','complaint_oem_notes','complaint_hours','ticket_hours','complaint_status','complaint_created']),
    'inspection': ('inspection:joint_inspection', ['ticket_serial','ticket_id','complaint_symptom','complaint_oem_notes','inspection_status','inspection_date','inspection_failure_date','inspection_potential_cause','inspection_complaint_text','inspection_defect_text']),
    'warranty': ('warranty:warranty_assessment', ['ticket_serial','ticket_id','complaint_hours','ticket_hours','sale_date','invoice_serial','invoice_date']),
    'replacement': ('replacement:replacement_case', ['ticket_serial','ticket_id','replacement_mode','part_replacement_mode','dispatch_serial','dispatch_status','inspection_status']),
    'history': ('engines:engine_invoice_record', ['ticket_serial','ticket_id','complaint_symptom','invoice_serial','invoice_date','qa_serial','qa_defect','qa_status']),
    'recurrence': ('monitoring:recurrence_event', ['invoice_serial','qa_serial','qa_defect','qa_status','qa_effective_date']),
    'unsupported': (None, []),
}
# Application vocabulary expands retrieval terms only; it never equates diagnoses.
SYNONYMS = {'motor':'engine', 'motors':'engine', 'breakdown':'complaint failure',
            'breakdowns':'complaint failure', 'service issues':'complaint', 'customer issue':'complaint',
            'customer issues':'complaint', 'cooling':'cooling', 'jir':'joint inspection report'}
FACTS = {
    'operating_hours': ('source_mapping', ['complaint_hours']),
    'sale_date': ('source_mapping', ['sale_date']),
    'invoice_date': ('source_mapping', ['invoice_date']),
    'engine_identity': ('derived_check', []), 'physical_identity': ('derived_check', []),
    'identity_resolved': ('derived_check', []), 'applicable_policy': ('pinned_policy', []),
    'policy_applicable': ('derived_check', []),
    'report_status': ('source_mapping', ['inspection_status']),
    'inspection_evidence_present': ('derived_check', []),
    'assessment_date': ('explicit_input', []),
}
CONDITIONS = {
    'selected policy requires sale date': {'sale_and_hours','sale_invoice_and_hours'},
    'selected policy requires invoice date': {'invoice_and_hours','sale_invoice_and_hours'},
}


def normalized(text):
    return ' '.join(re.findall(r'[a-z0-9]+', re.sub(r'([a-z])([A-Z])', r'\1 \2', text).lower()))


def expanded(text):
    value = text.lower()
    for word, replacement in SYNONYMS.items():
        value = re.sub(r'\b'+re.escape(word)+r'\b', replacement, value)
    return value


class ConceptIndex:
    """Per-request index: no mutable cache can leak a foreign owner/version."""
    def __init__(self, snapshot):
        self.snapshot = snapshot
        self.details = {d['concept_id']: d for d in snapshot['knowledge']['concept_details']}

    def search(self, question, limit=16):
        query = terms(expanded(question)); nq = normalized(expanded(question)); result = []
        for c in self.snapshot['concepts']:
            detail = self.details.get(c['id'], {})
            names = [c['id'], c['label'], *detail.get('aliases', [])]
            exact = [n for n in names if normalized(n) and (' '+normalized(n)+' ') in (' '+nq+' ')]
            attributes = ' '.join(a['business_meaning'] for a in detail.get('attributes', []))
            predicates = ' '.join(r['predicate'] for r in self.snapshot['relationships'] if c['id'] in (r['source'],r['target']))
            direct = query & terms(' '.join(names))
            context = query & terms(c['definition']+' '+attributes+' '+predicates+' '+c['module_id'])
            score = 20*len(exact)+5*len(direct)+len(context)
            if score:result.append(dict(concept_id=c['id'], score=score, matched_names=exact,
                                        matched_terms=sorted(direct), contextual_terms=sorted(context)))
        return sorted(result, key=lambda r:(-r['score'],r['concept_id']))[:limit]


def interpret(question, snapshot, inputs=None):
    if not isinstance(question,str) or not 1 <= len(question.strip()) <= 4000:
        fail('Question must contain 1–4000 characters.')
    inputs = inputs or {}; q = expanded(question); ambiguity=[]; unsupported=[]
    identifiers={}
    patterns = {
        'serial': r'\b(?:engine|motor)(?:\s+(?:serial(?:\s+number)?|number|no))?\s*[:#]?\s+([A-Za-z0-9][A-Za-z0-9_.:/-]*\d[A-Za-z0-9_.:/-]*|\d+)\b',
        'complaint_id': r'\b(?:complaint|ticket)(?:\s+(?:id|number|no))?\s*[:#]?\s+([A-Za-z0-9][A-Za-z0-9_.:/-]*\d[A-Za-z0-9_.:/-]*|\d+)\b',
    }
    for kind, pattern in patterns.items():
        found=list(dict.fromkeys(re.findall(pattern, question, re.I)))
        if len(found)>1:ambiguity.append('Multiple '+kind+' values; provide one exact identifier.')
        elif found:identifiers[kind]=found[0]
    for kind in ('serial','complaint_id'):
        if kind in inputs:
            value=inputs[kind]
            if not isinstance(value,str) or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.:/-]{0,127}',value):fail('Invalid exact identifier.')
            if kind in identifiers and identifiers[kind]!=value:ambiguity.append('Question and explicit '+kind+' disagree.')
            identifiers[kind]=value
    task='unsupported'
    if re.search(r'\b(recurrence|recur|cut.in|incorporation)\b',q):task='recurrence'
    elif re.search(r'\b(warranty|eligible|eligibility|coverage)\b',q):task='warranty'
    elif re.search(r'\b(replacement|replace|dispatch)\b',q):task='replacement'
    elif re.search(r'\b(inspection|inspect|joint|compare)\b',q):task='inspection'
    elif re.search(r'\b(history|history of|quality|qa)\b',q):task='history'
    elif re.search(r'\b(complaint|complaints|ticket|tickets|failure|failures)\b',q):task='complaints'
    if re.search(r'\b(delete|update|approve|authorize|insert|modify|send|dispatch\s+an?\s+engine)\b',q):
        unsupported.append('Operational actions are outside read-only retrieval.')
    if re.search(r'\b(count|rate|percentage|average|every|all.time|most|rank|total|trend)\b',q):
        unsupported.append('Population aggregates and rankings require a separate complete query capability.')
    if re.search(r'\b(before|after|since|between|last|yesterday|today|this month|this year)\b',q):
        unsupported.append('Natural-language time filters require an explicit supported mapping and interval; no date was assumed.')
    if re.search(r'\b(oem|mahindra|tafe|scheduled|in progress|completed|root cause|confirmed diagnosis)\b',q):
        unsupported.append('This scope or confirmed lifecycle/diagnosis condition has no supported deterministic filter; it was not assumed.')
    if re.search(r'\b(if|unless|except|not|without|either|or)\b',q):
        unsupported.append('Conditional and negative query logic is outside the supported read grammar.')
    if re.search(r'\b(priority|severity|region|plant|component|cost|amount|oil|smoke|noise|vibration|overheat\w*)\b',q):
        unsupported.append('This requested condition is outside the supported filter vocabulary; it was not dropped or interpreted as a diagnosis.')
    filters=[]
    hours=list(re.finditer(r'\b(above|over|greater than|more than|below|under|less than)\s+(\d+(?:\.\d+)?)\s*(?:hours|hmr)\b',q))
    if hours:
        for h in hours:
            op='lt' if h[1] in ('below','under','less than') else 'gt'
            filters.append(dict(mapping_id='mapping:complaint_hours',operator=op,value=h[2],mode='bounded_post_conversion'))
    elif re.search(r'\b(hours|hmr)\b',q) and re.search(r'\b(above|over|below|under|less|more|greater)\b',q):
        unsupported.append('The numeric hours condition could not be interpreted safely.')
    if re.search(r'[<>]|=\s*[-\d]',q):unsupported.append('Symbolic numeric predicates are outside the supported phrase grammar.')
    if re.search(r'\bcooling(?:.related)?\b',q):
        filters.append(dict(mapping_id='mapping:complaint_symptom',operator='contains',value='cool',mode='bounded_post_conversion'))
    elif re.search(r'\brelated\b',q):unsupported.append('Specify a supported symptom search; related symptoms are not equivalent diagnoses.')
    statuses=list(dict.fromkeys(s.upper() for s in re.findall(r'\b(OPENED|RESOLVED|CLOSED|REOPENED|DRAFTED|PUBLISHED)\b',question,re.I)))
    if len(statuses)>1:ambiguity.append('Multiple status values require an explicit supported combination; none was assumed.')
    elif statuses:
        status=statuses[0]
        filters.append(dict(mapping_id='mapping:inspection_status' if status in ('DRAFTED','PUBLISHED') else 'mapping:complaint_status',operator='eq',value=status,mode='exact'))
    if task=='unsupported':unsupported.append('No supported retrieval task was identified.')
    if not identifiers and not filters:ambiguity.append('Provide an engine serial, complaint ID, or supported bounded symptom/status filter.')
    if len(identifiers)>1:ambiguity.append('Choose an engine serial or a complaint ID as the retrieval anchor.')
    if re.search(r'\b(this complaint|its inspection)\b',q) and not identifiers:ambiguity.append('The referenced complaint has no explicit identifier.')
    candidates=ConceptIndex(snapshot).search(question)
    cid=TASKS[task][0]
    valid={c['id'] for c in snapshot['concepts']}
    concepts=[cid] if cid in valid else []
    return dict(task=task,concept_ids=concepts,identifiers=identifiers,
                requested_facts=[],filters=filters,time_references=[dict(text=t,state='unresolved') for t in re.findall(r'\b(?:before|after|since|between|last|yesterday|today)\b',q)],business_scope='Simpson',
                ambiguities=ambiguity,unsupported=unsupported,candidates=candidates,
                interpretation='deterministic',model_calls=0)


def closure(snapshot, roots, inputs, max_items=96):
    k=snapshot['knowledge']; concepts={c['id']:c for c in snapshot['concepts']}
    rels={r['id']:r for r in snapshot['relationships']}
    seen=set(); relationships=set(); mappings=set(); rules=set(); facts=set(); deps=[]; conditions=[]; pending=deque(roots)
    policies=k['manifest']['policy_snapshots']; selected=next((p for p in policies if p['policy_id']==inputs.get('policy_id')),None)
    mode=((selected or {}).get('clauses',{}).get('coverage_mode') or {}).get('value')
    while pending:
        cid=pending.popleft()
        if cid in seen:continue
        if cid not in concepts:fail('Dependency refers to an unknown saved concept.')
        seen.add(cid)
        if len(seen)+len(relationships)+len(mappings)+len(rules)>max_items:
            return dict(complete=False,reason='required_knowledge_limit',concept_ids=sorted(seen),relationship_ids=sorted(relationships),mapping_ids=sorted(mappings),rule_ids=sorted(rules),required_facts=sorted(facts),dependencies=deps,conditions=conditions)
        parent=concepts[cid].get('parent_id')
        if parent:pending.append(parent)
        for d in k['dependencies']:
            if d['subject_id']!=cid:continue
            deps.append(d['id']);pending.extend(d['concepts']);relationships.update(d['relationships']);mappings.update(d['mappings']);rules.update(d['rules']);facts.update(d['required_facts'])
            for rule in k['structured_rules']:
                if rule['id'] in d['rules']:facts.update(rule['required_facts'])
            for rid in d['relationships']:
                pending.extend((rels[rid]['source'],rels[rid]['target']))
            for condition in d['conditional']:
                allowed=CONDITIONS.get(condition['when'])
                state='unsupported_predicate' if allowed is None else 'unknown' if mode is None else 'true' if mode in allowed else 'false'
                conditions.append(dict(predicate=condition['when'],state=state))
                # Unknown condition keeps requirements visible, never drops them.
                if state!='false':
                    pending.extend(condition['concepts']);mappings.update(condition['mappings']);facts.update(condition['required_facts'])
    complete=len(seen)+len(relationships)+len(mappings)+len(rules)<=max_items and not any(c['state']=='unsupported_predicate' for c in conditions)
    return dict(complete=complete,reason=None if complete else 'required_knowledge_limit_or_predicate',concept_ids=sorted(seen),relationship_ids=sorted(relationships),mapping_ids=sorted(mappings),rule_ids=sorted(rules),required_facts=sorted(facts),dependencies=deps,conditions=conditions)


def resolve(snapshot, question, inputs=None, intent=None, max_items=96):
    inputs=inputs or {};k=snapshot.get('knowledge')
    if not k:fail('Import Phase 1 knowledge into this isolated workspace first.','BUSINESS_RETRIEVAL_KNOWLEDGE_REQUIRED',409)
    if digest(k)!=snapshot.get('knowledge_sha256'):fail('Saved knowledge hash mismatch.')
    intent=deepcopy(intent or interpret(question,snapshot,inputs))
    maps={m['id']:m for m in k['source_mappings']}
    base_ids={'mapping:'+x for x in TASKS[intent['task']][1]}
    base_ids.update('mapping:'+x for x in SUPPORT_MAPPINGS.get(intent['task'],[]) if 'mapping:'+x in maps)
    if intent['task']=='recurrence' and intent['identifiers'].get('complaint_id'):base_ids.update({'mapping:ticket_id','mapping:ticket_serial'})
    base_ids.update(f['mapping_id'] for f in intent['filters'])
    if re.search(r'\b(build date|manufactur\w* date)\b',question,re.I):base_ids.add('mapping:engine_build_date')
    if re.search(r'\b(model)\b',question,re.I):base_ids.add('mapping:invoice_model')
    roots=set(intent['concept_ids']);ids=set(base_ids)
    # A mapping can introduce a concept which itself has dependencies. Expand to
    # a fixed point, rather than stopping after a single concept/field pass.
    for _ in range(max_items+1):
        dep=closure(snapshot,sorted(roots),inputs,max_items)
        needed=ids | set(dep['mapping_ids'])
        for name in dep['required_facts']:
            needed.update('mapping:'+m for m in FACTS.get(name,('unavailable',[]))[1])
        next_roots=roots | {maps[mid]['concept_id'] for mid in needed if mid in maps}
        if needed==ids and next_roots==roots:break
        ids,roots=needed,next_roots
        if not dep['complete']:break
    else:
        dep['complete']=False;dep['reason']='dependency_expansion_limit'
    providers=[]
    for name in dep['required_facts']:
        kind,names=FACTS.get(name,('unavailable',[]))
        mid=['mapping:'+m for m in names]
        state='requires_evidence' if kind in ('source_mapping','derived_check') else 'supplied' if kind=='explicit_input' and inputs.get(name) else 'selected' if kind=='pinned_policy' and any(p['policy_id']==inputs.get('policy_id') for p in k['manifest']['policy_snapshots']) else 'missing'
        providers.append(dict(fact=name,provider=kind,mapping_ids=mid,state=state,
                              qualification='Policy selection does not prove applicability.' if kind=='pinned_policy' else None))
    intent['requested_facts']=dep['required_facts']
    dep['provider_mapping_ids']=sorted({mid for p in providers for mid in p['mapping_ids']})
    missing=[dict(fact=p['fact'],reason=p['state']) for p in providers if p['state']=='missing']
    missing.extend(dict(mapping_id=i,reason='missing_mapping') for i in sorted(ids) if i not in maps)
    selected=[deepcopy(maps[i]) for i in sorted(ids) if i in maps]
    for m in selected:
        m['version_id']=snapshot['version_id']
    return dict(retrieval_version=VERSION,version_id=snapshot['version_id'],knowledge_sha256=snapshot['knowledge_sha256'],
                intent=intent,dependency_resolution=dep,fact_providers=providers,mappings=selected,
                concepts=[deepcopy(c) for c in snapshot['concepts'] if c['id'] in dep['concept_ids']],
                relationships=[deepcopy(r) for r in snapshot['relationships'] if r['id'] in dep['relationship_ids']],
                rules=[deepcopy(r) for r in k['structured_rules'] if r['id'] in dep['rule_ids']],
                policies=deepcopy([p for p in k['manifest']['policy_snapshots'] if intent['task']=='warranty' and (not inputs.get('policy_id') or p['policy_id']==inputs['policy_id'])]),
                state_models=deepcopy([s for s in k['state_models'] if s.get('mapping_id') in ids]),
                temporal_models=deepcopy([t for t in k['temporal_models'] if t.get('mapping_id') in ids or t['concept_id'] in dep['concept_ids']]),missing=missing,
                ready=dep['complete'] and not intent['unsupported'] and not intent['ambiguities'])
