"""Run-owned adaptive control; GraphRunner remains the only action executor.

This shares the existing evaluator/provider, plan compiler, Registry grants,
working-memory bounds and run checkpoints. It has no business-case dependency.
"""
from copy import deepcopy
import json
import re
from pathlib import Path
from uuid import uuid4

from jsonschema import Draft202012Validator, FormatChecker
from registry.safety import reject_secrets
from runtime.service import RuntimeFailure, digest
from runtime.memory import bounded_context
from runtime.adaptive_context import DEFAULT_LIMITS, brief
from .service import ApiFailure

CONTRACT = json.loads((Path(__file__).parents[1] / 'shared/contracts/investigation-assessment-v1.json').read_text())
VALIDATOR = Draft202012Validator(CONTRACT)
KIND = 'workflow-investigation'


def fail(code, message):
    raise RuntimeFailure(code, message, 409)


def controlled(workflow):
    return workflow.get('metadata', {}).get('adaptive_control', {}).get('kind') == KIND


def initialize(run, workflow):
    if not controlled(workflow) or 'adaptive' in run:
        return
    plan = workflow['metadata']['connected_action_plan']
    control = workflow['metadata']['adaptive_control']
    limits = {**DEFAULT_LIMITS, 'evaluator_output_tokens':6000, 'max_retrieval_rounds': 4, 'max_no_progress': 2}
    limits.update(control.get('limits', {}))
    if set(limits) != set(DEFAULT_LIMITS) | {'max_retrieval_rounds','max_no_progress'} or any(type(v) is not int or v < 1 for v in limits.values()):
        fail('ADAPTIVE_BUDGET_INVALID', 'Adaptive budgets must be bounded positive integers.')
    run['adaptive'] = dict(kind=KIND, objective=plan['goal'], revision=1,
        status='active', turns=0, retrieval_rounds=0, no_progress=0, decisions=[],
        requirements=[], assessment=None, pending_wait=None, revisions=[],
        retired_action_ids=[], deadline=run['created_at'] + limits['max_seconds'], limits=limits)
    run['adaptive_limits'] = limits
    run['adaptive_reasoning_usage'] = dict(tokens=0, llm_calls=0)


def effective(run, approved):
    """Root approval is revalidated by RuntimeService before this projection."""
    revised = run.get('adaptive_workflow')
    if not revised:
        return approved
    if not controlled(approved) or digest(revised) != run.get('adaptive_workflow_digest'):
        fail('ADAPTIVE_REVISION_INVALID', 'Adaptive revision integrity check failed.')
    for field in ('workflow_id', 'version', 'agents', 'tools', 'execution_policy', 'approval_gates'):
        if revised[field] != approved[field]:
            fail('ADAPTIVE_AUTHORITY_CHANGED', 'Adaptive revision cannot change reviewed execution authority.')
    return revised


def presentation_document(doc, workflow):
    """Project current tasks without changing the original reviewed composition."""
    result=deepcopy(doc)
    templates={t['capability_id']:t for t in doc['tasks']}
    configs={t['capability_id']:next(c for c in doc['configurations'] if c['assigned_task']==t['task_id']) for t in doc['tasks']}
    result.update(action_plan=deepcopy(workflow['metadata']['connected_action_plan']),tasks=[],configurations=[],selected_tools={})
    for action in result['action_plan']['actions']:
        template=templates[action['capability_id']]
        result['tasks'].append(dict(template,task_id=action['action_id'],depends_on=action['depends_on'],condition=action['when']))
        result['configurations'].append(dict(deepcopy(configs[action['capability_id']]),assigned_task=action['action_id']))
        if template['task_id'] in doc['selected_tools']:
            result['selected_tools'][action['action_id']]=deepcopy(doc['selected_tools'][template['task_id']])
    return result


