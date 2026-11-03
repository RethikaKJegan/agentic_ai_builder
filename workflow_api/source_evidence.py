"""Shared database profiling provenance, independent of ontology definitions."""
import json
from .google_connections import GoogleConnections, now
from .service import ApiFailure


class SourceEvidence:
    def __init__(self, manager):
        self.manager, self.store = manager, manager.store
        with self.store.transaction() as db:
            db.execute('CREATE TABLE IF NOT EXISTS source_profile_requests (job_id TEXT PRIMARY KEY)')
            for table in ('source_profiles','source_observations'):
                db.execute(f'CREATE TABLE IF NOT EXISTS {table} (connection_id TEXT PRIMARY KEY, document TEXT NOT NULL)')

    def import_profile_evidence(self):
        """Copy provenance only, preserving original tables and existing new rows."""
        with self.store.transaction() as db:
            for old,new in (('ontology_source_profiles','source_profiles'),('ontology_source_observations','source_observations'),('ontology_profile_requests','source_profile_requests')):
                if db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",(old,)).fetchone():
                    db.execute(f'INSERT OR IGNORE INTO {new} SELECT * FROM {old}')

    @staticmethod
    def requested(db,job):
        if db.execute('SELECT 1 FROM source_profile_requests WHERE job_id=?',(job,)).fetchone():return True
        if db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='ontology_profile_requests'").fetchone():
            return bool(db.execute('SELECT 1 FROM ontology_profile_requests WHERE job_id=?',(job,)).fetchone())
        return False

    @staticmethod
    def observations(db,cid):
        row=db.execute('SELECT document FROM source_observations WHERE connection_id=?',(cid,)).fetchone()
        if not row and db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='ontology_source_observations'").fetchone():
            row=db.execute('SELECT document FROM ontology_source_observations WHERE connection_id=?',(cid,)).fetchone()
        return json.loads(row[0]) if row else {}

    def request_profile(self, auth, cid):
        GoogleConnections.identity(auth, True)
        self.manager.configured()
        with self.store.transaction() as db:
            secret,doc=self.manager.owned(db,auth,cid)
            if not secret or doc['connection_status']!='connected':
                raise ApiFailure('BUSINESS_SOURCE_UNAVAILABLE','Connect this source before profiling.',409)
            active=db.execute("SELECT job_id FROM data_source_profile_jobs WHERE connection_id=? AND state IN ('queued','running')",(cid,)).fetchone()
            if active:
                raise ApiFailure('BUSINESS_PROFILE_BUSY','Source discovery is already queued or running. Refresh its saved status.',409)
            ready=doc.get('profiling_status')=='ready' and doc.get('metadata_revision',0)>0
            job=self.manager.queue(db,doc,invalidate=False)
            if ready:doc['profiling_status']='ready'
            self.manager.save(db,doc)
            db.execute('INSERT INTO source_profile_requests VALUES (?)',(job,))
            # Compatibility marker consumed by the existing worker. Keeping
            # both markers allows an in-flight job to survive a later rollout.
            if db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='ontology_profile_requests'").fetchone():
                db.execute('INSERT INTO ontology_profile_requests VALUES (?)',(job,))
            db.execute('INSERT INTO data_source_auto_jobs VALUES (?,?)',(job,cid))
            return dict(job_id=job,status='queued',limits=dict(rows_per_dataset=100,seconds=60),basis='bounded_sample')

    @staticmethod
    def store_profiles(db,cid,generation,revision,profiles):
        doc=dict(generation=generation,metadata_revision=revision,profiles=profiles,at=now())
        db.execute('INSERT INTO source_profiles VALUES (?,?) ON CONFLICT(connection_id) DO UPDATE SET document=excluded.document',(cid,json.dumps(doc)))
        # Preserve existing historical signatures and permit worker rollback.
        # This stores provenance only; no legacy editing service is invoked.
        if db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='ontology_source_profiles'").fetchone():
            db.execute('INSERT INTO ontology_source_profiles VALUES (?,?) ON CONFLICT(connection_id) DO UPDATE SET document=excluded.document',(cid,json.dumps(doc)))

    @staticmethod
    def profile(db,cid):
        row=db.execute('SELECT document FROM source_profiles WHERE connection_id=?',(cid,)).fetchone()
        if not row and db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='ontology_source_profiles'").fetchone():
            row=db.execute('SELECT document FROM ontology_source_profiles WHERE connection_id=?',(cid,)).fetchone()
        return json.loads(row[0]) if row else None
