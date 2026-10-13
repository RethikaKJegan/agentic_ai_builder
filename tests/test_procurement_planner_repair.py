"""Offline generated-plan regressions, without application startup or providers."""
from copy import deepcopy
import json
from types import SimpleNamespace
import unittest
from connector_extension.tests.test_procurement_slice import PLAN
from planner.errors import PlannerFailure
from workflow_api.procurement import ProcurementPlanner


class PlannerRepairTests(unittest.TestCase):
    def setUp(self):
        self.plan=deepcopy(PLAN);self.plan.pop('project_id')
        self.plan.update(action_mode='automatic',supplier_mode='supplied',search_region='wt-wt',
            phase2={'enabled':True,'calendar_id':'primary','reminder_minutes':60,'purchasing_limit':'100,000','allow_single_offer':True})
        self.catalogs=[{'spreadsheet_id':identifier,'tables':[{'title':title,'range':title+'!A1:'+end+'1000',
            'header_row':1,'headers':headers}]} for identifier,title,end,headers in (
            ('requirements_book','Requirements','F',['ID','Category','Product','Qty','Unit','Specs']),
            ('vendors_book','Contacts','D',['ID','Supplier','Email','Categories']))]
        self.plan['requirements']['range']='Requirements!A1:F1000'
        self.plan['vendors']['range']='Contacts!A1:D1000'
        self.inputs=[]
        def response(**kwargs):
            self.inputs.append(kwargs)
            return SimpleNamespace(status='completed',output_text=json.dumps(self.plan))
        self.planner=ProcurementPlanner(None,SimpleNamespace(responses=SimpleNamespace(create=response)),'offline',
            lambda identifier:next(c for c in self.catalogs if c['spreadsheet_id']==identifier))
    def generate(self):
        return self.planner.generate('Procurement from https://docs.google.com/spreadsheets/d/requirements_book/edit '
            'and https://docs.google.com/spreadsheets/d/vendors_book/edit',{})
    def test_full_discovered_ranges_and_formatted_limit_generate(self):
        w=self.generate();p=w['metadata']['procurement_plan']
        self.assertEqual(p['requirements']['range'],'Requirements!A1:F101')
        self.assertEqual(p['vendors']['range'],'Contacts!A1:D101')
        self.assertEqual(p['phase2']['purchasing_limit'],'100000')
        self.assertEqual(p['requirements']['columns'],self.plan['requirements']['columns'])
        self.assertEqual(len(self.inputs),1)
    def test_invalid_policy_exposes_precise_code(self):
        self.plan['phase2']['purchasing_limit']='unlimited'
        with self.assertRaises(PlannerFailure) as caught:self.generate()
        self.assertEqual(caught.exception.code,'PROCUREMENT_PHASE2_SETUP_INVALID')
        self.assertEqual(caught.exception.details['requirement_codes'],['PROCUREMENT_PHASE2_SETUP_INVALID'])
        self.assertEqual(json.loads(self.inputs[1]['input'][1]['content'])['correction']['code'],'PROCUREMENT_PHASE2_SETUP_INVALID')
    def test_matching_currency_label_is_formatting_only(self):
        for value in ('INR 100000','INR 100,000','100000 INR'):
            with self.subTest(value=value):
                self.plan['phase2']['purchasing_limit']=value
                self.assertEqual(self.generate()['metadata']['procurement_plan']['phase2']['purchasing_limit'],'100000')
    def test_conflicting_currency_is_not_silently_converted(self):
        self.plan['phase2']['purchasing_limit']='USD 100000'
        with self.assertRaises(PlannerFailure) as caught:self.generate()
        self.assertEqual(caught.exception.code,'PROCUREMENT_PHASE2_SETUP_INVALID')
    def test_unknown_headers_are_not_invented(self):
        self.plan['requirements']['columns']['quantity']='Invented'
        with self.assertRaises(PlannerFailure) as caught:self.generate()
        self.assertEqual(caught.exception.code,'PROCUREMENT_MAPPING_REQUIRED')
    def test_outside_discovered_capacity_remains_rejected(self):
        self.plan['requirements']['range']='Requirements!A1:F2000'
        with self.assertRaises(PlannerFailure) as caught:self.generate()
        self.assertEqual(caught.exception.code,'PROCUREMENT_SOURCE_BOUNDS')

if __name__=='__main__':unittest.main()