def evidence(runtime, db, run, workflow, auth):
    """Only completed, scoped connector receipts become business evidence.

    Model output, source catalogues and filenames remain context, not facts.
    Actual record/document evidence retains the existing verifier's provenance.
    """
    from .business_knowledge_model import digest as query_digest
    result, limitations = {}, []
    plan = workflow['metadata']['connected_action_plan']
    actions = {a['action_id']: a for a in plan['actions']}
    scope = dict(workspace_id=run['workspace_id'], owner_id=run['subject_id'])
    # Recheck current owned source/credential generations before interpreting
    # saved receipts. A historical successful read is not a fresh authorization.
    current_catalog=runtime.workflows.subway_queries.catalog(auth)
    for aid, item in run.get('action_instances', {}).items():
        if item.get('state') != 'completed' or not item.get('verified_receipt') or aid not in actions:
            continue
        output = item['output']
        valid = True
        cid = actions[aid]['capability_id']
        # Delivery confirms execution, not source-backed business facts.
        if workflow['metadata']['connected_contracts'][cid]['side_effect'] in ('draft', 'write'):
            continue
        if cid == 'tool.subway_query':
            query = item.get('resolved_inputs', {}).get('query')
            row = db.execute('SELECT document FROM subway_query_receipts WHERE workspace=? AND owner=? AND query_id=?',
                (run['workspace_id'], run['subject_id'], output.get('query_id'))).fetchone()
            receipt = json.loads(row[0]) if row else {}
            version = workflow['metadata']['action_binding_context']['validated_context']['subway_query_catalog']['ontology_version']
            valid = (output.get('scope') == scope and output.get('ontology_version') == version
                and output.get('query_sha256') == query_digest(query)
                and receipt.get('query_sha256') == output.get('query_sha256')
                and receipt.get('sources') == output.get('sources')
                and receipt.get('coverage') == output.get('coverage')
                and receipt.get('join_checks') == output.get('join_checks')
                and receipt.get('source_authority_sha256')==query_digest(current_catalog['stamps'])
                and item.get('output_fingerprint') == digest(output)
                and output.get('coverage', {}).get('complete_scan') is True)
            overview=workflow['metadata'].get('overview_intent',{})
            if overview.get('subway_temporal'):
                from .subway_automation import date_filters
                from .source_freshness import covers
                filters=date_filters(overview,run)
                if not all(covers(source,filters) for source in output.get('sources',[])):
                    valid=False
                    limitations.append(dict(action_id=aid,code='SOURCE_FRESHNESS_UNVERIFIED',details='Source synchronization does not establish coverage of the requested reporting period. Historical snapshots and metadata profiling are not current business activity.'))
            # A complete scan is not complete returned detail or known semantics.
            coverage = output.get('coverage', {})
            if coverage.get('truncated') or coverage.get('warnings'):
                valid = False
                limitations.append(dict(action_id=aid, code='QUERY_SCOPE_LIMITATION', details=deepcopy(coverage)))
            elif coverage.get('has_more') and not coverage.get('aggregate_complete'):
                limitations.append(dict(action_id=aid, code='QUERY_DETAIL_PAGINATED', details=deepcopy(coverage)))
        elif cid=='tool.subway_documents':
            from hashlib import sha256
            records=output.get('records',[])
            valid=bool(records) and output.get('scope')==scope and all(r.get('scope')==scope and r.get('content_available') is True
                and isinstance(r.get('text'),str) and sha256(r['text'].encode()).hexdigest()==r.get('excerpt_sha256') for r in records)
            limitations.extend(dict(action_id=aid,code='DOCUMENT_SCOPE_LIMITATION',details=text) for text in output.get('limitations',[]))
        elif 'records' in output:
            # Existing retrieval verifier is authoritative for actual contents.
            records = output.get('records', [])
            valid = bool(records) and output.get('completeness') == 'complete'
            if item.get('provenance_type') == 'SYNTHETIC':
                valid = False
            if any(r.get('scope') and r['scope'] != scope for r in records):
                valid = False
        else:
            valid = False
        eid = 'evidence:' + digest([run['run_id'], aid, item['output_fingerprint']])[:32]
        result[eid] = dict(evidence_id=eid, action_id=aid, valid=valid,
            output=deepcopy(output), provenance=item.get('provenance_type'),
            plan_revision=run['adaptive']['revision'])
        if not valid:
            limitations.append(dict(action_id=aid, code='EVIDENCE_INCOMPLETE_OR_UNVERIFIED'))
    return result, limitations


def evidence_preview(output):
    """Retain receipt metadata independently of sorted field order and row depth.

    The enclosing context budget still applies. Only rows are sampled. Never
    insert projection annotations inside evidence: they are not receipt facts.
    """
    if 'query_id' not in output or 'coverage' not in output or 'sources' not in output:
        return brief(output)
    result = deepcopy(output)
    result['rows'] = result.get('rows', [])[:4]
    return result


