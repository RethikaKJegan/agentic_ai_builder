"""Optional Brave Search; result pages are never fetched or executed."""
import time
from datetime import date
from urllib.parse import urlencode, urlparse
from .common import Connector, denied


class SearchConnector(Connector):
    def __init__(self, definition, transport, resolve):
        super().__init__(definition, transport)
        self.resolve = resolve

    def execute(self, grant, inputs, effect_id, deadline):
        key = self.resolve(grant['credential_reference'])
        if not isinstance(key, str) or not key.strip() or any(c in key for c in '\r\n'):
            denied('SEARCH_NOT_CONFIGURED', 'Configure a separate Brave Search API key.', 503)
        limit = inputs.get('limit', 5)
        query = {'q': inputs['query'], 'count': limit, 'offset': inputs.get('page', 0)}
        if inputs.get('country'): query['country'] = inputs['country'].upper()
        if inputs.get('language'): query['search_lang'] = inputs['language'].lower()
        if inputs.get('freshness'):
            freshness = inputs['freshness']
            if 'to' in freshness:
                try:
                    start, end = [date.fromisoformat(value) for value in freshness.split('to')]
                    if start > end: raise ValueError()
                except ValueError: denied('SEARCH_FILTER_INVALID', 'Use a valid ordered freshness date range.', 400)
            query['freshness'] = freshness
        payload = self.api.request('GET', 'https://api.search.brave.com/res/v1/web/search?' + urlencode(query),
            {'X-Subscription-Token': key, 'Accept': 'application/json'}, timeout=min(30, deadline - time.monotonic()))
        results = []
        for item in payload.get('web', {}).get('results', [])[:limit]:
            url = item.get('url', '')
            parsed = urlparse(url)
            if parsed.scheme not in {'http', 'https'} or not parsed.netloc or parsed.username or parsed.password: continue
            results.append({'title': str(item.get('title', ''))[:300], 'url': url[:2000], 'snippet': str(item.get('description', ''))[:2000]})
        more = payload.get('query', {}).get('more_results_available')
        if type(more) is not bool: more = None
        return {'results': results, 'has_more': more, 'next_page': query['offset'] + 1 if more and query['offset'] < 9 else None}
