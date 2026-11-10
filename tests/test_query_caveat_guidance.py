"""Trusted query guidance distinguishes schema caveats from missing user meaning."""
from copy import deepcopy
from tests.test_workflow_query_integration import automation,google_setup,connected,composition,investigation,retrieval,knowledge,reference,generation,foundation,auth,release,queries,setup_query,compile_run,stored,complete
from tests.test_data_queries import plan
from runtime.crew import QUERY_CLARIFICATION_GUIDANCE


def test_count_needs_no_unit_and_metadata_caveat_does_not_replace_engine_coverage(automation,queries):
    f=automation;p=plan()
    p.update(metrics=[dict(label='ticket_count',op='count',expression='')],limit=1,explanation='Count accessible records; disclose execution coverage in the report.')
    queries.reader.rows['pg_lines']*=201  # 603 source rows, beyond display limit.
    jobs,seen,inputs,body=setup_query(f,queries,p,expected_rows=[{'ticket_count':603}])
    provider=f.general.planner.provider.plan_actions
    def read_only(goal,context):
        proposal=deepcopy(provider(goal,context));proposal['actions']=proposal['actions'][:3];proposal['completion_criteria']=['analysis'];return proposal
    f.general.planner.provider.plan_actions=read_only
    body['objective']='Count every accessible record in the selected dataset across all statuses with no date or operating-hours filter. Report source, total and completeness. Do not email or create spreadsheets.'
    seen_messages=[];factory=f.runner.agents.model_factory
    def with_message_check(definition):
        model=factory(definition);transport=model.provider_call
        if set(definition['output_schema']['properties'])=={'query'}:
            def call(messages,*args):
                text='\n'.join(m['content'] for m in messages)
                assert QUERY_CLARIFICATION_GUIDANCE.strip() in text
                seen_messages.append(True)
                return transport(messages,*args)
            model.provider_call=call
        return model
    f.runner.agents.model_factory=with_message_check
    doc,w,rid=compile_run(f,body)
    assert f.runner.advance(rid,f.x.a)['status']=='running'
    assert seen_messages==[True] and stored(f,rid)['action_instances']['read']['state']=='waiting_for_query'
    assert jobs.tick();f.now+=2
    assert complete(f,w,rid)['status']=='completed'
    output=stored(f,rid)['action_instances']['read']['output']
    assert output['result']['rows']==[{'ticket_count':603}]
    assert output['coverage']['complete_scan'] and output['coverage']['aggregate_complete']
    assert not f.http.sent and f.http.write_count==0