def context(runtime, db, run, workflow, auth):
    a = run['adaptive']
    ev, limitations = evidence(runtime, db, run, workflow, auth)
    plan = workflow['metadata']['connected_action_plan']
    # Bounded rows are previews; full receipts remain persisted, never summarized
    # as an exhaustive population. Exact copied values are checked on commit.
    ctx = dict(evaluation_kind=KIND, original_objective=a['objective'],
        scope=deepcopy(plan['scope']), constraints=deepcopy(plan['constraints']),
        automation_trigger=brief(run.get('automation_reference',{})),
        execution_scope=dict(kind='automation_occurrence' if run.get('automation_reference') else 'reviewed_workflow',
            business_requirements='Source-backed findings and requested analysis only. Do not include report drafting, mail delivery or schedule creation as business evidence requirements.',
            schedule_management='The durable scheduler validates the owned schedule, occurrence and recurring authorization before this evaluator runs. This occurrence does not create a schedule. Do not request schedule creation receipts from query/report actions.',
            delivery_management='Report and delivery actions remain in plan.actions and completion_criteria. Business completion_eligible permits their reviewed execution; final complete still requires their actual completed action states and approvals.'),
        plan=deepcopy(plan), frozen_requirements=deepcopy(a['requirements']),
        evidence={k:{**v, 'output':evidence_preview(v['output'])} for k,v in ev.items()},
        evidence_projection='Evidence output.rows contains at most four preview rows. Full verified receipts are persisted and supplied to reporting actions. Use executed coverage metadata for scan/aggregate completeness; never infer population totals from this preview. Display pagination does not invalidate an authenticated complete-scan receipt. Returned detail supports only the returned records; matched counts and join coverage retain their executed scope. Explicitly disclose incomplete detail in source_limitations. Do not claim exhaustive comparisons, population totals or absence of exceptions from a page; requirements needing unreturned detail remain unsatisfied unless other complete evidence supports them. Projection annotations are not source facts.',
        deterministic_limitations=limitations, previous_assessment=a['assessment'],
        completed_actions=[k for k,v in run.get('action_instances', {}).items() if v.get('state') == 'completed'],
        failures=deepcopy(run.get('classified_failures', [])[-4:]),
        user_values=deepcopy(workflow['metadata']['action_binding_context']['user_values']),
        knowledge=brief(workflow['metadata']['action_binding_context']['validated_context'].get('business_knowledge', {})),
        working_memory=runtime.working_memory.view(run, workflow),
        remaining_budgets={k:max(0,v-(a['turns'] if k=='max_reasoning_turns' else a['revision'] if k=='max_plan_revisions'
            else a['retrieval_rounds'] if k=='max_retrieval_rounds' else run.get('usage',{}).get('workflow',{}).get(k.removeprefix('max_'),0)
            +run.get('adaptive_reasoning_usage',{}).get(k.removeprefix('max_'),0))) for k,v in a['limits'].items()},
        allowed_capabilities=deepcopy(workflow['metadata']['connected_contracts']),
        qualification='Current scoped run only. Metadata and historical conclusions are not current business facts. '
            'Only observation/correlation findings are supported; unresolved causes and missing company policy are gaps. '
            'Preserve conflicting source values. No source precedence exists without a verified rule. '
            'Assess business findings separately from pending delivery. Select an approved external follow-up only after business requirements are verified; execution completion still requires its actual receipt.')
    bounded_context(ctx, max_bytes=96000, max_tokens=96000)
    return ctx, ev, limitations


def validate_decision(decision, run, workflow, ev):
    if list(VALIDATOR.iter_errors(decision)):
        fail('ADAPTIVE_DECISION_INVALID', 'Invalid investigation assessment.')
    reject_secrets(decision)
    a = run['adaptive']; assessment = decision['assessment']
    if assessment['objective'] != a['objective']:
        fail('ADAPTIVE_GOAL_CHANGED', 'The original objective is immutable.')
    reqs = assessment['requirements']
    frozen = [dict(id=r['id'], description=r['description']) for r in reqs]
    if len({r['id'] for r in reqs}) != len(reqs) or a['requirements'] and frozen != a['requirements']:
        fail('ADAPTIVE_REQUIREMENTS_CHANGED', 'Goal requirements must retain stable unique identities.')
    valid = {k for k,v in ev.items() if v['valid']}
    for req in reqs:
        if set(req['evidence_ids']) - set(ev) or req['status'] == 'verified' and (not req['evidence_ids'] or not set(req['evidence_ids']) <= valid):
            fail('ADAPTIVE_EVIDENCE_INVALID', 'Verified requirements require actual valid scoped receipts.')
    for finding in assessment['findings']:
        if finding['evidence_id'] not in valid:
            fail('ADAPTIVE_EVIDENCE_INVALID', 'Findings require verified source evidence.')
        value = ev[finding['evidence_id']]['output']
        try:
            for segment in finding['path']:
                if isinstance(value, list) and (type(segment) is not int or segment < 0):
                    raise KeyError()
                value = value[segment]
        except (KeyError, IndexError, TypeError):
            fail('ADAPTIVE_FINDING_INVALID', 'Finding references an unavailable source location.')
        if value != finding['value']:
            fail('ADAPTIVE_FINDING_INVALID', 'Finding value differs from its cited evidence.')
    # Arithmetic is verified independently; semantic comparability and units
    # remain explicit business requirements, never invented by the calculator.
    from decimal import Decimal, InvalidOperation, localcontext
    for calculation in assessment.get('calculations',[]):
        operands=[]
        try:
            for operand in calculation['operands']:
                if operand['evidence_id'] not in valid:raise ValueError()
                value=ev[operand['evidence_id']]['output']
                for segment in operand['path']:
                    if isinstance(value,list) and (type(segment) is not int or segment<0):raise ValueError()
                    value=value[segment]
                if type(value) not in (str,int,float):raise ValueError()
                number=Decimal(str(value))
                if not number.is_finite():raise ValueError()
                operands.append(number)
            with localcontext() as arithmetic:
                arithmetic.prec=38
                result=operands[0]-operands[1] if calculation['operation']=='difference' else operands[0]/operands[1]
                if not result.is_finite() or Decimal(calculation['result'])!=result:raise ValueError()
        except (KeyError,IndexError,TypeError,ValueError,InvalidOperation,ZeroDivisionError):
            fail('ADAPTIVE_CALCULATION_INVALID','Calculated findings must match exact cited numeric source values.')
    # Rule application is conservative: unsupported model calculations/policies
    # cannot become a verified rule merely by citing a source filename.
    for rule in assessment['rule_evaluations']:
        if rule['classification'] in ('verified_policy', 'scenario_only'):
            fail('ADAPTIVE_RULE_UNVERIFIED', 'No executable authoritative policy rule was bound to this workflow.')
        if rule['classification'] == 'user_threshold':
            values = workflow['metadata']['action_binding_context']['user_values']
            if rule['source_ref'] not in values or rule['inputs']!={rule['source_ref']:values[rule['source_ref']]}:
                fail('ADAPTIVE_RULE_UNVERIFIED', 'Analytical rules must identify the exact supplied business input.')
    eligible = (all(r['status'] == 'verified' for r in reqs)
        and not any(g['blocking'] for g in assessment['gaps']) and not assessment['invalid_assumptions'])
    if assessment['completion_eligible'] != eligible:
        fail('ADAPTIVE_FALSE_COMPLETION', 'Completion eligibility conflicts with the evidence assessment.')
    choice = decision['decision']
    if (decision['proposal'] is not None) != (choice in ('retrieve_more', 'replan')):
        fail('ADAPTIVE_DECISION_INVALID', 'Only retrieval/replanning may include a proposal.')
    if bool(decision['input_requests']) != (choice == 'request_input'):
        fail('ADAPTIVE_DECISION_INVALID', 'Typed input requests are required only for input waits.')
    if choice != 'continue' and decision['action_id'] is not None:
        fail('ADAPTIVE_DECISION_INVALID', 'Only continue selects an action.')
    if choice == 'complete':
        plan = workflow['metadata']['connected_action_plan']
        if not eligible or any(run.get('action_instances', {}).get(i, {}).get('state') != 'completed' for i in plan['completion_criteria']):
            fail('ADAPTIVE_FALSE_COMPLETION', 'Tool completion does not establish objective satisfaction.')
    return frozen


