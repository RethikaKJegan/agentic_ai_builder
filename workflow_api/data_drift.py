"""Shared metadata drift helpers; sampled omissions never verify continuity."""
from difflib import SequenceMatcher
from .data_relationships import compatible


def rename_candidates(previous,current,limit=100):
    before={d['dataset_id']:d for d in (previous or {}).get('datasets',[])}
    result=[];compared=0
    for dataset in current.get('datasets',[]):
        old=before.get(dataset['dataset_id'])
        if not old:continue
        a={f['field_id']:f for f in old['fields']};b={f['field_id']:f for f in dataset['fields']}
        for left in a.keys()-b.keys():
            for right in b.keys()-a.keys():
                compared+=1
                if compared>10000 or len(result)>=limit:return result
                if not compatible(a[left],b[right]):continue
                score=SequenceMatcher(None,a[left]['name'].casefold(),b[right]['name'].casefold()).ratio()
                if score>=.6:
                    result.append(dict(dataset_id=dataset['dataset_id'],previous_field_id=left,current_field_id=right,
                        previous_name=a[left]['name'],current_name=b[right]['name'],naming_similarity=round(score,3),
                        classification='unverified_hypothesis',validation_status='needs_review',
                        sampled_omission_is_not_deletion=old.get('discovery_method')=='sampled'))
    return sorted(result,key=lambda c:(c['dataset_id'],c['previous_field_id'],c['current_field_id']))


def retain_targeted_observations(previous, current, observations=()):
    """Retain separately evidenced fields that a later bounded sample omits.

    Observation provenance is ontology-owned. Public field metadata retains the
    existing sampled/declared contract, and current observed types win.
    """
    from copy import deepcopy
    import json
    before={d['dataset_id']:d for d in (previous or {}).get('datasets',[])}
    for dataset in current.get('datasets',[]):
        if dataset.get('discovery_method')!='sampled':continue
        targeted={o['field']['name']:o['field'] for o in observations if o['dataset_id']==dataset['dataset_id']}
        if not targeted:continue
        fields={f['name']:f for f in dataset['fields']}
        try:schema=json.loads(dataset.get('validation_schema_json','{}'))
        except (TypeError,ValueError):schema={}
        for name,field in targeted.items():
            # A declared prohibition is stronger than historical observations.
            if schema.get('additionalProperties') is False and name not in schema.get('properties',{}):continue
            if name in fields:continue
            if len(fields)<1000:
                fields[name]=deepcopy(field)
                warning=f"{dataset['name']}.{name}: prior targeted observation retained; not observed in this bounded sample."
                if warning not in current.setdefault('warnings',[]):current['warnings'].append(warning)
            else:
                current.setdefault('warnings',[]).append(f"{dataset['name']}.{name}: prior observation unavailable because the field bound was reached.")
        # Sample enumeration order does not change a known field's identity.
        order=[f['name'] for f in before.get(dataset['dataset_id'],{}).get('fields',[]) if f['name'] in fields]
        order+=sorted(set(fields)-set(order))
        dataset['fields']=[fields[name] for name in order]
    return current
