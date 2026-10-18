"""Bounded CrewAI model bridge; every provider request reserves its own budget."""
import json
import math
import os
from pathlib import Path
import re
import time

os.environ['CREWAI_TESTING'] = 'true'
os.environ['CREWAI_TRACING_ENABLED'] = 'false'
os.environ['CREWAI_DISABLE_TELEMETRY'] = 'true'
os.environ['CREWAI_STORAGE_DIR'] = str(Path(__file__).resolve().parents[1] / '.local/crewai')
from crewai.llms.base_llm import BaseLLM
from registry.safety import reject_secrets
from jsonschema import Draft202012Validator
from .service import RuntimeFailure


class BoundedLLM(BaseLLM):
    def __init__(self, definition, provider, count_tokens, input_rate, output_rate, clock=time.monotonic):
        super().__init__(model=definition['model']['model_id'])
        if any(type(v) not in (int, float) or not math.isfinite(v) or v < 0 for v in (input_rate, output_rate)):
            raise ValueError('Configure finite nonnegative provider rates per token.')
        self.output_schema = definition['output_schema']
        self.limits = definition['limits']
        self.provider_call, self.count_tokens = provider, count_tokens
        self.input_rate, self.output_rate, self.clock = input_rate, output_rate, clock
        self.started, self.calls, self.reserved_tokens, self.reserved_cost = clock(), 0, 0, 0.0
        self.last_failure = None
        self.actual_usage = {'llm_calls': 0, 'tokens': 0, 'estimated_cost_usd': 0.0}
        self.control_format = None
        self.control_context = None

    def call(self, messages, tools=None, callbacks=None, available_functions=None, **kwargs):
        try:
            return self._call(messages, tools, callbacks, available_functions, **kwargs)
        except RuntimeFailure as exc:
            self.last_failure = exc
            raise

    def _call(self, messages, tools=None, callbacks=None, available_functions=None, **kwargs):
        if tools or available_functions:
            raise RuntimeFailure('MODEL_TOOL_CALL_DENIED', 'Tools are dispatched only through the authorized application boundary.', 403)
        reject_secrets(messages)
        # Basic data guardrails; policy/schema gates remain authoritative even
        # when injection detection misses an adversarial phrasing.
        serialized = json.dumps(messages)
        if re.search(r'ignore (?:all |the )?(?:previous|system) instructions|reveal (?:the )?system prompt', serialized, re.I):
            raise RuntimeFailure('PROMPT_INJECTION_DETECTED', 'Model input contains an instruction override.', 400)
        redacted = re.sub(r'\b[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}\b|\b\d{3}-\d{2}-\d{4}\b', '[REDACTED]', serialized)
        safe_messages = json.loads(redacted)
        input_size = self.count_tokens(safe_messages)
        if type(input_size) is not int or input_size < 0:
            raise RuntimeFailure('INVALID_USAGE', 'Provider token accounting is unavailable.')
        remaining = self.limits['max_tokens'] - self.reserved_tokens
        completion_cap = remaining - input_size
        duration = self.limits['timeout_seconds'] - (self.clock() - self.started)
        if self.calls >= self.limits['max_llm_calls'] or completion_cap < 1 or duration <= 0:
            raise RuntimeFailure('BUDGET_EXHAUSTED', 'The next model request exceeds an agent budget.')
        cost = input_size * self.input_rate + completion_cap * self.output_rate
        if self.reserved_cost + cost > self.limits.get('max_estimated_cost_usd', 0):
            raise RuntimeFailure('BUDGET_EXHAUSTED', 'The next model request exceeds the agent cost budget.')
        # Reserve the worst case before provider invocation. Unused capacity is
        # not refunded, including failed requests and hidden CrewAI retries.
        self.calls += 1
        self.reserved_tokens += input_size + completion_cap
        self.reserved_cost += cost
        try:
            text, actual_input, actual_output = self.provider_call(safe_messages, completion_cap, duration)
            if (type(actual_input) is not int or type(actual_output) is not int or min(actual_input, actual_output) < 0 or
                    actual_input > input_size or actual_output > completion_cap or self.clock() - self.started > self.limits['timeout_seconds']):
                raise RuntimeFailure('MODEL_USAGE_EXCEEDED', 'The provider response exceeded the reserved usage or duration.')
            reject_secrets(text)
            try:
                output = json.loads(text)
            except (ValueError, TypeError):
                raise RuntimeFailure('MODEL_OUTPUT_INVALID_JSON', 'The provider did not return a complete JSON object.') from None
            if list(Draft202012Validator(self.output_schema).iter_errors(output)):
                raise RuntimeFailure('MODEL_OUTPUT_SCHEMA_INVALID', 'The provider JSON did not satisfy the required schema.')
            self.actual_usage['llm_calls'] += 1
            self.actual_usage['tokens'] += actual_input + actual_output
            self.actual_usage['estimated_cost_usd'] += actual_input * self.input_rate + actual_output * self.output_rate
            # CrewAI's bounded single-turn executor expects a Final Answer marker.
            # The provider returns JSON; the application supplies this delimiter.
            return 'Final Answer: ' + json.dumps(output)
        except RuntimeFailure:
            raise
        except Exception as exc:
            raise RuntimeFailure('MODEL_INVOCATION_FAILED', 'The model failed or exceeded reserved usage.') from None

    def supports_stop_words(self):
        return False