def revise(service, run, workflow, proposal, reason, *, auth):
    """Compile a validated run-local revision using exact approved agent templates.

    No new agent, tool, grant, workflow approval or side effect is created. The
    original immutable reviewed workflow remains the authority for every call.
    """
    from .action_plans import compile_workflow
    from .action_bindings import validate_plan
    from .goal_inputs import bind_internal
    from planner.validation import validate_workflow
    a = run['adaptive']; old = workflow['metadata']['connected_action_plan']
    if a['revision'] >= a['limits']['max_plan_revisions']:
        fail('ADAPTIVE_REVISION_LIMIT', 'Investigation revision limit reached.')
    if not isinstance(proposal, dict) or set(proposal) != {'actions', 'completion_criteria', 'missing_inputs'} or proposal['missing_inputs']:
        fail('ADAPTIVE_REVISION_INVALID', 'Revisions require a complete bounded action proposal with resolved inputs.')
    # The original stored composition supplies the reviewed capability templates.
    doc = deepcopy(service.business_composition.get(auth, workflow['metadata']['composition_id']))
    contracts = workflow['metadata']['connected_contracts']
    actions = deepcopy(proposal['actions'])
    if not isinstance(actions, list) or not 1 <= len(actions) <= old['constraints']['max_actions']:
        fail('ADAPTIVE_REVISION_INVALID', 'Invalid revision action count.')
    previous = {x['action_id']:x for x in old['actions']}
    completed = {k for k,v in run.get('action_instances', {}).items() if v.get('state') == 'completed'}
    if any(x not in {v.get('action_id') for v in actions} for x,v in previous.items() if contracts[v['capability_id']]['side_effect'] in ('draft','write')):
        fail('ADAPTIVE_AUTHORITY_CHANGED','Revisions must preserve reviewed external actions.')
    binding_context = deepcopy(workflow['metadata']['action_binding_context'])
    for action in actions:
        cid = action.get('capability_id')
        if cid not in contracts:
            fail('ADAPTIVE_AUTHORITY_CHANGED', 'Revisions require already approved capabilities.')
        if contracts[cid]['side_effect'] in ('draft','write') and previous.get(action.get('action_id'))!=action:
            fail('ADAPTIVE_AUTHORITY_CHANGED','Revisions cannot add or alter an approved external action.')
        action['expected_output_schema'] = deepcopy(contracts[cid]['output_schema'])
        if action.get('optional') or action.get('when'):
            fail('ADAPTIVE_CONDITIONAL_REVISION','Adaptive revisions require unconditional bounded actions.')
        if action.get('action_id') in a['retired_action_ids']:
            fail('ADAPTIVE_ACTION_REUSED', 'Retired action identifiers cannot be reused.')
    # Resolve internal task/context inputs with the same Phase 1 binder.
    frozen_actions={x['action_id']:deepcopy(x) for x in actions if x.get('action_id') in completed}
    bind_internal(actions, contracts, binding_context, {}, lambda cid,c:cid.removeprefix('tool.'), run['run_id'])
    actions=[frozen_actions.get(x['action_id'],x) for x in actions]
    new = {x['action_id']:x for x in actions}
    if any(new.get(k)!=v for k,v in previous.items() if contracts[v['capability_id']]['side_effect'] in ('draft','write')):
        fail('ADAPTIVE_AUTHORITY_CHANGED','Rebinding cannot alter reviewed external actions.')
    if any(k not in new or new[k] != previous[k] for k in completed):
        fail('ADAPTIVE_COMPLETED_ACTION', 'Completed actions and bindings are immutable.')
    plan = deepcopy(old)
    plan.update(schema_version='orchestration-plan-v2', revision=a['revision'] + 1,
        previous_revision=dict(plan_id=old['plan_id'], revision=old['revision'], fingerprint=old['fingerprint'], composition_id=doc['composition_id']),
        revision_reason=reason, triggering_observations=[g['id'] for g in (a['assessment'] or {}).get('gaps', [])] or ['objective-unsatisfied'],
        actions=actions, completion_criteria=deepcopy(proposal['completion_criteria']), missing_inputs=[])
    plan['fingerprint'] = digest({k:v for k,v in plan.items() if k != 'fingerprint'})
    validate_plan(plan, contracts, binding_context, old['scope'])
    for action in actions:
        if set(action['evidence_references']) - (set(action['depends_on']) | set(binding_context['evidence'])):
            fail('ADAPTIVE_EVIDENCE_INVALID', 'Revised evidence references must identify actual dependencies or pinned evidence.')
    templates = {t['capability_id']:next(c for c in doc['configurations'] if c['assigned_task'] == t['task_id']) for t in doc['tasks']}
    configs, tasks, tools = [], [], {}
    for action in actions:
        cfg = deepcopy(templates[action['capability_id']]); cfg['assigned_task'] = action['action_id']
        approved_agent = next(x for x in workflow['agents'] if x['agent_id'] == cfg['configuration_id'])
        if any(action['budget'][k] > approved_agent['limits'][k] for k in action['budget'] if k in approved_agent['limits']):
            fail('ADAPTIVE_BUDGET_EXHAUSTED', 'Revised action exceeds its approved agent allowance.')
        configs.append(cfg)
        tasks.append(dict(task_id=action['action_id'], capability_id=action['capability_id'], depends_on=action['depends_on'],
            state='ready', condition=action['when'], side_effect=contracts[action['capability_id']]['side_effect']))
        source = next((t for t in doc['tasks'] if t['capability_id'] == action['capability_id']), None)
        if source['task_id'] in doc['selected_tools']:
            tools[action['action_id']] = deepcopy(doc['selected_tools'][source['task_id']])
    doc.update(action_plan=plan, binding_context=binding_context, tasks=tasks, configurations=configs, selected_tools=tools)
    revised = compile_workflow(doc)
    # Keep exact Registry-reviewed definitions/grants and cumulative root budget.
    for field in ('workflow_id', 'version', 'status', 'agents', 'tools', 'execution_policy', 'approval_gates'):
        revised[field] = deepcopy(workflow[field])
    revised['metadata']['adaptive_control'] = deepcopy(workflow['metadata']['adaptive_control'])
    validate_workflow(revised)
    # Rebuild edges by stable endpoints: compiler edge numbers can change.
    states = {}
    for edge in revised['edges']:
        if edge['source'].startswith('approve_') and edge['source'][8:] in completed:
            states[edge['edge_id']]='selected' if edge.get('outcome')=='approved' else 'skipped'
        elif edge['source'] in completed or edge['source'] == 'objective_received' and run['node_states'].get('objective_received') == 'completed':
            if edge.get('outcome') is not None:
                fail('ADAPTIVE_CONDITIONAL_REVISION', 'Conditional completed paths require explicit review.')
            states[edge['edge_id']] = 'selected'
    a['retired_action_ids'] = sorted(set(a['retired_action_ids']) | (set(previous) - set(new)))
    a['revisions'].append(dict(revision=plan['revision'], reason=reason, fingerprint=plan['fingerprint'],
        previous_fingerprint=old['fingerprint'], completed_actions=sorted(completed)))
    a['revision'] = plan['revision']
    a['revisions'][-1]['prior_node_states']=deepcopy(run['node_states'])
    run['node_states']={k:v for k,v in run['node_states'].items() if k in completed or k=='objective_received' or k.startswith('approve_') and k[8:] in completed}
    run.update(adaptive_workflow=revised, adaptive_workflow_digest=digest(revised), edge_states=states)
    return revised


