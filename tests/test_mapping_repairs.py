from copy import deepcopy
import pytest
from tests.test_simpsons_recurring_queries import pipeline,automation,google_setup,connected,composition,investigation,retrieval,knowledge,reference,generation,foundation,auth,release,queries
from workflow_api.readiness import repair_draft
from workflow_api.business_composition import verify_composition

@pytest.mark.parametrize('field',['reviewed_simpsons_queries','data_query_catalog','business_knowledge'])
def test_exact_pinned_mapping_repair_without_source_reads(pipeline,field):
 p=pipeline;f=p.f;doc=p.router.handle(f.x.a,deepcopy(p.body));w=f.c.workflow(f.x.a,doc['composition_id'])
 context=w['metadata']['action_binding_context']['validated_context']
 if field not in context:pytest.skip('This preparation does not carry that binding namespace')
 expected=deepcopy(context[field]);context[field]={'incorrect_source_reference':True}
 with f.general.store.transaction() as db:
  fixes=repair_draft(f.general,w,f.x.a,db);verify_composition(db,f.x.a,w)
 assert context[field]==expected and any(r['field'].endswith(field) for r in fixes)
 assert not p.queries.reader.calls
