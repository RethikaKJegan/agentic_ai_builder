import hashlib
import hmac
import time
from copy import deepcopy

from fastapi.testclient import TestClient
import pytest

from scripts.subway_client import provision, create_subway_app
from workflow_api.client_isolation import ClientIsolation, HEADER


def token(client, secret):
    payload = f'{client}.{int(time.time()) + 60}.{"a" * 48}'
    return payload + '.' + hmac.new(secret.encode(), payload.encode(), hashlib.sha256).hexdigest()


@pytest.fixture
def subway(tmp_path):
    env = provision(tmp_path / 'subway', 'subway.admin@example.com', 'test-password')
    return env, create_subway_app(env)


def test_subway_has_own_identity_and_no_company_data_or_execution(subway):
    env, app = subway
    with TestClient(app) as client:
        assert client.get('/session').status_code == 401
        client.headers[HEADER] = token('subway', env['BUILDER_SUBWAY_PROXY_SECRET'])
        session = client.get('/session').json()['data']
        assert session['auth']['subject'] == {'workspace_id': 'client-subway', 'subject_id': 'subway-client'}
        assert session['mode'] == 'client-isolated'
        assert session['planning_available'] is session['runtime_available'] is False
        assert client.get('/data-sources').json()['data']['items'] == []
        ontology = client.get('/business-ontology/v1').json()['data']
        assert ontology['workspace'] is None and ontology['versions'] == []
        assert client.get('/workflows').json()['data']['items'] == []
        assert client.get('/data-sources/simpsons-source/metadata').status_code == 404
        assert client.post('/workflows/plan', json={}).status_code == 409
        assert client.post('/data-sources', json={}).status_code == 409
        assert client.post('/business-ontology/v1/initialize', json={}).status_code == 409


def test_client_audience_is_checked_even_if_secrets_accidentally_match(subway):
    env, app = subway
    secret = env['BUILDER_SUBWAY_PROXY_SECRET']
    with TestClient(app) as client:
        assert client.get('/session', headers={HEADER: token('simpsons', secret)}).status_code == 401
        assert client.get('/session', headers={HEADER: token('subway', 'different-secret-with-32-characters')}).status_code == 401
    other = deepcopy(env)
    other.update(BUILDER_CLIENT_ID='simpsons', BUILDER_SIMPSONS_PROXY_SECRET=secret)
    with pytest.raises(ValueError):
        ClientIsolation.configured(other)
