"""Pinned read-only local dump adapter; the cloud connector policy is unchanged."""
from contextlib import contextmanager
import hashlib
import json
from pathlib import Path
from urllib.parse import urlsplit

from .data_source_adapters import CloudAdapters
from .service import ApiFailure


class RestoredSubwayAdapters(CloudAdapters):
    def __init__(self, env):
        super().__init__(env)
        if env.get('BUILDER_CLIENT_ID') != 'subway':
            raise ValueError('The restore adapter is only available to Subway.')
        self.manifest = json.loads(Path(env['BUILDER_SUBWAY_RESTORED_MANIFEST']).read_text())
        if self.manifest.get('client_id') != 'subway':
            raise ValueError('Invalid restored source manifest.')

    def target(self, config):
        target = self.manifest['sources'].get(config.get('_subway_source_id'))
        uri = urlsplit(config.get('uri', ''))
        if (not target or config.get('engine') != 'mongodb' or
                config.get('database') != target['database'] or uri.scheme != 'mongodb' or
                uri.hostname != '127.0.0.1' or uri.port != 27028 or
                hashlib.sha256(config['uri'].encode()).hexdigest() != target['uri_sha256']):
            raise ApiFailure('DATA_SOURCE_NOT_AUTHORIZED', 'The source is outside the pinned Subway restore.', 403)
        return target

    def business_freshness(self, config):
        self.target(config)
        return dict(status='historical_snapshot',last_synced_at=None,extracted_at=None,coverage_start=None,coverage_end=None,refresh_available=False)

    @contextmanager
    def connection(self, config):
        self.target(config)
        from pymongo import MongoClient
        with MongoClient(config['uri'], serverSelectionTimeoutMS=5000, connectTimeoutMS=5000,
                         socketTimeoutMS=10000, maxPoolSize=2, retryReads=False, retryWrites=False) as client:
            yield client
