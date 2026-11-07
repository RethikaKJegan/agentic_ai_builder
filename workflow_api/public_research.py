"""Explicit tenant public research using existing bounded keyless connectors."""
from copy import copy,deepcopy
import re
from urllib.parse import unquote
from runtime.supplier_search import SEARCH,PAGE,SupplierSearchConnector
from runtime.service import RuntimeFailure


def enabled(env):
    value=env.get('BUILDER_CLIENT_WEB_ENABLED','0')
    if value not in {'0','1'}:raise ValueError('BUILDER_CLIENT_WEB_ENABLED must be0 or1.')
    return value=='1'


def extend_registry(config):
    for definition in (SEARCH,PAGE):
        config['tools'].append({'definition':deepcopy(definition)})
        config['policy']['remaining_quota'][definition['tool_id']]=10000
    config['policy']['approved_providers']=sorted(set(config['policy']['approved_providers'])|{'ddgs'})
    for target,key in ((config['policy'],'agent_permissions'),(config,'subject_permissions'),(config,'subject_scopes')):
        target[key]=sorted(set(target.get(key,[]))|{'data.read'})


class PublicResearch(SupplierSearchConnector):
    def __init__(self,definition,service):
        super().__init__(definition);self.service=service;self.private_identifiers=()
    def bind_context(self,workflow,run,auth,node):
        bound=copy(self);identifiers=[]
        pin=workflow.get('metadata',{}).get('business_preparation')
        if pin:
            doc=self.service.business_preparation.checked(auth,pin['preflight_id'])
            identifiers.extend(doc['inputs']['identifiers'].values())
            for evidence in doc.get('available_evidence',{}).values():
                for record in evidence.get('records',[]):
                    for key in ('mapping:ticket_id','mapping:ticket_serial','mapping:invoice_serial','mapping:qa_serial'):
                        value=record.get('values',{}).get(key,{}).get('value')
                        if isinstance(value,(str,int)):identifiers.append(str(value))
        values=workflow.get('metadata',{}).get('action_binding_context',{}).get('user_values',{})
        identifiers.extend(values[k] for k in ('complaint_id','serial') if k in values)
        bound.private_identifiers=tuple(str(value) for value in identifiers)
        return bound
    def execute(self,grant,inputs,effect_id,deadline):
        outbound=unquote(inputs.get('query',inputs.get('url','')))
        normalized=lambda value:''.join(re.findall('[a-z0-9]',value.lower()))
        if re.search(r'[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}',outbound) or any(normalized(value) in normalized(outbound) for value in self.private_identifiers if normalized(value)):
            raise RuntimeFailure('PUBLIC_QUERY_PRIVATE_DATA','Use public technical terms without complaint IDs, engine serials or email addresses.',400)
        return super().execute(grant,inputs,effect_id,deadline)


def install(service):
    for definition in (SEARCH,PAGE):service.runtime_runner.connectors[definition['tool_id']]=PublicResearch(definition,service)
