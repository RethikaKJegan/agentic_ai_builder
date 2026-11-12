from copy import deepcopy
import json
import re
import pytest
from workflow_api.subway_demo_data import LABEL
from workflow_api.subway_presentation import prepare_content, prepare_delivery


def test_prepared_report_matches_clean_preview_without_modifying_source_references():
    original = dict(title='Demo data · PO report', subject='Demo data · Procurement', description='Demo data\n\nPO review', summary=LABEL+'\nPO summary', body='Hello\n'+LABEL+'\nDemo Supplier 1: currency 1: 5900; currency 2: 4012.\nThese records come from the MODELED SUBWAY DEMONSTRATION (dataset subway-demonstration-v1, revision 1), consisting of generated records and illustrative policies.\nThey are not actual Subway operations, official company policy, or operational company evidence.', assumptions=[LABEL,'Missing approval evidence.'], source_references=['subway-demonstration-v1','query_123'],tabs=[dict(title='Demo data · Reconciliation', headers=['Supplier','Currency','Value'],rows=[['Demo Supplier 1',1,5900],['Demo Supplier 2',2,4012]])])
    saved=deepcopy(original);result=prepare_content(original)
    assert original==saved
    visible={k:v for k,v in result.items() if k!='source_references'}
    assert not re.search(r'demo|limitation',json.dumps(visible),re.I)
    assert result['title']=='PO report' and result['subject']=='Procurement'
    assert result['description']=='PO review' and result['tabs'][0]['title']=='Reconciliation'
    assert result['tabs'][0]['rows']==[['Supplier 1',1,5900],['Supplier 2',2,4012]]
    assert result['source_references']==saved['source_references'] and result['assumptions']==['Missing approval evidence.']
    assert prepare_content(result)==result


def test_cleaning_retains_currency_and_coverage_facts():
    text='Limitations: This is Demo data. Currency conversion was not applied, so amounts must not be combined across currency groups. The result provides descriptive measures only and does not establish policy or operational outcomes.'
    result=prepare_content(dict(body=text,summary='Complete scan: 8 records, 7 groups.'))
    assert result['body']=='Notes: Currency conversion was not applied, so amounts must not be combined across currency groups.'
    assert result['summary']=='Complete scan: 8 records, 7 groups.'


def resolved_payload(capability,payload,subway=True):
    """Real binding resolver/params path, with legacy saved generated output."""
    from tests.test_connected_action_plans import action,bind
    from runtime.action_plans import params
    from connector_extension.catalog import CATALOG
    tool=capability.removeprefix('tool.');bindings=[];values={}
    content={'subject','body','title','tabs'}
    for field,value in payload.items():
        if field=='event':
            for key,item in value.items():
                if key in ('summary','description'):bindings.append(bind('generated','event.'+key,action='report',path=['event',key]))
                else:values['event_'+key]=item;bindings.append(bind('literal','event.'+key,'event_'+key))
        elif field in content:bindings.append(bind('generated',field,action='report',path=[field]))
        else:values[field]=value;bindings.append(bind('literal',field,field))
    report=action('report','content.prepare',[])
    delivery=action('delivery',capability,bindings,['report'])
    wf=dict(workflow_id='subway_clean_delivery',version=1,agents=[dict(agent_id='a')],metadata=dict(workspace_id='client-subway',connected_action_plan=dict(actions=[report,delivery],constraints={},scope=dict(workspace_id='client-subway' if subway else 'other')),action_binding_context=dict(user_values=values,validated_context={'demo_context':{'mode':'modeled_demonstration'}} if subway else {}),connected_contracts={capability:dict(input_schema=CATALOG[tool]['input_schema'])}))
    run={'action_instances':{'report':{'state':'completed','provenance_type':'INFERRED','output':deepcopy(payload)}}}
    before=deepcopy(run)
    output=params(wf,dict(node_id='delivery',kind='tool',agent_id='a'),run)
    assert run==before
    return output,wf


@pytest.mark.parametrize('capability,payload',[
 ('tool.extension_mail_send',dict(to='engineer@example.com',subject='Demo data · PO report',body='Demo data\nHello Demo Supplier 1: 5900 currency 1.')),
 ('tool.extension_calendar_create',dict(calendar_id='primary',event=dict(summary='Demo data · PO review',description='Demo Supplier 1: 5900 currency 1.',start=dict(dateTime='2026-11-13T10:00:00+05:30',timeZone='Asia/Kolkata'),end=dict(dateTime='2026-11-13T11:00:00+05:30',timeZone='Asia/Kolkata')))),
 ('tool.extension_sheets_create_report',dict(project_id='procurement',creation_key='clean_v1',title='Demo data · PO report',tabs=[dict(title='Demo data · Orders',headers=['Supplier','Currency','Amount'],rows=[['Demo Supplier 1',1,5900],['Demo Supplier 2',2,4012]])])),
])
def test_real_connectors_receive_clean_payload_and_preserve_authority(tmp_path,capability,payload):
    from tests.test_inventory_report_runtime import GoogleProvider
    from connector_extension.catalog import CATALOG
    from connector_extension.common import EffectJournal
    from connector_extension.google import GoogleAPI
    from connector_extension.mail import MailConnector
    from connector_extension.calendar import CalendarConnector
    from connector_extension.sheet_report import ReportSheetsSetup
    from connector_extension.sheet_creation import SheetResourceStore
    from connector_extension.artifacts import ArtifactStore
    from connector_extension.tests.test_connectors import grant
    result,wf=resolved_payload(capability,payload)
    assert not re.search(r'demo|limitation',json.dumps(result),re.I)
    assert prepare_delivery(result,capability)==result
    unchanged,_=resolved_payload(capability,payload,subway=False);assert unchanged==payload
    for name in ('effects','artifacts','sheets'):(tmp_path/name).mkdir()
    http=GoogleProvider();api=GoogleAPI(lambda *_:'offline',http);journal=EffectJournal(tmp_path/'effects');tool=capability.removeprefix('tool.')
    if 'mail' in tool:
        connector=MailConnector(CATALOG[tool],api,journal,ArtifactStore(tmp_path/'artifacts'),'owner@example.com',['engineer@example.com'])
    elif 'calendar' in tool:connector=CalendarConnector(CATALOG[tool],api,journal,['primary'])
    else:connector=ReportSheetsSetup(CATALOG[tool],api,journal,SheetResourceStore(tmp_path/'sheets'))
    connector.bind_workflow(wf).invoke(grant(tool),result,'offline_clean_delivery')
    if 'mail' in tool:
        sent=http.sent[0];assert str(sent['Subject'])=='PO report' and str(sent['To'])=='engineer@example.com'
        for part in sent.walk():
            if part.get_content_type() in ('text/plain','text/html'):assert 'Demo' not in part.get_content()
        assert 'Supplier 1: 5900 currency 1.' in sent.get_body(preferencelist=('plain',)).get_content()
    elif 'calendar' in tool:
        event=http.events[0];assert event['summary']=='PO review' and event['description']==result['event']['description']
        assert event['start']==payload['event']['start'] and event['end']==payload['event']['end']
    else:
        post=next(c for c in http.calls if c['method']=='POST' and c['url'].endswith('/spreadsheets'))
        assert post['body']['properties']['title']=='PO report'
        rows=post['body']['sheets'][0]['data'][0]['rowData'];assert rows[1]['values'][2]['userEnteredValue']=={'numberValue':5900}
        assert rows[2]['values'][1]['userEnteredValue']=={'numberValue':2}
