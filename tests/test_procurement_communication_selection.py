import unittest
from workflow_api.procurement_observability import communication_actions
class CommunicationSelectionTests(unittest.TestCase):
    def test_polling_does_not_hide_real_agent_definitions(self):
        actions={'ingestion':{'run_id':'ingest'},'ful_extract_actual':{'run_id':'extract'}}
        actions.update({f'ful_read_thread_{i:04}':{'run_id':f'poll_{i}'} for i in range(240)})
        actions.update({f'sync_record_{i:04}':{'run_id':f'sync_{i}'} for i in range(120)})
        selected=dict(communication_actions(actions))
        self.assertLessEqual(len(selected),100)
        self.assertEqual(selected['ingestion'],actions['ingestion'])
        self.assertEqual(selected['ful_extract_actual'],actions['ful_extract_actual'])
        self.assertLessEqual(sum(k.startswith('ful_read_') for k in selected),10)
        self.assertTrue(all(actions[k]==v for k,v in selected.items()))
    def test_small_histories_stay_exact(self):
        actions={'send_rfq':{'run_id':'sent'},'ingestion':{'run_id':'ingest'}}
        self.assertEqual(communication_actions(actions),list(actions.items()))
