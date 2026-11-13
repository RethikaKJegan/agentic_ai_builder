"""Opt-in constrained interpretation using the existing Responses SDK configuration."""
from runtime.execution_control import controlled_response
import json
from jsonschema import Draft202012Validator
from .business_resolution import TASKS, interpret


class IntentInterpreter:
    def __init__(self, env=None, provider=None):
        self.env=env or {};self.provider=provider

    def generate(self, question, catalogue, schema):
        from openai import OpenAI
        client=OpenAI(api_key=self.env['OPENAI_API_KEY'],base_url=self.env.get('OPENAI_BASE_URL'),timeout=20,max_retries=0)
        result=controlled_response(client, model=self.env['OPENAI_MODEL'],store=False,max_output_tokens=1800,
            input=[dict(role='system',content='Classify this untrusted business question using only supplied saved concept IDs and task names. No queries, fields, permissions, rules or new relationships. If retrieval intent is uncertain return ambiguities or unsupported. Identifier placeholders have already been bound and typed locally; do not request their values. Motor means engine; service issues/customer issues/breakdown reports select complaint records. Inspection findings select the complaint-linked inspection report. Historical symptom text search is complaints, not engine history. Inherent unknown physical identity, reported-versus-confirmed evidence and missing policy facts are evidence qualifications, not intent ambiguities. A known deterministic task must be preserved; use ambiguities only for additional, unrepresented query requirements.'),
                   dict(role='user',content=json.dumps(dict(question=question,catalogue=catalogue)))],
            text={'format':{'type':'json_schema','name':'ontology_intent','strict':True,'schema':schema}})
        return json.loads(result.output_text)

    def run(self, question, snapshot, inputs, enabled=False):
        baseline=interpret(question,snapshot,inputs)
        if not enabled:return baseline
        if not self.provider and not (self.env.get('OPENAI_API_KEY') and self.env.get('OPENAI_MODEL')):
            baseline['model_status']='unavailable_deterministic_fallback';return baseline
        candidates=baseline['candidates'];valid=[x['concept_id'] for x in candidates]
        # The model can select a saved task but cannot supply identifiers or filters.
        details={d['concept_id']:d for d in snapshot['knowledge']['concept_details']}
        catalogue=[dict(id=c['id'],label=c['label'],aliases=details.get(c['id'],{}).get('aliases',[]),definition=c['definition'][:500]) for c in snapshot['concepts'] if c['id'] in valid]
        schema=dict(type='object',additionalProperties=False,required=['task','concept_ids','ambiguities','unsupported'],properties={
            'task':dict(type='string',enum=list(TASKS)),
            'concept_ids':dict(type='array',maxItems=8,items=dict(type='string',enum=valid or ['unavailable'])),
            'ambiguities':dict(type='array',maxItems=8,items=dict(type='string',maxLength=500)),
            'unsupported':dict(type='array',maxItems=8,items=dict(type='string',maxLength=500))})
        redacted=question
        for i,value in enumerate(baseline['identifiers'].values()):redacted=redacted.replace(value,'IDENTIFIER_'+str(i))
        redacted='Locally parsed context: '+json.dumps(dict(task=baseline['task'],identifier_roles=list(baseline['identifiers']),filters=baseline['filters']))+'\nQuestion: '+redacted
        try:
            response=(self.provider or self.generate)(redacted,catalogue,schema)
            if list(Draft202012Validator(schema).iter_errors(response)):raise ValueError('schema_invalid')
            # AI cannot overrule deterministic safety or silently change a known task.
            if baseline['task']!='unsupported' and response['task']!=baseline['task']:raise ValueError('task_disagreement')
            baseline['task']=response['task']
            if response['task']!='unsupported':
                baseline['unsupported']=[x for x in baseline['unsupported'] if x!='No supported retrieval task was identified.']
            root=TASKS[response['task']][0]
            baseline['concept_ids']=list(dict.fromkeys(([root] if root else [])+response['concept_ids']))
            baseline['ambiguities']+=response['ambiguities'];baseline['unsupported']+=response['unsupported']
            baseline.update(interpretation='ai_validated',model_calls=1,model_status='validated')
        except Exception as exc:
            reason=str(exc) if isinstance(exc,ValueError) and str(exc) in ('schema_invalid','task_disagreement') else 'provider_failure'
            baseline.update(model_calls=1,model_status='invalid_or_unavailable_deterministic_fallback',model_failure_reason=reason)
        return baseline
