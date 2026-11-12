"""Versioned semantic date parameters. No source reads or scheduling side effects."""
from copy import deepcopy
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
from .service import ApiFailure

VERSION = 'relative-query-v1'
ANNOTATION = 'x-praxi-relative-query-v1'
PERIODS = {'today', 'yesterday', 'this_week', 'previous_week', 'current_month', 'previous_month', 'last_n_days', 'previous_quarter', 'current_quarter'}


def fail(message):
    raise ApiFailure('AUTOMATION_TEMPORAL_INVALID', message, 422)


def window(period, zone, due, days=1):
    if period not in PERIODS or type(days) is not int or not 1 <= days <= 90:
        fail('Choose a supported date period and 1–90 days.')
    try:
        local = datetime.fromtimestamp(due, timezone.utc).astimezone(ZoneInfo(zone))
    except (ValueError, TypeError, OverflowError, ZoneInfoNotFoundError):
        fail('Supply a valid occurrence time and IANA timezone.')
    start = local.replace(hour=0, minute=0, second=0, microsecond=0)
    if period == 'yesterday':
        end = start; start -= timedelta(days=1)
    elif period in {'this_week', 'previous_week'}:
        start -= timedelta(days=start.weekday())
        if period == 'previous_week': start -= timedelta(days=7)
        end = start + timedelta(days=7)
    elif period in {'current_quarter', 'previous_quarter'}:
        month = ((start.month - 1) // 3) * 3 + 1
        start = start.replace(month=month, day=1)
        if period == 'previous_quarter':
            start = start.replace(year=start.year - 1, month=10) if month == 1 else start.replace(month=month - 3)
        end = start.replace(year=start.year + 1, month=1) if start.month == 10 else start.replace(month=start.month + 3)
    elif period in {'current_month', 'previous_month'}:
        start = start.replace(day=1)
        if period == 'previous_month': start = (start - timedelta(days=1)).replace(day=1)
        end = (start.replace(day=28) + timedelta(days=4)).replace(day=1)
    else:
        end = start + timedelta(days=1)
        if period == 'last_n_days': start -= timedelta(days=days - 1)
    return tuple(d.astimezone(timezone.utc).isoformat() for d in (start, end))


def validate_pin(pin, query):
    if (not isinstance(pin, dict) or set(pin) != {'version', 'period', 'timezone', 'days', 'field_id', 'lower_index', 'upper_index'}
            or pin['version'] != VERSION or pin['period'] not in PERIODS):
        fail('Use a complete reviewed relative-query-v1 parameter.')
    window(pin['period'], pin['timezone'], 0, pin['days'])
    low, high = pin['lower_index'], pin['upper_index']
    if type(low) is not int or type(high) is not int or low == high:
        fail('Pin two distinct filter positions.')
    filters = query.get('filters', [])
    if not 0 <= low < len(filters) or not 0 <= high < len(filters): fail('Pinned date filters are absent.')
    for index, op in ((low, 'gte'), (high, 'lt')):
        f = filters[index]
        if set(f) != {'field_id', 'op', 'value'} or f['field_id'] != pin['field_id'] or f['op'] != op:
            fail('Only the reviewed half-open date bounds may vary.')
        if not isinstance(f['value'], str): fail('Date bounds must be timezone-aware timestamps.')
        try:
            if datetime.fromisoformat(f['value'].replace('Z', '+00:00')).tzinfo is None: fail('Date bounds need a timezone.')
        except ValueError: fail('Invalid reviewed date bound.')
    return pin


def resolve(query, pin, due):
    validate_pin(pin, query)
    result = deepcopy(query)
    for index, value in zip((pin['lower_index'], pin['upper_index']), window(pin['period'], pin['timezone'], due, pin['days'])):
        result['filters'][index]['value'] = value
    return result


def consent_schema(schema, due):
    """Materialize only an explicitly annotated exact-query schema."""
    result = deepcopy(schema)
    pin = result.pop(ANNOTATION, None)
    if pin is not None:
        query = result.get('properties', {}).get('query', {}).get('const')
        if not isinstance(query, dict): fail('Relative consent requires an exact query template.')
        result['properties']['query']['const'] = resolve(query, pin, due)
    return result