def drive(runner, run_id, auth, raw_advance):
    try:
        return _drive(runner, run_id, auth, raw_advance)
    except (RuntimeFailure,ApiFailure) as exc:
        if isinstance(exc,RuntimeFailure) and not (exc.code.startswith('ADAPTIVE_') or exc.code == 'WORKING_CONTEXT_LIMIT'):
            raise
        runtime = runner.runtime
        with runtime.store.transaction() as db:
            run = runtime.load(db, run_id, auth, 'workflow.execute')
            if run['subject_id'] != auth['subject']['subject_id']:
                raise
            if run.get('adaptive') and run['status'] in ('queued', 'running'):
                block(runtime, db, run, exc.code)
            return runtime.public(run)


def finalize_verified_actions(runtime, db, run, workflow, auth):
    """Finish an already verified objective using durable execution receipts.

    Never invent a new assessment or retry a connector. The exact last accepted
    assessment is revalidated against current source authority and stored output.
    """
    a = run['adaptive']
    assessment = a.get('assessment')
    plan = workflow['metadata']['connected_action_plan']
    required = plan['completion_criteria']
    instances = run.get('action_instances', {})
    if (not assessment or not assessment['completion_eligible'] or not required
            or any(instances.get(aid, {}).get('state') != 'completed' for aid in required)):
        return False
    contracts = workflow['metadata']['connected_contracts']
    for action in plan['actions']:
        item = instances.get(action['action_id'], {})
        if item.get('state') != 'completed':
            continue
        if item.get('output_fingerprint') != digest(item.get('output')):
            fail('ADAPTIVE_RECEIPT_INVALID', 'Completed action output integrity check failed.')
        if contracts[action['capability_id']]['side_effect'] in ('read', 'draft', 'write') and not item.get('verified_receipt'):
            fail('ADAPTIVE_RECEIPT_INVALID', 'Required connector completion needs a verified receipt.')
    ev, limitations = evidence(runtime, db, run, workflow, auth)
    decision = dict(decision='complete', rationale='Verified business requirements and all required actions are complete.',
                    action_id=None, proposal=None, input_requests=[], assessment=deepcopy(assessment))
    validate_decision(decision, run, workflow, ev)
    a['deterministic_limitations'] = limitations
    if a['status'] != 'completed':
        a.update(status='completed')
        a.pop('execution_permission', None)
        a['decisions'].append(dict(decision='complete', rationale=decision['rationale'], revision=a['revision'],
            evidence_ids=sorted(ev), completion_basis='verified_action_receipts'))
        runtime.event(db, run, 'adaptive.completed', dict(completion_basis='verified_action_receipts',
            required_actions=list(required), revision=a['revision']))
    run.pop('error_code', None)
    return True


