"""Source adapter attestations; metadata profiling is never a business sync."""
from datetime import datetime


def describe(adapter,config,version):
    value=dict(status='unverified',last_synced_at=None,extracted_at=None,coverage_start=None,coverage_end=None,source_version=None,metadata_revision=version,refresh_available=False)
    hook=getattr(adapter,'business_freshness',None)
    if hook:
        supplied=hook(config)
        if isinstance(supplied,dict):
            value.update({k:v for k,v in supplied.items() if k in value})
    # No timestamps can be inferred from metadata profiling or wall-clock reads.
    for key in ('last_synced_at','extracted_at','coverage_start','coverage_end'):
        try:
            if value[key] is not None and datetime.fromisoformat(value[key].replace('Z','+00:00')).tzinfo is None:raise ValueError()
        except (ValueError,TypeError,AttributeError):value[key]=None
    if value['status'] not in ('current','historical_snapshot','unverified'):value['status']='unverified'
    value['refresh_available']=value['refresh_available'] is True
    return value


def covers(source,filters):
    f=source.get('freshness',{})
    if f.get('status')!='current' or not f.get('last_synced_at'):return False
    try:
        start=datetime.fromisoformat(f['coverage_start']);end=datetime.fromisoformat(f['coverage_end'])
        low=next(datetime.fromisoformat(v['value']) for v in filters if v['op']=='gte')
        high=next(datetime.fromisoformat(v['value']) for v in filters if v['op']=='lt')
        return start<=low<high<=end
    except (KeyError,TypeError,ValueError,StopIteration):return False
