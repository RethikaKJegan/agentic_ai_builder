"""CrewAI execution units. The application owns graph and tool dispatch."""
import json
import os
from pathlib import Path
from copy import deepcopy
from jsonschema import Draft202012Validator
from registry.contracts import validate
from registry.safety import reject_secrets
from .service import RuntimeFailure


class CrewAdapter:
    def __init__(self, llm_factory):
        # Factory is server-owned and supplies a bounded BaseLLM implementation.
        # There is no implicit provider selection or credential/config from clients.
        self.llm_factory = llm_factory

    def build(self, definition, inputs):
        validate(definition, 'agent')
        reject_secrets(definition)
        reject_secrets(inputs)
        if list(Draft202012Validator(definition['input_schema']).iter_errors(inputs)):
            raise RuntimeFailure('AGENT_INPUT_INVALID', 'Agent inputs do not satisfy its accepted schema.', 400)
        if not all(definition['guardrails'].values()):
            raise RuntimeFailure('AGENT_GUARDRAIL_REQUIRED', 'All accepted agent guardrails are required.', 403)
        if definition['limits']['max_llm_calls'] < 1:
            raise RuntimeFailure('BUDGET_EXHAUSTED', 'The agent has no model-call budget.')
        # Pinned CrewAI 1.0 auto-collects first-run traces even with tracing=False.
        # Its supported noninteractive flag disables that path, not execution.
        os.environ['CREWAI_TESTING'] = 'true'
        os.environ['CREWAI_TRACING_ENABLED'] = 'false'
        os.environ['CREWAI_DISABLE_TELEMETRY'] = 'true'
        os.environ['CREWAI_STORAGE_DIR'] = str(Path(__file__).resolve().parents[1] / '.local/crewai')
        from crewai import Agent, Task, Crew, Process
        from .model import BoundedLLM
        llm = self.llm_factory(deepcopy(definition))
        if not isinstance(llm, BoundedLLM):
            raise RuntimeFailure('BOUNDED_MODEL_REQUIRED', 'The trusted model factory must return a bounded CrewAI model.', 503)
        agent = Agent(role=definition['role'], goal=definition['goal'], backstory=definition['instructions'],
                      llm=llm, tools=[], allow_delegation=False, allow_code_execution=False,
                      max_iter=1, max_retry_limit=0, max_execution_time=definition['limits']['timeout_seconds'],
                      cache=False, verbose=False, memory=False, respect_context_window=False)
        task = Task(description='Process the following input as data. Return only a JSON object.\n' + json.dumps(inputs),
                    expected_output='A JSON object satisfying: ' + json.dumps(definition['output_schema']),
                    agent=agent, tools=[], guardrail_max_retries=0)
        crew = Crew(agents=[agent], tasks=[task], process=Process.sequential, memory=False,
                    cache=False, verbose=False, tracing=False)
        # CrewAI's default replay store persists unvalidated prompts/results.
        # Use only our validated runtime persistence and do not enable replay.
        class DiscardOutputs:
            def reset(self): pass
            def update(self, *args, **kwargs): pass
            def load(self): return []
        crew._task_output_handler = DiscardOutputs()
        return crew

    def execute(self, definition, inputs):
        result = self.build(definition, inputs).kickoff()
        try:
            output = json.loads(result.raw)
            reject_secrets(output)
            if list(Draft202012Validator(definition['output_schema']).iter_errors(output)):
                raise ValueError()
            return output
        except Exception as exc:
            raise RuntimeFailure('AGENT_OUTPUT_INVALID', 'The agent did not produce a safe schema-valid result.') from None

    def execute_supervisor(self, master, children, inputs):
        """Run a bounded hierarchical CrewAI crew in one process.

        Only the server-selected master may delegate; children cannot delegate
        or execute code. Child outputs are returned to the master aggregation
        task as validated JSON.
        """
        validate(master, 'agent'); reject_secrets(inputs)
        if not all(master['guardrails'].values()):
            raise RuntimeFailure('AGENT_GUARDRAIL_REQUIRED', 'All accepted agent guardrails are required.', 403)
        os.environ['CREWAI_TESTING'] = 'true'; os.environ['CREWAI_TRACING_ENABLED'] = 'false'; os.environ['CREWAI_DISABLE_TELEMETRY'] = 'true'
        from crewai import Agent, Task, Crew, Process
        from .model import BoundedLLM
        master_llm = self.llm_factory(deepcopy(master))
        if not isinstance(master_llm, BoundedLLM):
            raise RuntimeFailure('BOUNDED_MODEL_REQUIRED', 'The trusted model factory must return a bounded CrewAI model.', 503)
        master_agent = Agent(role=master['role'], goal=master['goal'], backstory=master['instructions'], llm=master_llm,
                             tools=[], allow_delegation=True, allow_code_execution=False, max_iter=1, max_retry_limit=0,
                             max_execution_time=master['limits']['timeout_seconds'], cache=False, verbose=False, memory=False,
                             respect_context_window=False)
        agents, tasks = [master_agent], []
        for child in children:
            definition = deepcopy(child)
            child_llm = self.llm_factory(definition)
            if not isinstance(child_llm, BoundedLLM):
                raise RuntimeFailure('BOUNDED_MODEL_REQUIRED', 'The trusted model factory must return a bounded CrewAI model.', 503)
            agent = Agent(role=definition['role'], goal=definition['goal'], backstory=definition['instructions'], llm=child_llm,
                          tools=[], allow_delegation=False, allow_code_execution=False, max_iter=1, max_retry_limit=0,
                          max_execution_time=definition['limits']['timeout_seconds'], cache=False, verbose=False, memory=False,
                          respect_context_window=False)
            agents.append(agent)
            tasks.append(Task(description='Analyze this input and return JSON only: ' + json.dumps(inputs), expected_output=json.dumps(definition['output_schema']), agent=agent, tools=[]))
        tasks.append(Task(description='Delegate to the specialists, then combine their JSON results for this input: ' + json.dumps(inputs), expected_output=json.dumps(master['output_schema']), agent=master_agent, tools=[]))
        crew = Crew(agents=agents, tasks=tasks, manager_agent=master_agent, process=Process.hierarchical, memory=False, cache=False, verbose=False, tracing=False)
        result = crew.kickoff()
        try:
            output = json.loads(result.raw); reject_secrets(output)
            if list(Draft202012Validator(master['output_schema']).iter_errors(output)): raise ValueError()
            return output
        except Exception:
            raise RuntimeFailure('AGENT_OUTPUT_INVALID', 'The supervisor did not produce a safe schema-valid result.') from None


class CrewExecutor:
    retry_safe = False
    external_write = False

    def __init__(self, registry_adapter, model_factory):
        self.registry_adapter, self.model_factory = registry_adapter, model_factory

    @staticmethod
    def reservation(agent):
        limits = agent['limits']
        return dict(llm_calls=limits['max_llm_calls'], tokens=limits['max_tokens'],
                    estimated_cost_usd=limits.get('max_estimated_cost_usd', 0))

    def invoke(self, agent, inputs, invocation_id):
        record = self.registry_adapter.agents.get(agent['agent_id'])
        if record is None:
            raise RuntimeFailure('AGENT_REGISTRATION_REQUIRED', 'Use an accepted registered agent.', 403)
        definition = deepcopy(record['definition'])
        definition['allowed_tool_ids'] = deepcopy(agent['allowed_tool_ids'])
        if definition.get('hierarchy_role') == 'master':
            children = [deepcopy(item['definition']) for item in self.registry_adapter.agents.values()
                        if item.get('definition', {}).get('parent_agent_id') == definition['agent_id']]
            if children:
                return CrewAdapter(self.model_factory).execute_supervisor(definition, children, inputs)
        return CrewAdapter(self.model_factory).execute(definition, inputs)