def _drive(runner, run_id, auth, raw_advance):
    runtime = runner.runtime; service = runtime.workflows
    for _ in range(4):  # One worker tick is bounded; the durable worker continues.
        token = uuid4().hex
        with runtime.store.transaction() as db:
            run = runtime.load(db, run_id, auth, 'workflow.execute')
            if run['subject_id'] != auth['subject']['subject_id']:
                fail('SUBJECT_MISMATCH', 'The execution subject must match.')
            approved, _ = runtime.revision(db, run['workflow_id'], run['workflow_version'], auth, run.get('release_bound', False))
            initialize(run, approved)
            workflow = effective(run, approved); a = run['adaptive']
            if run['status'] not in ('queued', 'running'):
                return runtime.public(run)
            automation=getattr(service,'automation',None)
            if automation and automation.suspended(db,auth,run):return runtime.public(run)
            if automation and run.get('automation_reference'):
                try:automation.guard_run(db,auth,run,workflow)
                except RuntimeFailure as error:
                    block(runtime,db,run,error.code);return runtime.public(run)
            if run.get('lease_until', 0) > runtime.clock() or run.get('available_at', 0) > runtime.clock():
                return runtime.public(run)
            if a.get('claim'):
                if a['claim']['until'] > runtime.clock():
                    return runtime.public(run)
                # A provider call has no external effect, but its reserved usage is
                # retained. Never silently replay an unknown paid request.
                block(runtime, db, run, 'ADAPTIVE_UNKNOWN_EVALUATION')
                return runtime.public(run)
            if a.get('pending_wait'):
                runtime.save(db, run)
                return runtime.public(run)
            terminal = finalize_verified_actions(runtime, db, run, workflow, auth)
            if not terminal and (runtime.clock() >= a['deadline'] or a['turns'] >= a['limits']['max_reasoning_turns']):
                block(runtime, db, run, 'ADAPTIVE_BUDGET_EXHAUSTED')
                return runtime.public(run)
            # Resume an authorized in-progress action after read-only durable wait.
            permission = a.get('execution_permission')
            if terminal or permission and run.get('action_instances', {}).get(permission, {}).get('state') != 'completed':
                runtime.save(db, run)
                resume = True
            else:
                resume = False
                a.pop('execution_permission', None)
                if not callable(getattr(service.planner.provider,'evaluate_actions',None)):
                    block(runtime,db,run,'ADAPTIVE_PROVIDER_UNAVAILABLE')
                    return runtime.public(run)
                ctx, ev, limitations = context(runtime, db, run, workflow, auth)
                a['deterministic_limitations']=deepcopy(limitations)
                reservation = len(json.dumps(dict(schema=CONTRACT, context=ctx)).encode()) + a['limits']['evaluator_output_tokens']
                from runtime.adaptive_control import reserve
                reserve(run, workflow, dict(tokens=reservation, llm_calls=1))
                if controls:=getattr(runtime,'resource_controls',None):
                    from .resource_limits import CapacityDeferred
                    try:controls.reserve_provider(db,run['workspace_id'],workflow['agents'][0]['model']['provider'],runtime.clock())
                    except CapacityDeferred as exc:
                        try:controls.defer(runtime,db,run,exc)
                        except RuntimeFailure as failure:block(runtime,db,run,failure.code)
                        return runtime.public(run)
                a['turns'] += 1
                run['adaptive_reasoning_usage']['tokens'] += reservation
                run['adaptive_reasoning_usage']['llm_calls'] += 1
                a['claim'] = dict(token=token, until=runtime.clock() + 360)
                runtime.event(db, run, 'adaptive.evaluating', dict(revision=a['revision'], turn=a['turns']))
                runtime.save(db, run)
        if resume:
            outcome = raw_advance()
            if outcome['status'] not in ('running', 'queued'):
                return outcome
            continue
        try:
            decision = service.planner.provider.evaluate_actions(ctx, max_output_tokens=run['adaptive']['limits']['evaluator_output_tokens'])
            with runtime.store.transaction() as db:
                current = runtime.load(db, run_id, auth, 'workflow.execute')
                if current['status'] not in ('queued', 'running') or current['adaptive'].get('claim', {}).get('token') != token:
                    return runtime.public(current)
                approved, _ = runtime.revision(db, current['workflow_id'], current['workflow_version'], auth, current.get('release_bound', False))
                workflow = effective(current, approved)
                if current['adaptive']['revision'] != run['adaptive']['revision']:
                    fail('ADAPTIVE_STALE_REVISION', 'Concurrent revision changed.')
                a = current['adaptive']
                ev,_=evidence(runtime,db,current,workflow,auth)
                a['requirements'] = validate_decision(decision, current, workflow, ev)
                a['assessment'] = deepcopy(decision['assessment'])
                a.pop('claim', None)
                choice = decision['decision']
                progress = digest([sorted(ev), [(r['id'],r['status']) for r in decision['assessment']['requirements']],
                    sorted((key,item.get('output_fingerprint')) for key,item in current.get('action_instances',{}).items() if item.get('state')=='completed'),
                    [(item.get('affected_task'),item.get('error_code')) for item in current.get('classified_failures',[])]])
                a['no_progress'] = a['no_progress'] + 1 if a.get('progress') == progress else 0
                a['progress'] = progress
                a['decisions'].append(dict(decision=choice, rationale=decision['rationale'], revision=a['revision'],
                    evidence_ids=sorted(ev), context_sha256=digest(ctx)))
                runtime.event(db, current, 'adaptive.decision', dict(decision=choice, revision=a['revision'],
                    completion_eligible=decision['assessment']['completion_eligible']))
                if choice in ('replan', 'retrieve_more'):
                    if a['no_progress'] >= a['limits']['max_no_progress']:
                        fail('ADAPTIVE_NO_PROGRESS', 'Repeated decisions did not add evidence or satisfy a requirement.')
                    if choice == 'retrieve_more':
                        a['retrieval_rounds'] += 1
                        if a['retrieval_rounds'] > a['limits']['max_retrieval_rounds']:
                            fail('ADAPTIVE_RETRIEVAL_LIMIT', 'Evidence retrieval limit reached.')
                    # Pass live auth explicitly; never store executable roles.
                    workflow = revise(service, current, workflow, decision['proposal'], decision['rationale'], auth=auth)
                    runtime.event(db, current, 'adaptive.replanned', dict(revision=a['revision']))
                elif choice == 'continue':
                    aid = decision['action_id']
                    actions = {x['action_id']:x for x in workflow['metadata']['connected_action_plan']['actions']}
                    done = {k for k,v in current.get('action_instances', {}).items() if v.get('state') == 'completed'}
                    if aid not in actions or aid in done or not set(actions[aid]['depends_on']) <= done:
                        fail('ADAPTIVE_ACTION_NOT_READY', 'Continue must select a ready unfinished action.')
                    if current['node_states'].get(aid) in ('failed','blocked'):
                        fail('ADAPTIVE_ACTION_NOT_READY','Rejected actions require a validated replacement with a fresh action ID.')
                    capability=workflow['metadata']['connected_contracts'][actions[aid]['capability_id']]
                    if capability['side_effect'] in ('draft','write') and not decision['assessment']['completion_eligible']:
                        fail('ADAPTIVE_EVIDENCE_INCOMPLETE','External follow-up requires verified business findings before approval.')
                    a['execution_permission'] = aid
                    current['adaptive_next_action'] = aid
                elif choice == 'request_input':
                    check_inputs(decision['input_requests'])
                    a['pending_wait'] = dict(wait_id='input_' + uuid4().hex, requests=decision['input_requests'])
                    a['status'] = 'waiting_for_input'
                    runtime.event(db, current, 'adaptive.waiting_for_input', dict(wait_id=a['pending_wait']['wait_id']))
                elif choice == 'blocked':
                    block(runtime, db, current, 'ADAPTIVE_OBJECTIVE_BLOCKED')
                    return runtime.public(current)
                elif choice == 'complete':
                    a['status'] = 'completed'
                    current.pop('error_code',None)
                runtime.save(db, current)
            if choice in ('continue', 'complete'):
                outcome = raw_advance()
                if outcome['status'] not in ('running', 'queued'):
                    return outcome
            elif choice == 'request_input':
                return runtime.public(current)
        except Exception as exc:
            with runtime.store.transaction() as db:
                current = runtime.load(db, run_id, auth, 'workflow.execute')
                if current['status'] in ('queued', 'running'):
                    if current['adaptive'].get('claim',{}).get('token') not in (None,token):
                        return runtime.public(current)
                    current['adaptive'].pop('claim', None)
                    diagnostics = dict(exception_type=type(exc).__name__)
                    stage = getattr(exc, 'details', {}).get('validation_stage')
                    if stage in ('response','incomplete','transport','encoded_value','canonical'):
                        diagnostics['validation_stage'] = stage
                    runtime.event(db,current,'adaptive.evaluation_failed',diagnostics)
                    # Explicit provider rejection is safe to retry. Unknown
                    # outcomes remain blocked; their usage reservation is kept.
                    if getattr(exc,'status_code',None) in (429,503):
                        failures=current['adaptive'].get('provider_failures',0)+1
                        current['adaptive']['provider_failures']=failures
                        if failures<=2:
                            current['available_at']=runtime.clock()+2**failures
                            runtime.event(db,current,'adaptive.retry_scheduled',dict(attempt=failures,code='PROVIDER_TEMPORARILY_UNAVAILABLE'))
                            runtime.save(db,current)
                            return runtime.public(current)
                    block(runtime, db, current, getattr(exc, 'code', 'ADAPTIVE_EVALUATION_FAILED'))
                return runtime.public(current)
    with runtime.store.transaction(write=False) as db:
        return runtime.public(runtime.load(db, run_id, auth))