class OpenAIModelFactory:
    """Server-owned provider pricing and tokenizer; credentials stay in SDK."""
    def __init__(self, rates, client=None, tokenizers=None):
        self.rates, self.client, self.tokenizers = rates, client, tokenizers or {}

    def __call__(self, definition):
        model = definition['model']
        if model['provider'] != 'openai' or model['model_id'] not in self.rates:
            raise RuntimeFailure('MODEL_NOT_CONFIGURED', 'Configure the exact provider/model and cost ceiling.', 503)
        os.environ['TIKTOKEN_CACHE_DIR'] = str(Path(__file__).resolve().parents[1] / '.local/tiktoken')
        from openai import OpenAI
        import tiktoken
        try:
            encoding = (tiktoken.get_encoding(self.tokenizers[model['model_id']]) if model['model_id'] in self.tokenizers
                        else tiktoken.encoding_for_model(model['model_id']))
        except KeyError as exc:
            raise RuntimeFailure('MODEL_TOKENIZER_REQUIRED', 'Configure a supported exact model tokenizer.', 503) from None
        client = self.client.with_options(max_retries=0) if self.client is not None else OpenAI(max_retries=0)
        def count(messages):
            # Conservative upper bound for Responses framing plus encoded content.
            extra = ''
            if bridge.control_format is not None:
                from .model_protocol import INSTRUCTIONS
                extra = json.dumps(bridge.control_format) + INSTRUCTIONS
            return len(encoding.encode(json.dumps(messages))) + len(encoding.encode(extra)) + 1024
        def invoke(messages, cap, timeout):
            response_format = {'type':'json_object'}
            if bridge.control_format is not None:
                from .model_protocol import INSTRUCTIONS
                messages = [*messages,{'role':'system','content':INSTRUCTIONS}]
                response_format = bridge.control_format
            response = client.responses.create(model=model['model_id'], input=messages, max_output_tokens=cap,
                                               timeout=timeout, store=False, text={'format': response_format})
            if getattr(response, 'status', None) == 'incomplete':
                raise RuntimeFailure('MODEL_OUTPUT_TRUNCATED', 'The provider could not complete its output within the reserved output tokens.')
            text = response.output_text
            if bridge.control_format is not None:
                from .model_protocol import decode_response
                text = decode_response(text, bridge.control_context, bridge.control_format['schema'])
            return text, response.usage.input_tokens, response.usage.output_tokens
        rates = self.rates[model['model_id']]
        bridge = BoundedLLM(definition, invoke, count, rates['input_per_token'], rates['output_per_token'])
        return bridge
