"""Explicit offline browser fixture server; never used by the product launcher."""
import tempfile
from pathlib import Path
from urllib.parse import urlparse
from connector_extension.app import STATE_ROOT, create_extension_app
from connector_extension.examples import connector_workflow


class OfflineTransport:
    def request(self, method, url, headers, body=None, timeout=30):
        if 'sheets.googleapis.com' in url and method == 'GET':
            if '?fields=' in url:
                identifier = url.split('/spreadsheets/')[1].split('?')[0]
                return {'spreadsheetId':identifier,'properties':{'title':'Requirements'},'sheets':[{'properties':{
                    'title':'Items','gridProperties':{'rowCount':1000,'columnCount':2}}}]}
            if url.endswith('A1%3AB1'): return {'values':[['item_id','quantity']]}
            return {'values': [['item_id', 'quantity'], ['p1', 4]]}
        if '/users/me/calendarList' in url and method == 'GET':
            return {'items':[{'id':'team_calendar','summary':'Team','timeZone':'Asia/Kolkata','accessRole':'writer'}]}
        if '/calendar/v3/' in url and method == 'POST': return {'id': body['id'], 'status': 'confirmed'}
        if '/gmail/v1/users/me/profile' in url and method == 'GET': return {'emailAddress':'connected@example.com'}
        if '/gmail/v1/users/me/messages/send' in url and method == 'POST': return {'id':'offline_mail','threadId':'offline_thread'}
        raise RuntimeError('Offline fixture has no provider operation for this request')


class OfflinePlanner:
    def generate(self, objective, context):
        from workflow_api.sheet_discovery import spreadsheet_references
        references=spreadsheet_references(objective)
        inputs=({'spreadsheet_url':f'https://docs.google.com/spreadsheets/d/{references[0]}/edit','range':'Items!A1:B10'}
                if references else {'spreadsheet_id':'sheet_one','range':'Items!A1:B10'})
        workflow=connector_workflow('google_sheets_read_rows',inputs)
        workflow['name']='New spreadsheet check'
        return workflow


def main():
    import uvicorn
    STATE_ROOT.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='browser-', dir=STATE_ROOT) as directory:
        config = {'enabled_providers':['google_sheets','google_calendar','gmail','brave_search']}
        app = create_extension_app(config, Path(directory), transport=OfflineTransport(), token_supplier=lambda scopes,timeout:'offline',
                                   planner_provider=OfflinePlanner(), search_key='offline', start_workers=False)
        service,auth=app.state.workflow_service,app.state.extension_auth
        fixtures=[('google_sheets_read_rows', {'spreadsheet_id':'sheet_one','range':'Items!A1:B10'},'extension_sheet_browser','Extension Sheets smoke'),
                  ('extension_calendar_create', {'calendar_id':'team_calendar','event':{'summary':'Quote deadline',
                    'start':{'date':'2026-11-01'},'end':{'date':'2026-11-02'}}},'extension_calendar_browser','Extension Calendar smoke'),
                  ('extension_mail_send', {'to':'new-recipient@example.org','subject':'New recipient','body':'Hello from the connected account'},
                   'extension_mail_browser','Extension Mail smoke')]
        for tool,inputs,identity,name in fixtures:
            workflow=connector_workflow(tool,inputs,identity);workflow['name']=name
            ref={'workflow_id':identity,'workflow_version':1}
            for operation,payload,key in [('save_workflow_version',{**ref,'base_version':0,'workflow':workflow},'save_'+identity),
                ('validate_workflow',ref,'validate_'+identity),('approve_workflow',{**ref,'action':'approve'},'approve_'+identity),
                ('approve_workflow',{**ref,'action':'publish'},'publish_'+identity)]:
                result=service.handle({'request_id':'req_fixture','operation':operation,'idempotency_key':key,'payload':payload},auth)
                if result['status']!=200: raise RuntimeError('Offline fixture setup failed')
            result=service.handle_lifecycle('activate_release', {'request_id':'req_release','operation':'activate_release',
                'idempotency_key':'activate_'+identity,'payload':{**ref,'expected_release_id':None,'triggers':[]}},auth)
            if result['status']!=200: raise RuntimeError('Offline fixture activation failed')
        uvicorn.run(app,host='127.0.0.1',port=8013,log_level='warning')

if __name__=='__main__': main()