def block(runtime, db, run, code):
    if not isinstance(code,str) or not re.fullmatch(r'[A-Z][A-Z0-9_]{0,127}',code):code='ADAPTIVE_EVALUATION_FAILED'
    run['error_code']=code
    run['adaptive'].update(status='blocked', blocker=code)
    if run['status'] == 'queued':
        runtime.transition(db, run, 'running')
    runtime.event(db, run, 'adaptive.blocked', dict(code=code))
    runtime.transition(db, run, 'blocked')


def check_inputs(requests):
    keys = set()
    for item in requests:
        schema = item['schema']
        if item['key'] in keys or len(json.dumps(schema).encode()) > 4000 or '$ref' in json.dumps(schema):
            fail('ADAPTIVE_INPUT_INVALID', 'Input requests require unique bounded self-contained schemas.')
        Draft202012Validator.check_schema(schema)
        if set(schema)-{'type','minimum','maximum','minLength','maxLength','enum','description'}:
            fail('ADAPTIVE_INPUT_INVALID','Use bounded scalar business input constraints.')
        if schema.get('type') not in ('string', 'number', 'integer', 'boolean'):
            fail('ADAPTIVE_INPUT_INVALID', 'Business input must be a scalar value.')
        keys.add(item['key'])


def supply(runtime, auth, run_id, body):
    reject_secrets(body)
    if not isinstance(body, dict) or set(body) != {'wait_id', 'values'} or not isinstance(body['values'], dict) or len(json.dumps(body).encode()) > 8000:
        fail('ADAPTIVE_INPUT_INVALID', 'Supply the current wait ID and bounded business values.')
    with runtime.store.transaction() as db:
        run = runtime.load(db, run_id, auth, 'workflow.execute')
        if run['subject_id'] != auth['subject']['subject_id']:
            fail('SUBJECT_MISMATCH', 'Only the execution owner may supply business input.')
        a = run.get('adaptive', {}); wait = a.get('pending_wait')
        if not wait or wait['wait_id'] != body['wait_id'] or run['status'] not in ('queued', 'running'):
            fail('ADAPTIVE_WAIT_STALE', 'The input wait is no longer active.')
        if set(body['values']) != {r['key'] for r in wait['requests']}:
            fail('ADAPTIVE_INPUT_INVALID', 'Supply exactly the requested business values.')
        for item in wait['requests']:
            if list(Draft202012Validator(item['schema'], format_checker=FormatChecker()).iter_errors(body['values'][item['key']])):
                fail('ADAPTIVE_INPUT_INVALID', 'Business input violates the requested schema.')
        approved, _ = runtime.revision(db, run['workflow_id'], run['workflow_version'], auth, run.get('release_bound', False))
        workflow = deepcopy(effective(run, approved))
        existing=workflow['metadata']['action_binding_context']['user_values']
        if set(body['values']) & set(existing):
            fail('ADAPTIVE_INPUT_INVALID','Business continuation cannot overwrite existing execution inputs.')
        workflow['metadata']['action_binding_context']['user_values'].update(deepcopy(body['values']))
        run.update(adaptive_workflow=workflow, adaptive_workflow_digest=digest(workflow))
        a.update(pending_wait=None, status='active')
        runtime.event(db, run, 'adaptive.input_supplied', dict(wait_id=wait['wait_id'], keys=sorted(body['values'])))
        runtime.save(db, run)
        return runtime.public(run)
