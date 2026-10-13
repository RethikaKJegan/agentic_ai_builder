"""Opt-in internal tool contracts and exact Registry-bound adapters."""
from copy import deepcopy
from jsonschema import Draft202012Validator
from registry.contracts import validate
from connector_extension.catalog import definition, obj, string
from connector_extension.common import Connector, denied

PROJECT={'type':'string','pattern':'^[A-Za-z][A-Za-z0-9_-]{1,127}$'}
ROWS={'type':'array','maxItems':101,'items':{'type':'array','maxItems':100,'items':{'type':['string','number','boolean','null']}}}


def tools():
    result=[]
    for identifier,capability,inputs in (
        ('extension_procurement_ingest','procurement_ingest',obj({'project_id':PROJECT,'requirements_rows':ROWS,'vendor_rows':ROWS},
          ['project_id','requirements_rows','vendor_rows'])),
        ('extension_procurement_status','procurement_status',obj({'project_id':PROJECT},['project_id']))):
        tool=definition(identifier,'procurement',capability,'Read scoped procurement state' if capability.endswith('status') else
            'Validate actual mapped source tables and persist BOQ, vendors and RFQs; no external writes.',
            inputs,{'type':'object'},[],'data.read' if capability.endswith('status') else 'data.write')
        tool['authentication']={'mode':'none','credential_reference_required':False,'scopes':[]}
        validate(tool,'tool');result.append(tool)
    return {t['tool_id']:t for t in result}


TOOLS=tools()


class ProcurementConnector(Connector):
    def __init__(self, definition, service):
        super().__init__(definition,None);self.service=service;self.project_id=None

    def bind_workflow(self, workflow):
        bound=super().bind_workflow(workflow)
        bound.project_id=workflow.get('metadata',{}).get('procurement_project_id')
        bound.review_agents=workflow.get('metadata',{}).get('procurement_required_reviews',[])
        return bound

    def invoke(self, grant, inputs, effect_id):
        t=self.definition
        if not self.namespace or not self.project_id or inputs.get('project_id')!=self.project_id:
            denied('PROCUREMENT_SCOPE_MISMATCH','Use the reviewed project-bound workflow.')
        if (grant.get('tool_id')!=t['tool_id'] or grant.get('authorization_state')!='authorized' or
            not grant.get('authorization_reference') or grant.get('input_schema')!=t['input_schema'] or
            grant.get('output_schema')!=t['output_schema']):
            denied('CONNECTOR_NOT_AUTHORIZED','Use the exact current internal Registry binding.')
        if list(Draft202012Validator(t['input_schema']).iter_errors(inputs)):
            denied('CONNECTOR_INPUT_INVALID','Use bounded source rows and the reviewed project.',400)
        from .store import ProcurementError
        try:
            if t['tool_id']=='extension_procurement_ingest':
                job=self.service.job(self.namespace[0],self.project_id)
                if self.namespace[1]!=job['ingestion_workflow_id'] or self.namespace[2]!=1:
                    denied('PROCUREMENT_SCOPE_MISMATCH','Ingestion belongs to the exact registered source workflow.')
                if self.review_agents:
                    auth=self.service.auth_supplier(self.namespace[0])
                    events=self.service.workflows.runtime_runner.runtime.events(effect_id.split(':',1)[0],auth)['items']
                    returned={e['details'].get('source_agent_id') for e in events
                              if e['workflow_id']==self.namespace[1] and e['workflow_version']==self.namespace[2] and
                              e['event_type']=='node.handoff' and e['details'].get('transfer_kind')=='delegated_result'}
                    if not set(self.review_agents)<=returned:
                        denied('PROCUREMENT_REVIEW_INCOMPLETE','Both source specialists must return results before preparation.',409)
                return self.service.ingest(self.namespace[0],self.project_id,inputs['requirements_rows'],inputs['vendor_rows'])
            status=self.service.status(self.namespace[0],self.project_id)
            return {k:status[k] for k in ('project_id','phase','issues','record_counts')}
        except ProcurementError as exc:
            denied(exc.code,'Procurement validation stopped this operation.',409)


def ingestion_workflow(plan, workflow_id):
    from connector_extension.examples import connector_workflow
    workflow=connector_workflow('google_sheets_read_rows',{},workflow_id)
    template=workflow['agents'][0];agents={}
    for name,capability in (('requirements','read_spreadsheet'),('vendors','read_spreadsheet'),('prepare','procurement_ingest')):
        a=deepcopy(template);a['agent_id']=workflow_id+'_'+name;a['role']=name.title()+' specialist'
        a['goal']='Use actual authorized tool results for '+name+'; preserve missing facts.'
        a['instructions']='Use the deterministic mapped tool node; do not infer authority or invent source values.'
        a['capabilities']=[capability];a['permissions']=['workflow.read_input','data.read']+(['data.write'] if name=='prepare' else [])
        a['limits']['max_tool_calls']=3;agents[name]=a
    workflow['agents']=list(agents.values())
    workflow['name']='Procurement source ingestion';workflow['description']='Read selected requirements and supplied vendor contacts, then persist validated BOQ and RFQs.'
    workflow['tools']=[{'tool_id':'google_sheets_read_rows','capability':'read_spreadsheet'},
                       {'tool_id':'extension_procurement_ingest','capability':'procurement_ingest'}]
    workflow['metadata']['procurement_project_id']=plan['project_id']
    nodes=[{'node_id':'start','kind':'trigger','label':'Start procurement'}]
    for name,source in (('requirements',plan['requirements']),('vendors',plan['vendors'])):
        nodes.append({'node_id':name,'kind':'tool','label':'Read '+name,'tool_id':'google_sheets_read_rows',
            'agent_id':agents[name]['agent_id'],'configuration':{'input':{'spreadsheet_id':source['spreadsheet_url'],'range':source['range']}}})
    nodes.extend([{'node_id':'ingest','kind':'tool','label':'BOQ and RFQ preparation','tool_id':'extension_procurement_ingest',
        'agent_id':agents['prepare']['agent_id'],'configuration':{'input_mapping':{'project_id':repr(plan['project_id']),
            'requirements_rows':'nodes.requirements.rows','vendor_rows':'nodes.vendors.rows'}}},
        {'node_id':'finish','kind':'output','label':'Prepared','configuration':{'input':{}}}])
    workflow['nodes']=nodes
    workflow['edges']=[{'edge_id':'edge_'+str(i),'source':nodes[i]['node_id'],'target':nodes[i+1]['node_id']} for i in range(len(nodes)-1)]
    return deepcopy(workflow)
