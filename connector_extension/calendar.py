"""Explicit Calendar event operations; endpoints never come from model output."""
from datetime import date, datetime
import hashlib
from urllib.parse import quote, urlencode
from zoneinfo import ZoneInfo
from .common import Connector, denied


def validate_event(event):
    start, end = event['start'], event['end']
    try:
        if ('date' in start) != ('date' in end): raise ValueError()
        if 'date' in start:
            if date.fromisoformat(start['date']) >= date.fromisoformat(end['date']): raise ValueError()
        else:
            ZoneInfo(start['timeZone']); ZoneInfo(end['timeZone'])
            first, last = [datetime.fromisoformat(value['dateTime'].replace('Z', '+00:00')) for value in (start, end)]
            if first.tzinfo is None or last.tzinfo is None or first >= last: raise ValueError()
    except (ValueError, KeyError):
        denied('CALENDAR_TIME_INVALID', 'Use matching all-day dates or timezone-aware times with end after start.', 400)


class CalendarConnector(Connector):
    def __init__(self, definition, api, journal=None, calendars=None):
        super().__init__(definition, api, journal)
        self.calendars = frozenset(calendars or [])

    def execute(self, grant, inputs, effect_id, deadline):
        action = self.definition['tool_id'].removeprefix('extension_calendar_')
        if action == 'discover':
            query = {'maxResults': inputs.get('limit', 50), 'minAccessRole': 'reader'}
            if 'page_token' in inputs: query['pageToken'] = inputs['page_token']
            result = self.api.request('calendar', 'GET', 'users/me/calendarList?' + urlencode(query),
                                     ['calendar.calendarlist.readonly'], deadline=deadline)
            items = result.get('items', [])
            if not isinstance(items, list) or len(items) > query['maxResults']:
                denied('CALENDAR_OUTPUT_INVALID', 'The calendar discovery response exceeds its bound.', 502)
            calendars = []
            for item in items:
                primary = bool(item.get('primary', False))
                if self.calendars and item.get('id') not in self.calendars and not (primary and 'primary' in self.calendars): continue
                identifier = 'primary' if primary and 'primary' in self.calendars else item['id']
                calendars.append({'calendar_id': identifier, 'name': item.get('summary', ''),
                    'time_zone': item.get('timeZone'), 'access_role': item.get('accessRole'), 'primary': bool(item.get('primary', False))})
            return {'calendars': calendars, 'next_page_token': result.get('nextPageToken')}
        calendar = inputs.get('calendar_id', 'primary')
        if self.calendars and calendar not in self.calendars:
            denied('CALENDAR_NOT_AUTHORIZED', 'This calendar is outside the optional operator restriction.')
        base = 'calendars/' + quote(calendar, safe='') + '/events'
        if action == 'list':
            query = {'maxResults': inputs.get('limit', 50), 'singleEvents': 'true', 'orderBy': 'startTime'}
            for field, parameter in [('time_min', 'timeMin'), ('time_max', 'timeMax'), ('page_token', 'pageToken')]:
                if field in inputs: query[parameter] = inputs[field]
            result = self.api.request('calendar', 'GET', base + '?' + urlencode(query), ['calendar.events.readonly'], deadline=deadline)
            events = result.get('items', [])
            if not isinstance(events, list) or len(events) > query['maxResults']:
                denied('CALENDAR_OUTPUT_INVALID', 'The Calendar response exceeds its requested limit.', 502)
            return {'events': [{key: item[key] for key in ('id', 'summary', 'description', 'start', 'end', 'status', 'reminders') if key in item}
                               for item in events], 'next_page_token': result.get('nextPageToken')}
        if action != 'cancel': validate_event(inputs['event'])
        def write():
            if action == 'cancel':
                self.api.request('calendar', 'DELETE', base + '/' + quote(inputs['event_id'], safe='') + '?sendUpdates=none',
                                 ['calendar.events'], deadline=deadline)
                return {'event_id': inputs['event_id'], 'status': 'cancelled'}
            event = dict(inputs['event'])
            # Calendar custom IDs accept base32hex. Hex SHA256 is a valid subset.
            if action == 'create': event['id'] = hashlib.sha256(effect_id.encode()).hexdigest()
            path = base if action == 'create' else base + '/' + quote(inputs['event_id'], safe='')
            result = self.api.request('calendar', 'POST' if action == 'create' else 'PATCH', path + '?sendUpdates=none',
                                     ['calendar.events'], event, deadline)
            if action == 'update' and result.get('id') != inputs['event_id']:
                denied('CALENDAR_OUTPUT_INVALID', 'The Calendar response identifies a different event.', 502)
            return {'event_id': result['id'], 'status': result.get('status', 'confirmed')}
        return self.write(effect_id, inputs, write)
