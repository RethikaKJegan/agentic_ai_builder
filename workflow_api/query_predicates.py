"""Conjunction checks on typed query literals; never change filter meaning."""
from collections import defaultdict
from datetime import datetime,timezone

FILTER_GUIDANCE = (
    ' Flat query filters are combined with AND, never OR. For requested alternative '
    'conditions, create a separate query-plan/read branch for each alternative and '
    'include every branch result as a direct reporting dependency. Repeat shared '
    'scope, date, currency and authorization constraints in each branch. Each query '
    'agent implements its assigned action branch; the overall goal describes the '
    'whole workflow and must not merge other branches into its conjunction. Never '
    'combine mutually exclusive conditions on one field, drop an alternative, or '
    'invent an OR operator. Reports must label each branch and use its actual '
    'matched count and coverage. Do not sum overlapping branch counts or claim a '
    'distinct union count without validated record-identity deduplication. A scan '
    'with contradictory filters does not establish that each requested category is absent.'
)


def validate_conjunction(filters,fields):
    from .subway_queries import fail,key
    def invalid():
        fail('Conjunctive filters contradict each other on the same field. Filters use AND; plan separate queries for alternatives without dropping conditions.','SUBWAY_QUERY_INVALID')
    def literal(field,value):
        if value is None:return None
        types=set(field.get('types',[]))-{'null'}
        if types & {'date','datetime','timestamp'}:
            value=datetime.fromisoformat(value.replace('Z','+00:00'))
            if value.tzinfo:value=value.astimezone(timezone.utc).replace(tzinfo=None)
        elif types=={'ObjectId'}:
            from bson import ObjectId
            value=ObjectId(value)
        return key(value)
    grouped=defaultdict(list)
    for predicate in filters:grouped[predicate['field_id']].append(predicate)
    for fid,predicates in grouped.items():
        null=any(p['op']=='is_null' or p['op']=='eq' and p['value'] is None for p in predicates)
        nonnull=any(p['op'] in {'not_null','gt','gte','lt','lte'} or p['op']=='eq' and p['value'] is not None or p['op']=='ne' and p['value'] is None for p in predicates)
        if null and nonnull:invalid()
        equals=[];excluded=[];lower=[];upper=[]
        for p in predicates:
            op=p['op']
            if op in {'is_null','not_null'}:continue
            if op in {'gt','gte','lt','lte'} and p['value'] is None:
                fail('Ordered comparisons require a non-null literal value.','SUBWAY_QUERY_INVALID')
            try:value=literal(fields[fid],p['value'])
            except Exception:continue  # Existing typed-value validation handles malformed literals.
            if op=='eq':equals.append(value)
            elif op=='ne':excluded.append(value)
            elif op in {'gt','gte'}:lower.append((value,op=='gte'))
            elif op in {'lt','lte'}:upper.append((value,op=='lte'))
        if len(set(equals))>1 or any(v in excluded for v in equals):invalid()
        bounds=lower+upper
        # Compare only values with identical native types; never coerce meanings.
        if not bounds or any(v is None for v,_ in bounds) or len({v[0] for v,_ in bounds})!=1:continue
        low=max((v for v,_ in lower),default=None)
        high=min((v for v,_ in upper),default=None)
        low_inclusive=all(include for v,include in lower if v==low)
        high_inclusive=all(include for v,include in upper if v==high)
        if low is not None and high is not None and (low>high or low==high and not (low_inclusive and high_inclusive)):invalid()
        for equal in equals:
            if equal is None or equal[0]!=bounds[0][0][0]:continue
            if low is not None and (equal<low or equal==low and not low_inclusive):invalid()
            if high is not None and (equal>high or equal==high and not high_inclusive):invalid()
