"""Scoped evidence documents and metadata-only context for module extraction."""
from hashlib import sha256
import json
from pathlib import Path
import re
import secrets
from registry.safety import reject_secrets
from .business_ontology import identity, MODULES
from .google_connections import now
from .service import ApiFailure

ROOT=Path(__file__).resolve().parents[1]
REFERENCE=ROOT/'ontology/business-reference/simpson-evidence.json'
TARGETS={
 'organization':('oemnames','oems','users','limits'), 'engines':('enginedetails','products'),
 'complaints':('tickets','claims','claimsftps'), 'warranty':('tickets','enginedetails','claims','claimsftps'),
 'inspection':('jointinspectionreports','tickets','jirlogs'), 'failure':('simpsoncodes','jointinspectionreports','failedengineanalyses'),
 'replacement':('enginereplacements','partreplacements','floatengines','workorders','focs','floatengineftps'),
 'quality':('failedengineanalyses','failedpartanalyses','workorders'), 'capa':('icacapas','failedengineanalyses'),
 'effectivity':('internalcutins','servicebulletins','serviceinformations','failedengineanalyses'),
 'monitoring':('claimsftps','tickets','failedengineanalyses'), 'evidence':('jirlogs','jointinspectionreports','tickets'),
}


def summarize(doc):
    return {k:doc[k] for k in ('source_id','title','kind','module_ids','sha256','origin')}


class BusinessDocuments:
    def __init__(self, ontology):
        self.ontology=ontology;self.store=ontology.store

    @staticmethod
    def rows(db, scope):
        return [json.loads(r[0]) for r in db.execute('SELECT document FROM business_ontology_documents WHERE workspace=? AND owner=? ORDER BY document_id',scope).fetchall()]

    def add(self,auth,body):
        scope=identity(auth,True)
        if (not isinstance(body,dict) or set(body)!={'title','kind','module_ids','text'}
            or not isinstance(body['title'],str) or not 1<=len(body['title'].strip())<=160
            or body['kind'] not in ('blueprint','application_code','policy','process','evidence')
            or not isinstance(body['module_ids'],list) or not 1<=len(body['module_ids'])<=12
            or any(not isinstance(m,str) or m not in TARGETS for m in body['module_ids'])
            or len(body['module_ids'])!=len(set(body['module_ids']))
            or not isinstance(body['text'],str) or not 20<=len(body['text'].strip())<=16000):
            raise ApiFailure('BUSINESS_DOCUMENT_INVALID','Provide a title, source kind, module selection and 20–16000 characters of source text.',422)
        try:reject_secrets(body)
        except Exception:raise ApiFailure('SENSITIVE_DATA_DETECTED','Remove credentials from source documents.',422) from None
        text=body['text'].strip()
        doc=dict(source_id='doc_'+secrets.token_hex(16),title=body['title'].strip(),kind=body['kind'],module_ids=body['module_ids'],text=text,sha256=sha256(text.encode()).hexdigest(),origin='owner_supplied',created_at=now())
        with self.store.transaction() as db:
            if not self.ontology.document(db,scope):raise ApiFailure('BUSINESS_FOUNDATION_REQUIRED','Create the business foundation first.',409)
            self.save(db,scope,[doc])
        return summarize(doc)

    @staticmethod
    def save(db,scope,documents):
        existing={r[0] for r in db.execute('SELECT document_id FROM business_ontology_documents WHERE workspace=? AND owner=?',scope).fetchall()}
        if len(existing|{d['source_id'] for d in documents})>40:
            raise ApiFailure('BUSINESS_DOCUMENT_LIMIT','This workspace has reached the 40-source limit.',422)
        for doc in documents:
            reject_secrets(doc)
            db.execute('INSERT INTO business_ontology_documents VALUES (?,?,?,?) ON CONFLICT DO NOTHING',(*scope,doc['source_id'],json.dumps(doc)))

    def import_reference(self,auth,body):
        scope=identity(auth,True)
        if body!={}:raise ApiFailure('BUSINESS_DOCUMENT_INVALID','Reference import accepts an empty object.',422)
        bundle=json.loads(REFERENCE.read_text())
        with self.store.transaction() as db:
            workspace=self.ontology.document(db,scope)
            if not workspace or workspace['sources']!=bundle['required_sources']:
                raise ApiFailure('BUSINESS_REFERENCE_SCOPE','The supplied Simpson reference belongs to different source bindings. Add your own documents instead.',403)
            source_stamp(self.ontology,db,scope,workspace)
            for doc in bundle['documents']:
                if sha256(doc['text'].encode()).hexdigest()!=doc['sha256']:raise ValueError('Invalid reference hash')
            self.save(db,scope,bundle['documents'])
        return self.ontology.get(auth)

    def get(self,auth,document_id):
        scope=identity(auth)
        with self.store.transaction(write=False) as db:
            row=db.execute('SELECT document FROM business_ontology_documents WHERE workspace=? AND owner=? AND document_id=?',(*scope,document_id)).fetchone()
        if not row:raise ApiFailure('BUSINESS_DOCUMENT_NOT_FOUND','Source document not found.',404)
        return json.loads(row[0])


def source_stamp(ontology,db,scope,workspace):
    connections=ontology.connections(db,scope)
    if not workspace or any(cid not in connections or connections[cid]['connection_status']!='connected' for cid in workspace['sources'].values()):
        raise ApiFailure('BUSINESS_SOURCE_UNAVAILABLE','Both bound sources must remain connected.',409)
    return {role:dict(connection_id=cid,revision=connections[cid]['metadata_revision'],generation=connections[cid].get('generation')) for role,cid in workspace['sources'].items()}


def context_documents(ontology,db,scope,workspace,module_id):
    documents=[d for d in BusinessDocuments.rows(db,scope) if module_id in d['module_ids']]
    if not documents:raise ApiFailure('BUSINESS_EVIDENCE_REQUIRED','Import the supplied reference or add source documents for this module.',422)
    for role,cid in workspace['sources'].items():
        connection=ontology.connections(db,scope)[cid]
        row=db.execute('SELECT document FROM data_source_snapshots WHERE connection_id=? AND revision=?',(cid,connection['metadata_revision'])).fetchone()
        if not row:continue
        for dataset in json.loads(row[0]).get('datasets',[]):
            if dataset.get('name') not in TARGETS[module_id]:continue
            fields=[{'name':f['name'],'types':f.get('types',[])} for f in dataset.get('fields',[])
                    if isinstance(f.get('name'),str) and not re.search(r'password|secret|token|credential|private.?key|api.?key',f['name'],re.I)][:60]
            text='Saved sampled/declared schema; not business policy.\n'+json.dumps(dict(collection=dataset['name'],fields=fields),sort_keys=True)
            digest=sha256(text.encode()).hexdigest()
            documents.append(dict(source_id='meta_'+digest[:24],title=role+' / '+dataset['name'],kind='schema',module_ids=[module_id],text=text,sha256=digest,origin=dict(connection_id=cid,metadata_revision=connection['metadata_revision'])))
    # Avoid ambiguous duplicate citation IDs for identical metadata.
    documents=list({d['source_id']:d for d in documents}.values())
    if sum(len(d['text']) for d in documents)>65000:
        raise ApiFailure('BUSINESS_EVIDENCE_LIMIT','Selected module evidence exceeds 65000 characters. Narrow its source documents.',422)
    return documents
