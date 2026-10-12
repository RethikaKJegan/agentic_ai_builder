"""Dynamic runtime integration, including real bounded CrewAI with offline transport."""
from copy import deepcopy
import json
from threading import Event
from tests.test_runtime import RuntimeFixture, ROOT
from registry import RegistryService, WorkspacePolicy
from workflow_api.registry_adapter import RegistryAdapter
from workflow_api.service import WorkflowService
from runtime import RuntimeService
from runtime.graph import GraphRunner
from runtime.crew import CrewExecutor
from runtime.model import BoundedLLM


class DynamicDelegationTests(RuntimeFixture):
    def test_accounted_turns_use_remaining_tokens_and_settle_actual_usage(self):
        caps, turns = [], []
        def factory(definition):
            def provider(messages, cap, timeout):
                if definition['agent_id'] == 'master_agent':
                    caps.append(cap)
                    turns.append(1)
                    if len(turns) < 3:
                        child = 'research_agent' if len(turns) == 1 else 'analysis_agent'
                        output = {'action': 'delegate', 'reason': 'Check another source.', 'tasks': [
                            {'agent_id': child, 'inputs': {'task': 'check'}, 'reason': 'Required check.'}]}
                    else:
                        output = {'action': 'finish', 'reason': 'Combine both sources.', 'output': {'summary': 'Verified.'}}
                else:
                    output = {'verified': True}
                return json.dumps(output), 1500, 1000
            return BoundedLLM(definition, provider, lambda messages: 2000, 0, 0)
        result, events = self.run_case(executor=CrewExecutor(self.workflows.registry_adapter, factory))
        self.assertEqual(result['status'], 'completed', json.dumps(events))
        self.assertEqual(caps, [14000, 11500, 9000])
        with self.store.transaction() as db:
            stored = self.runtime.load(db, result['run_id'], self.auth)
        self.assertEqual(stored['usage']['master_agent']['tokens'], 7500)
        self.assertEqual(stored['usage']['workflow']['tokens'], 12500)
        self.assertEqual(len([e for e in events if e['event_type'] == 'budget.settled']), 5)

    def test_unconfirmed_provider_failure_keeps_full_reservation(self):
        def factory(definition):
            def provider(*args):
                raise RuntimeFailure('MODEL_OUTPUT_TRUNCATED', 'The provider truncated its answer.')
            return BoundedLLM(definition, provider, lambda messages: 2000, 0, 0)
        from runtime.service import RuntimeFailure
        result, events = self.run_case(executor=CrewExecutor(self.workflows.registry_adapter, factory))
        self.assertEqual(result['status'], 'failed')
        with self.store.transaction() as db:
            stored = self.runtime.load(db, result['run_id'], self.auth)
        self.assertEqual(stored['error_code'], 'MODEL_OUTPUT_TRUNCATED')
        self.assertEqual(stored['usage']['master_agent']['tokens'], 16000)
        self.assertFalse(any(e['event_type'] == 'budget.settled' for e in events))

    def test_master_continues_while_child_runs_and_joins_before_final_output(self):
        started, release, finished = Event(), Event(), Event()
        contexts = []

        def choose(context):
            contexts.append(deepcopy(context))
            if len(contexts) == 1:
                return {'action': 'delegate', 'reason': 'This item requires specialist work.',
                        'continuation': {'remaining_items': ['other item']},
                        'tasks': [{'agent_id': 'research_agent', 'inputs': {'task': 'check item'}, 'reason': 'Check the triggered item.'}]}
            if len(contexts) == 2:
                self.assertTrue(started.wait(5), 'Child never started')
                self.assertFalse(finished.is_set(), 'Child finished before independent master work')
                self.assertEqual(context['continuation']['remaining_items'], ['other item'])
                self.assertEqual(len(context['pending_tasks']), 1)
                return {'action': 'continue', 'reason': 'Processed the independent item.',
                        'continuation': {'summary': 'Other item summarized'}}
            if len(contexts) == 3:
                release.set()
                return {'action': 'finish', 'reason': 'Attempted early synthesis.', 'output': {'incomplete': True}}
            self.assertTrue(finished.is_set())
            self.assertFalse(context['pending_tasks'])
            return {'action': 'finish', 'reason': 'Combine independent work and checked facts.',
                    'output': {'summary': context['continuation']['summary'], 'verified': context['results'][0]['result']}}

        executor = self.executor(choose)
        def child(agent, inputs, invocation_id):
            started.set()
            if not release.wait(5):
                raise RuntimeError('Master failed to continue')
            finished.set()
            return {'facts': 'Checked fact'}
        executor.invoke = child
        result, events = self.run_case(executor=executor)
        self.assertEqual(result['status'], 'completed', json.dumps(events))
        decisions = [e['details'] for e in events if e['event_type'] == 'agent.decision']
        self.assertEqual([d['action'] for d in decisions], ['delegate', 'continue', 'finish', 'finish'])
        self.assertEqual(decisions[-1]['output'], {'action': 'finish',
            'reason': 'Combine independent work and checked facts.',
            'output': {'summary': 'Other item summarized', 'verified': {'facts': 'Checked fact'}}})
        handoffs = [e['details'] for e in events if e['event_type'] == 'node.handoff' and e['details']['transfer_kind'].startswith('delegated_')]
        self.assertEqual(handoffs[0]['source_invocation_id'], decisions[0]['invocation_id'])
        self.assertEqual(handoffs[1]['target_invocation_id'], decisions[0]['invocation_id'])

    def test_children_overlap_and_wait_collects_both_results(self):
        started = {'research_agent': Event(), 'analysis_agent': Event()}
        contexts = []
        def choose(context):
            contexts.append(context)
            if len(contexts) == 1:
                return {'action': 'delegate', 'reason': 'Two independent tasks.', 'continuation': {},
                    'tasks': [{'agent_id': agent_id, 'inputs': {'task': agent_id}, 'reason': 'Independent task.'}
                              for agent_id in started]}
            if len(contexts) == 2:
                return {'action': 'wait', 'reason': 'Join the required facts.'}
            return {'action': 'finish', 'reason': 'Both results included.',
                    'output': {'results': context['results']}}
        executor = self.executor(choose)
        def child(agent, inputs, invocation_id):
            started[agent['agent_id']].set()
            other = 'analysis_agent' if agent['agent_id'] == 'research_agent' else 'research_agent'
            if not started[other].wait(5):
                raise RuntimeError('Children did not overlap')
            return {'facts': inputs['task']}
        executor.invoke = child
        result, events = self.run_case(executor=executor)
        self.assertEqual(result['status'], 'completed', json.dumps(events))
        self.assertEqual(len(contexts[-1]['results']), 2)

    def test_pending_child_failure_prevents_final_synthesis(self):
        contexts = []
        def choose(context):
            contexts.append(context)
            if len(contexts) == 1:
                return {'action': 'delegate', 'reason': 'Required check.', 'continuation': {},
                    'tasks': [{'agent_id': 'research_agent', 'inputs': {'task': 'check'}, 'reason': 'Required.'}]}
            return {'action': 'finish', 'reason': 'Cannot publish without check.', 'output': {'done': True}}
        executor = self.executor(choose)
        executor.invoke = lambda *args: (_ for _ in ()).throw(RuntimeError('Check failed'))
        result, events = self.run_case(executor=executor)
        self.assertEqual(result['status'], 'failed')
        self.assertFalse(any(e['event_type'] == 'node.completed' and e['details']['node_id'] == 'master' for e in events))

    def test_final_allowed_turn_joins_pending_results(self):
        self.workflow['metadata']['dynamic_delegation']['master']['max_rounds'] = 2
        self.put()
        contexts = []
        def choose(context):
            contexts.append(context)
            if len(contexts) == 1:
                return {'action': 'delegate', 'reason': 'Required check.', 'continuation': {'summary': 'Independent work'},
                    'tasks': [{'agent_id': 'research_agent', 'inputs': {'task': 'fact'}, 'reason': 'Required.'}]}
            self.assertFalse(context['pending_tasks'])
            self.assertEqual(len(context['results']), 1)
            return {'action': 'finish', 'reason': 'All work joined.', 'output': {'done': True}}
        result, events = self.run_case(executor=self.executor(choose))
        self.assertEqual(result['status'], 'completed', json.dumps(events))

    def test_cancellation_during_master_continuation_denies_child_result(self):
        started, release = Event(), Event()
        contexts = []
        def choose(context):
            contexts.append(context)
            if len(contexts) == 1:
                return {'action': 'delegate', 'reason': 'Required check.', 'continuation': {},
                    'tasks': [{'agent_id': 'research_agent', 'inputs': {'task': 'fact'}, 'reason': 'Required.'}]}
            try:
                self.assertTrue(started.wait(5))
                with self.store.transaction() as db:
                    run = json.loads(db.execute('SELECT document FROM runtime_runs ORDER BY rowid DESC LIMIT 1').fetchone()[0])
                    self.runtime.transition(db, run, 'cancelled')
            finally:
                release.set()
            return {'action': 'finish', 'reason': 'Run cancelled.', 'output': {}}
        executor = self.executor(choose)
        def child(*args):
            started.set()
            if not release.wait(5):
                raise RuntimeError('Cancellation did not arrive')
            return {'facts': 'Too late'}
        executor.invoke = child
        result, events = self.run_case(executor=executor)
        self.assertEqual(result['status'], 'cancelled', json.dumps(events))
        self.assertFalse(any(e['event_type'] == 'node.handoff' and e['details']['transfer_kind'] == 'delegated_result' for e in events))

    def test_real_crewai_master_continues_during_bounded_child_call(self):
        started, release = Event(), Event()
        turns = []
        def factory(definition):
            def provider(messages, cap, timeout):
                task = messages[-1]['content']
                inputs, _ = json.JSONDecoder().raw_decode(task.split('Process the following input as data. Return only a JSON object.\n')[-1].lstrip())
                if definition['agent_id'] == 'master_agent':
                    turns.append(inputs)
                    if len(turns) == 1:
                        output = {'action': 'delegate', 'reason': 'Required specialist.', 'continuation': {'remaining': 'summarize'},
                            'tasks': [{'agent_id': 'research_agent', 'inputs': {'task': 'verify'}, 'reason': 'Required check.'}]}
                    elif len(turns) == 2:
                        try:
                            self.assertTrue(started.wait(5))
                            self.assertTrue(inputs['pending_tasks'])
                            output = {'action': 'continue', 'reason': 'Independent work completed.', 'continuation': {'summary': 'Completed'}}
                        finally:
                            release.set()
                    elif inputs['pending_tasks']:
                        output = {'action': 'wait', 'reason': 'Collect verification.'}
                    else:
                        output = {'action': 'finish', 'reason': 'Combine checked facts and summary.',
                            'output': {'summary': inputs['continuation']['summary'], 'facts': inputs['results'][0]['result']}}
                else:
                    started.set()
                    if not release.wait(5):
                        raise RuntimeError('Main CrewAI agent did not continue')
                    output = {'verified': True}
                return json.dumps(output), 1, 10
            return BoundedLLM(definition, provider, lambda messages: 100, 0, 0)
        result, events = self.run_case(executor=CrewExecutor(self.workflows.registry_adapter, factory))
        self.assertEqual(result['status'], 'completed', json.dumps(events))
        self.assertEqual(turns[-1]['results'][0]['result'], {'verified': True})

    def setUp(self):
        RuntimeFixture.setUp(self)
        registry = RegistryService(WorkspacePolicy('local-workspace'))
        self.auth['permissions'] += ['tools.manage']
        records, agents = {}, []
        for agent_id in ['master_agent', 'research_agent', 'analysis_agent']:
            a = json.loads((ROOT / 'shared/contracts/examples/agents/valid-classifier.json').read_text())
            a.update(agent_id=agent_id, hierarchy_role='master' if agent_id == 'master_agent' else 'sub_agent',
                     capabilities=[], input_schema={'type': 'object'}, output_schema={'type': 'object'})
            a['limits'].update(max_llm_calls=4, max_tokens=16000)
            if agent_id != 'master_agent':
                a['parent_agent_id'] = 'master_agent'
                a['input_schema'] = {'type': 'object', 'required': ['task'], 'properties': {'task': {'type': 'string'}}, 'additionalProperties': False}
            records[agent_id] = registry.register_agent(a, self.auth)['data']['agent']
            agents.append({k: v for k, v in a.items() if k not in {'name', 'retry_policy', 'guardrails'}})
        self.workflows = WorkflowService(self.store, registry_adapter=RegistryAdapter(registry, records))
        self.runtime = RuntimeService(self.workflows)
        self.workflow['agents'] = agents
        self.workflow['conditions'] = []
        self.workflow['approval_gates'] = []
        self.workflow['tools'] = []
        self.workflow['execution_policy']['limits'].update(max_llm_calls=12, max_tokens=48000)
        self.workflow['metadata']['dynamic_delegation'] = {'master': {'max_rounds': 4, 'max_tasks': 6}}
        self.workflow['nodes'] = [dict(node_id='start', kind='trigger', label='Start'),
            dict(node_id='master', kind='agent', label='Master', agent_id='master_agent'),
            dict(node_id='finish', kind='output', label='Finish', configuration={'input_mapping': {'result': 'outputs.master'}})]
        self.workflow['edges'] = [dict(edge_id='a', source='start', target='master'), dict(edge_id='b', source='master', target='finish')]
        self.put()
        self.called, self.contexts = [], []

    def decision(self, context):
        self.contexts.append(deepcopy(context))
        if context['results']:
            return {'action': 'finish', 'reason': 'The specialist returned the requested facts.', 'output': {'answer': context['results'][-1]['result']}}
        selected = 'research_agent' if 'research' in context['request']['request_text'] else 'analysis_agent'
        return {'action': 'delegate', 'reason': 'Choose the specialist matching the request.',
                'tasks': [{'agent_id': selected, 'inputs': {'task': context['request']['request_text']}, 'reason': 'This specialist handles the requested task.'}]}

    def executor(self, choose=None):
        owner = self
        class Offline:
            retry_safe = False
            external_write = False
            @staticmethod
            def reservation(agent): return {'llm_calls': 1, 'tokens': 10}
            def invoke_decision(self, agent, inputs, invocation_id, schema):
                return (choose or owner.decision)(inputs)
            def invoke(self, agent, inputs, invocation_id):
                owner.called.append((agent['agent_id'], inputs, invocation_id))
                return {'facts': inputs['task']}
        return Offline()

    def run_case(self, text='research the issue', executor=None, key='dynamic_test_1234'):
        request = self.request(inputs={'request_text': text})
        request['idempotency_key'] = key
        run_id = self.runtime.create_run(request, self.auth)['run_id']
        result = GraphRunner(self.runtime, agents=executor or self.executor()).advance(run_id, self.auth)
        return result, self.runtime.events(run_id, self.auth)['items']

    def test_input_changes_selected_specialist_and_records_task_result_uuids(self):
        first, events = self.run_case()
        second, other = self.run_case('analyze the issue', key='dynamic_test_5678')
        self.assertEqual((first['status'], second['status']), ('completed', 'completed'))
        self.assertEqual([c[0] for c in self.called], ['research_agent', 'analysis_agent'])
        spawned = [e for e in events + other if e['event_type'] == 'agent.spawned']
        self.assertEqual(len({e['details']['invocation_id'] for e in spawned}), 2)
        for timeline in [events, other]:
            handoffs = [e['details'] for e in timeline if e['event_type'] == 'node.handoff' and e['details']['transfer_kind'].startswith('delegated_')]
            self.assertEqual([h['transfer_kind'] for h in handoffs], ['delegated_task', 'delegated_result'])
            self.assertEqual(handoffs[0]['target_invocation_id'], handoffs[1]['source_invocation_id'])
        self.assertEqual(self.contexts[1]['results'][0]['result'], {'facts': 'research the issue'})

    def test_master_can_spawn_same_specialist_again_after_receiving_result(self):
        def choose(context):
            if len(context['results']) == 2:
                return {'action': 'finish', 'reason': 'Both tasks completed.', 'output': {'done': True}}
            return {'action': 'delegate', 'reason': 'More evidence needed.', 'tasks': [{'agent_id': 'research_agent', 'inputs': {'task': str(len(context['results']))}, 'reason': 'Follow up on prior evidence.'}]}
        result, events = self.run_case(executor=self.executor(choose))
        self.assertEqual(result['status'], 'completed')
        self.assertEqual(len(self.called), 2)
        self.assertNotEqual(self.called[0][2], self.called[1][2])
        self.assertEqual(len([e for e in events if e['event_type'] == 'agent.decision']), 3)

    def test_invalid_batch_never_starts_a_child(self):
        for invalid in [{'agent_id': 'unknown_agent', 'inputs': {'task': 'x'}, 'reason': 'x'},
                        {'agent_id': 'analysis_agent', 'inputs': {}, 'reason': 'x'}]:
            choose = lambda context: {'action': 'delegate', 'reason': 'x', 'tasks': [
                {'agent_id': 'research_agent', 'inputs': {'task': 'x'}, 'reason': 'x'}, invalid]}
            result, events = self.run_case(executor=self.executor(choose), key='invalid_' + invalid['agent_id'])
            self.assertEqual(result['status'], 'failed')
            self.assertFalse(self.called)
            self.assertFalse(any(e['event_type'] == 'agent.spawned' for e in events))

    def test_task_and_round_limits_stop_further_spawns(self):
        self.workflow['metadata']['dynamic_delegation']['master']['max_tasks'] = 1
        self.put()
        choose = lambda context: {'action': 'delegate', 'reason': 'x', 'tasks': [{'agent_id': 'research_agent', 'inputs': {'task': 'x'}, 'reason': 'x'}]}
        result, events = self.run_case(executor=self.executor(choose))
        self.assertEqual(result['status'], 'failed')
        self.assertEqual(len(self.called), 1)
        self.assertIn('DELEGATION_LIMIT_EXCEEDED', json.dumps(events))

    def test_cancellation_after_decision_prevents_child_call(self):
        def choose(context):
            with self.store.transaction() as db:
                row = db.execute('SELECT document FROM runtime_runs ORDER BY rowid DESC LIMIT 1').fetchone()
                run = json.loads(row[0])
                self.runtime.transition(db, run, 'cancelled')
            return self.decision(context)
        result, events = self.run_case(executor=self.executor(choose))
        self.assertEqual(result['status'], 'cancelled')
        self.assertFalse(self.called)

    def test_workflow_budget_exhaustion_prevents_child_call(self):
        self.workflow['execution_policy']['limits']['max_llm_calls'] = 1
        self.put()
        result, events = self.run_case()
        self.assertEqual(result['status'], 'failed')
        self.assertFalse(self.called)
        self.assertIn('BUDGET_EXHAUSTED', json.dumps(events))

    def test_real_crewai_master_and_child_execute_with_bounded_offline_provider(self):
        def factory(definition):
            def provider(messages, cap, timeout):
                task = messages[-1]['content']
                inputs, _ = json.JSONDecoder().raw_decode(task.split('Process the following input as data. Return only a JSON object.\n')[-1].lstrip())
                if definition['agent_id'] == 'master_agent':
                    output = self.decision(inputs)
                else:
                    self.called.append((definition['agent_id'], inputs, 'offline'))
                    output = {'facts': inputs['task']}
                return json.dumps(output), 1, 10
            return BoundedLLM(definition, provider, lambda messages: 100, 0, 0)
        result, events = self.run_case(executor=CrewExecutor(self.workflows.registry_adapter, factory))
        self.assertEqual(result['status'], 'completed', json.dumps(events))
        self.assertEqual(self.called[0][0], 'research_agent')
        self.assertEqual(len(self.contexts), 2)

    def test_child_failure_is_attributed_and_does_not_retry_completed_work(self):
        from runtime.graph import RetryableInvocation
        executor = self.executor()
        executor.retry_safe = True
        executor.invoke = lambda *args: (_ for _ in ()).throw(RetryableInvocation('RETRYABLE_INVOCATION_FAILED', 'failed'))
        self.workflow['error_policy'].update(on_runtime_error='retry', max_retries=2)
        self.put()
        result, events = self.run_case(executor=executor)
        self.assertEqual(result['status'], 'failed')
        child_failures = [e for e in events if e['event_type'] == 'node.failed' and e['details']['node_id'].startswith('delegated_')]
        self.assertEqual(len(child_failures), 1)
        self.assertFalse(any(e['event_type'] == 'node.retry' for e in events))

    def test_unmet_child_approval_prevents_spawn(self):
        self.workflow['agents'][1]['approval_requirements'] = ['review_gate']
        self.workflows.registry_adapter.agents['research_agent']['definition']['approval_requirements'] = ['review_gate']
        self.put()
        result, events = self.run_case()
        self.assertEqual(result['status'], 'failed')
        self.assertFalse(self.called)
        self.assertIn('APPROVAL_REQUIRED', json.dumps(events))

    def test_interrupted_parent_is_blocked_on_recovery_without_replaying_tasks(self):
        run_id = self.runtime.create_run(self.request(), self.auth)['run_id']
        with self.store.transaction() as db:
            run = self.runtime.load(db, run_id, self.auth)
            self.runtime.transition(db, run, 'running')
            run['node_states']['master'] = 'executing'
            run['current_node_id'] = 'master'
            self.runtime.save(db, run)
        result = GraphRunner(self.runtime, agents=self.executor()).advance(run_id, self.auth)
        self.assertEqual(result['status'], 'blocked')
        self.assertFalse(self.called)
        self.assertIn('UNKNOWN_INVOCATION_RESULT', json.dumps(self.runtime.events(run_id, self.auth)))

    def test_master_may_finish_without_starting_any_child(self):
        executor = self.executor(lambda context: {'action': 'finish', 'reason': 'Existing evidence is sufficient.', 'output': {'answer': 'done'}})
        result, events = self.run_case(executor=executor)
        self.assertEqual(result['status'], 'completed')
        self.assertFalse(self.called)
        self.assertFalse(any(e['event_type'] == 'agent.spawned' for e in events))

    def test_dynamic_generation_has_distinct_identity_and_no_fixed_child_nodes(self):
        from tests.test_planner import local_service, request
        service = local_service()
        static_request = request('Classify a support request')
        static = service.plan(static_request)['data']['workflow']
        dynamic_request = request('Classify a support request', key='dynamic_plan_1234')
        dynamic_request['payload']['context'] = {'generation_mode': 'hierarchy', 'delegation_mode': 'runtime_v1'}
        dynamic = service.plan(dynamic_request)['data']['workflow']
        self.assertNotEqual(static['workflow_id'], dynamic['workflow_id'])
        self.assertTrue(dynamic['metadata']['dynamic_delegation'])
        self.assertEqual(len([n for n in dynamic['nodes'] if n['kind'] == 'agent']), 1)
