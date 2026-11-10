"""Scalar reference normalization preserves supplied authority and real traversals."""
from copy import deepcopy
import pytest
from workflow_api.goal_inputs import bind_internal
from workflow_api.action_bindings import binding_value
from runtime.service import RuntimeFailure


def normalized(kind,key='recipient',path=None,values=None,validated=None):
    context=dict(user_values=values if values is not None else {'recipient':'engineer@example.com'},validated_context={'goal':'Use the supplied recipient',**(validated or {})},configuration={},evidence={})
    binding=dict(kind=kind,key=key,path=[key] if path is None else path,target=['to'])
    actions=[dict(action_id='send',capability_id='tool.fixture',bindings=[binding],depends_on=[])]
    contract=dict(kind='tool',supported_operation='fixture.read',input_schema={'properties':{'to':{'type':'string'}}})
    bind_internal(actions,{'tool.fixture':contract},context,{},lambda cid,c:'fixture','test')
    return actions[0]['bindings'][0],context


@pytest.mark.parametrize('kind',['literal','context'])
def test_exact_live_recipient_self_path(kind):
    binding,ctx=normalized(kind)
    assert binding==dict(kind='literal',key='recipient',path=[],target=['to'])
    assert binding_value(binding,ctx,{})=='engineer@example.com'


@pytest.mark.parametrize('value',[{'recipient':'nested@example.com'},['first@example.com']])
def test_structured_values_are_not_flattened(value):
    binding,ctx=normalized('literal',values={'recipient':value})
    assert binding['path']==['recipient']
    if isinstance(value,dict):assert binding_value(binding,ctx,{})=='nested@example.com'
    else:
        with pytest.raises(RuntimeFailure):binding_value(binding,ctx,{})


def test_unknown_inputs_are_not_invented():
    binding,ctx=normalized('context',values={})
    with pytest.raises(RuntimeFailure) as error:binding_value(binding,ctx,{})
    assert error.value.code=='ACTION_INPUT_REQUIRED'


def test_nonredundant_invalid_path_keeps_validation_and_diagnostic():
    binding,ctx=normalized('literal',path=['address'])
    with pytest.raises(RuntimeFailure) as error:binding_value(binding,ctx,{})
    assert error.value.code=='ACTION_BINDING_INVALID'
    assert error.value.binding_issue['path']==['address']
    assert error.value.binding_issue['rule']=='invalid_binding_path'


def test_existing_context_namespace_wins_without_account_substitution():
    binding,ctx=normalized('context',validated={'recipient':'reviewed@example.com'})
    assert binding['kind']=='context' and binding['path']==[]
    assert binding_value(binding,ctx,{})=='reviewed@example.com'
