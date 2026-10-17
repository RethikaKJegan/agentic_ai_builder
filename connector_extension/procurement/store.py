"""Extension-owned procurement transactions. No API, worker or provider calls."""
from contextlib import contextmanager
from copy import deepcopy
from datetime import datetime, timezone
from decimal import Decimal, localcontext, ROUND_HALF_UP
import hashlib
import json
import os
from pathlib import Path
import re
import sqlite3
from workflow_api.auxiliary_database import connection as database_connection
from zoneinfo import ZoneInfo
from jsonschema import Draft202012Validator, FormatChecker

ROOT = Path(__file__).resolve().parent
STATE_ROOT = ROOT.parents[1] / '.local/connector-extension'
SCHEMA = json.loads((ROOT/'contracts/v1/records.schema.json').read_text())
STATES = json.loads((ROOT/'contracts/v1/states.json').read_text())
KINDS = ('project', 'boq_item', 'vendor', 'rfq', 'quotation', 'award',
         'purchase_order', 'fulfilment_event', 'approval', 'evidence')
TABLES = dict(zip(KINDS, ('projects','boq_items','vendors','rfqs','quotations','awards',
                         'purchase_orders','fulfilment_events','approvals','evidence')))
ID = re.compile(r'^[A-Za-z][A-Za-z0-9_-]{1,127}$')


class ProcurementError(ValueError):
    def __init__(self, code):
        self.code = code
        super().__init__(code)


def require(condition, code):
    if not condition: raise ProcurementError(code)


def encoded(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False)


def timestamp(value):
    return datetime.fromisoformat(value.replace('Z', '+00:00'))


def scope_digest(items):
    """Fingerprint commercial BOQ fields, excluding status and bookkeeping revisions."""
    fields=('section','description','quantity','unit','specifications','delivery_location','delivery_deadline')
    snapshot=[{'item_id':r['record_id'],**{k:r['data'][k] for k in fields}}
              for r in sorted(items,key=lambda r:r['record_id'])]
    return hashlib.sha256(encoded(snapshot).encode()).hexdigest()


class ProcurementStore:
    """Trusted in-process boundary; callers must supply authenticated scope.

    authority_check(evidence, role) verifies the source and subject independently.
    approval_check(approval, target, operation) resolves exact canonical approval.
    Neither callback is derived from model output or a persisted authority label.
    Currency precision is operator supplied; unsupported currencies stop actions.
    """
    def __init__(self, state_dir=None, *, authority_check=None, approval_check=None,
                 currency_precision=None, clock=None, database_url=None):
        root = Path(state_dir or STATE_ROOT).absolute()
        require(root.resolve().is_relative_to(STATE_ROOT.resolve()), 'STATE_PATH_INVALID')
        require(not root.is_symlink(), 'STATE_PATH_INVALID')
        root.mkdir(parents=True, exist_ok=True, mode=0o700)
        self.database_url=database_url
        self.path = root/'procurement.sqlite3'
        require(not self.path.is_symlink(), 'STATE_PATH_INVALID')
        self.authority_check, self.approval_check = authority_check, approval_check
        self.precision = dict(currency_precision or {})
        require(all(re.fullmatch('[A-Z]{3}', k) and type(v) is int and 0 <= v <= 6
                    for k,v in self.precision.items()), 'CURRENCY_CONFIGURATION_INVALID')
        self.clock = clock or (lambda: datetime.now(timezone.utc))
        self.validator = Draft202012Validator(SCHEMA, format_checker=FormatChecker())
        with self.connection() as db:
            version = db.execute('PRAGMA user_version').fetchone()[0]
            require(version in (0,1), 'DATABASE_VERSION_UNSUPPORTED')
            db.execute('CREATE TABLE IF NOT EXISTS records (workspace TEXT, project TEXT, id TEXT, '
                       'kind TEXT NOT NULL, revision INTEGER NOT NULL, body TEXT NOT NULL, '
                       'PRIMARY KEY(workspace,project,id))')
            for table in TABLES.values():
                db.execute(f'CREATE TABLE IF NOT EXISTS {table} (workspace TEXT, project TEXT, id TEXT, '
                           'body TEXT NOT NULL, PRIMARY KEY(workspace,project,id), '
                           'FOREIGN KEY(workspace,project,id) REFERENCES records(workspace,project,id))')
            db.execute('CREATE TABLE IF NOT EXISTS revisions (workspace TEXT, project TEXT, id TEXT, '
                       'revision INTEGER, body TEXT NOT NULL, PRIMARY KEY(workspace,project,id,revision), '
                       'FOREIGN KEY(workspace,project,id) REFERENCES records(workspace,project,id))')
            db.execute('CREATE TABLE IF NOT EXISTS transactions (workspace TEXT, project TEXT, key TEXT, '
                       'fingerprint TEXT NOT NULL, result TEXT NOT NULL, PRIMARY KEY(workspace,project,key))')
            db.execute('CREATE TABLE IF NOT EXISTS activity (sequence INTEGER PRIMARY KEY, workspace TEXT, '
                       'project TEXT, transaction_key TEXT, record_id TEXT, revision INTEGER, recorded_at TEXT)')
            db.execute('CREATE TABLE IF NOT EXISTS unique_refs (workspace TEXT, project TEXT, category TEXT, '
                       'value TEXT, record_id TEXT, PRIMARY KEY(workspace,project,category,value), '
                       'FOREIGN KEY(workspace,project,record_id) REFERENCES records(workspace,project,id))')
            db.execute('CREATE TABLE IF NOT EXISTS resources (workspace TEXT, project TEXT, record_id TEXT, '
                       'provider TEXT, resource_type TEXT, resource_id TEXT, metadata TEXT NOT NULL, '
                       'PRIMARY KEY(workspace,project,record_id,provider,resource_type,resource_id), '
                       'FOREIGN KEY(workspace,project,record_id) REFERENCES records(workspace,project,id))')
            db.execute('CREATE TABLE IF NOT EXISTS sync_intents (workspace TEXT, project TEXT, key TEXT, '
                       'record_id TEXT, record_revision INTEGER, target TEXT, payload TEXT, status TEXT, '
                       'PRIMARY KEY(workspace,project,key), FOREIGN KEY(workspace,project,record_id,record_revision) '
                       'REFERENCES revisions(workspace,project,id,revision))')
            db.execute('PRAGMA user_version=1')
        if self.path.exists():os.chmod(self.path, 0o600)

    @contextmanager
    def connection(self,write=True):
        with database_connection(self.path,write=write,database_url=self.database_url) as db:
            yield db

    @staticmethod
    def scope(workspace, project):
        require(isinstance(workspace,str) and ID.fullmatch(workspace) and
                isinstance(project,str) and ID.fullmatch(project), 'SCOPE_INVALID')

    def get(self, workspace, project, record_id, revision=None):
        self.scope(workspace, project)
        with self.connection(write=False) as db:
            if revision is None:
                row=db.execute('SELECT body FROM records WHERE workspace=? AND project=? AND id=?',
                               (workspace,project,record_id)).fetchone()
            else:
                row=db.execute('SELECT body FROM revisions WHERE workspace=? AND project=? AND id=? AND revision=?',
                               (workspace,project,record_id,revision)).fetchone()
        return json.loads(row[0]) if row else None

    def list_records(self, workspace, project, kind=None):
        self.scope(workspace,project)
        require(kind is None or kind in KINDS, 'RECORD_KIND_INVALID')
        with self.connection() as db:
            rows=db.execute('SELECT body FROM records WHERE workspace=? AND project=?'+
                            (' AND kind=?' if kind else '')+' ORDER BY id',
                            (workspace,project,kind) if kind else (workspace,project)).fetchall()
        return [json.loads(r[0]) for r in rows]

    def history(self, workspace, project):
        self.scope(workspace,project)
        with self.connection(write=False) as db:
            rows=db.execute('SELECT transaction_key,record_id,revision,recorded_at FROM activity '
                            'WHERE workspace=? AND project=? ORDER BY sequence',(workspace,project)).fetchall()
        return [dict(zip(('transaction_key','record_id','revision','recorded_at'),r)) for r in rows]

    def resources(self, workspace, project):
        self.scope(workspace,project)
        with self.connection(write=False) as db:
            rows=db.execute('SELECT record_id,provider,resource_type,resource_id,metadata FROM resources '
                            'WHERE workspace=? AND project=?',(workspace,project)).fetchall()
        return [dict(record_id=r[0],provider=r[1],resource_type=r[2],resource_id=r[3],metadata=json.loads(r[4])) for r in rows]

    def pending_sync(self, workspace, project):
        self.scope(workspace,project)
        with self.connection(write=False) as db:
            rows=db.execute("SELECT key,record_id,record_revision,target,payload,status FROM sync_intents "
                            "WHERE workspace=? AND project=? ORDER BY key",(workspace,project)).fetchall()
        return [dict(key=r[0],record_id=r[1],record_revision=r[2],target=r[3],payload=json.loads(r[4]),status=r[5]) for r in rows]

    def trusted_evidence(self, evidence, role, simulation):
        data=evidence['data']
        if simulation and data['authority_state']=='SIMULATION_ONLY':
            return data['asserted_actor_role']==role
        return (data['authority_state']=='VERIFIED_SOURCE' and data['asserted_actor_role']==role and
                data['verified_subject_id'] is not None and self.authority_check is not None and
                self.authority_check(deepcopy(evidence),role) is True)

    def check_approval(self, approval, target, operation):
        require(approval is not None, 'APPROVAL_REQUIRED')
        d=approval['data'];now=self.clock()
        require(d['decision']=='APPROVED' and timestamp(d['expires_at'])>now and
                timestamp(d['decided_at'])<=now and d['approver']['workspace_id']==target['workspace_id'] and
                'approver' in d['approver']['roles'] and d['operation']==operation and
                self.approval_check is not None and
                self.approval_check(deepcopy(approval),deepcopy(target),operation) is True,
                'TRUSTED_APPROVAL_REQUIRED')

    def transition(self, old, new):
        kind=new['record_type'];d=new['data'];definition=STATES.get(kind)
        if old is None:
            require(not definition or d[definition.get('state_field','status')]==definition['initial'], 'INITIAL_STATE_REQUIRED')
            return
        require(kind==old['record_type'] and new['created_at']==old['created_at'] and
                timestamp(new['updated_at'])>=timestamp(old['updated_at']), 'IMMUTABLE_IDENTITY')
        require(kind not in ('evidence','fulfilment_event'), 'IMMUTABLE_EVIDENCE')
        if kind=='project':require(d['simulation']==old['data']['simulation'], 'SIMULATION_MODE_IMMUTABLE')
        if kind=='rfq' and old['data']['status']!='DRAFT':
            require(all(d[k]==old['data'][k] for k in ('scope_item_ids','scope_digest','vendor_id','recipient',
                    'quote_deadline','comparison_currency','subject_reference')), 'RFQ_SNAPSHOT_IMMUTABLE')
        if not definition: return
        field=definition.get('state_field','status');first,last=old['data'][field],d[field]
        require(first not in definition['terminal'], 'TERMINAL_RECORD')
        allowed=first==last or [first,last] in definition['edges']
        if kind=='purchase_order':
            if last=='ON_HOLD':
                allowed=first in definition['hold_from'] and d['resume_status']==first and bool(d['unresolved_exception_ids'])
            elif first=='ON_HOLD':
                allowed=last==old['data']['resume_status'] and not d['unresolved_exception_ids'] and d['resume_status'] is None
            elif last=='CANCELLED':
                # Released-order cancellation reconciliation requires a future explicit adapter.
                allowed=first in ('DRAFT','READY')
            if first!='DRAFT':
                for key in ('award_id','vendor_id','po_number','financials','delivery_location','required_delivery_date','payment_terms'):
                    require(d[key]==old['data'][key], 'ORDER_SNAPSHOT_IMMUTABLE')
                before={i['item_id']:i for i in old['data']['items']}
                require(set(before)=={i['item_id'] for i in d['items']}, 'ORDER_SNAPSHOT_IMMUTABLE')
                for line in d['items']:
                    for key,value in before[line['item_id']].items():
                        if key in ('packed_quantity','dispatched_quantity','delivered_quantity','buyer_accepted_quantity'):
                            require(Decimal(line[key])>=Decimal(value), 'QUANTITY_REGRESSION')
                        else: require(line[key]==value, 'ORDER_SNAPSHOT_IMMUTABLE')
        require(allowed, 'ILLEGAL_TRANSITION')

    def guards(self, record, all_records, old=None):
        kind=record['record_type'];d=record['data'];project=all_records.get(record['project_id'])
        require(project and project['record_type']=='project', 'PROJECT_NOT_FOUND')
        simulation=project['data']['simulation']
        def ref(identifier, expected):
            value=all_records.get(identifier)
            require(value is not None and value['record_type']==expected, 'REFERENCE_NOT_FOUND')
            return value
        for identifier in record['evidence_ids']: ref(identifier,'evidence')
        relation={'vendor_id':'vendor','rfq_id':'rfq','quotation_id':'quotation','award_id':'award',
                  'purchase_order_id':'purchase_order','approval_id':'approval','release_approval_id':'approval'}
        for key,expected in relation.items():
            if d.get(key) is not None: ref(d[key],expected)
        for key in ('source_evidence_ids','contact_evidence_ids','compliance_evidence_ids','buyer_confirmation_evidence_ids'):
            for identifier in d.get(key,[]):ref(identifier,'evidence')
        for identifier in d.get('scope_change_approval_ids',[]):ref(identifier,'approval')
        for identifier in d.get('scope_item_ids',[]):ref(identifier,'boq_item')
        for line in d.get('items',[]):ref(line['item_id'],'boq_item')
        if kind=='project':
            require(record['record_id']==record['project_id'], 'PROJECT_ID_MISMATCH')
            context=d['context']
            if context['time_zone'] is not None:
                try: ZoneInfo(context['time_zone'])
                except Exception: raise ProcurementError('TIMEZONE_INVALID') from None
            if d['status'] in ('ACTIVE','COMPLETED'):
                require(context['comparison_currency'] in self.precision, 'CURRENCY_NOT_CONFIGURED')
                require(d['required_item_ids'], 'PROJECT_SCOPE_REQUIRED')
                for identifier in d['required_item_ids']:ref(identifier,'boq_item')
            require(set(d['resolved_item_ids'])|set(d['excluded_item_ids'])<=set(d['required_item_ids']), 'PROJECT_SCOPE_MISMATCH')
            if d['status']=='COMPLETED':
                required=set(d['required_item_ids']);resolved=set(d['resolved_item_ids']);excluded=set(d['excluded_item_ids'])
                require(not resolved&excluded and required==resolved|excluded, 'PROJECT_SCOPE_UNRESOLVED')
                closed={i['item_id'] for r in all_records.values() if r['record_type']=='purchase_order'
                        and r['data']['status']=='CLOSED' for i in r['data']['items']}
                require(resolved<=closed, 'PROJECT_SCOPE_UNRESOLVED')
                if excluded:
                    require(d['scope_change_approval_ids'], 'APPROVAL_REQUIRED')
                    for identifier in d['scope_change_approval_ids']:
                        self.check_approval(ref(identifier,'approval'),record,'scope_change')
        if kind=='evidence' and d['authority_state']=='VERIFIED_SOURCE':
            require(self.authority_check is not None and
                    self.authority_check(deepcopy(record),d['asserted_actor_role']) is True, 'TRUSTED_EVIDENCE_REQUIRED')
        if kind=='approval' and d['decision']=='APPROVED':
            self.check_approval(record,record,d['operation'])
        if kind=='rfq':
            vendor=ref(d['vendor_id'],'vendor')['data']
            require(d['recipient'].casefold()==vendor['email'].casefold(), 'CONTACT_MISMATCH')
            if d['status'] in ('READY','SENT','OPEN'):
                require(vendor['status']=='ACTIVE' and vendor['contact_evidence_ids'], 'VENDOR_NOT_READY')
                require(all(ref(i,'boq_item')['data']['status'] in ('READY','ORDERED') for i in d['scope_item_ids']), 'BOQ_NOT_READY')
                require(d['scope_digest']==scope_digest([ref(i,'boq_item') for i in d['scope_item_ids']]), 'STALE_REQUIREMENTS')
            if d['status'] in ('SENT','OPEN'):
                require(d['gmail_message_id'] and d['gmail_thread_ids'] and d['send_action_id'], 'SEND_NOT_CONFIRMED')
        if kind in ('quotation','purchase_order'):
            ids=[i['item_id'] for i in d['items']];require(len(ids)==len(set(ids)), 'DUPLICATE_LINE')
            if kind=='purchase_order' or d['status']=='QUALIFYING':self.financials(d,kind)
        if kind=='quotation' and d['status']=='QUALIFYING':
            rfq=ref(d['rfq_id'],'rfq');rd=rfq['data'];context=project['data']['context']
            require(rfq['revision']==d['rfq_revision'] and rd['scope_digest']==d['scope_digest'] and
                    rd['vendor_id']==d['vendor_id'] and rd['recipient'].casefold()==d['sender'].casefold() and
                    d['source_thread_id'] in rd['gmail_thread_ids'] and rd['status']=='OPEN', 'QUOTE_SCOPE_MISMATCH')
            require(set(ids)==set(rd['scope_item_ids']), 'QUOTE_SCOPE_MISMATCH')
            require(d['scope_digest']==scope_digest([ref(i,'boq_item') for i in ids]), 'STALE_REQUIREMENTS')
            for line in d['items']:
                item=ref(line['item_id'],'boq_item')['data']
                require(item['quantity'] is not None and Decimal(line['quantity'])==Decimal(item['quantity']) and
                        line['unit']==item['unit'], 'QUOTE_SCOPE_MISMATCH')
            require(d['financials']['currency']==rd['comparison_currency']==context['comparison_currency'], 'CURRENCY_MISMATCH')
            require(context['time_zone'] is not None and context['delivery_deadline'] is not None, 'PROJECT_NOT_READY')
            today=self.clock().astimezone(ZoneInfo(context['time_zone'])).date().isoformat()
            require(d['valid_until']>=today and d['delivery_date']<=context['delivery_deadline'] and
                    timestamp(d['received_at'])<=timestamp(rd['quote_deadline']), 'QUOTE_DEADLINE_INVALID')
            require(d['compliance_evidence_ids'], 'COMPLIANCE_EVIDENCE_REQUIRED')
            require(d['compliance_state']=='VERIFIED' or simulation and d['compliance_state']=='SIMULATION_ONLY', 'COMPLIANCE_UNVERIFIED')
            for identifier in d['compliance_evidence_ids']:
                evidence=ref(identifier,'evidence')
                require(simulation and evidence['data']['authority_state']=='SIMULATION_ONLY' or
                        self.authority_check is not None and self.authority_check(deepcopy(evidence),'COMPLIANCE') is True,
                        'COMPLIANCE_UNVERIFIED')
        if kind=='award':
            quote=ref(d['quotation_id'],'quotation')
            require(quote['data']['status']=='QUALIFYING' and quote['revision']==d['quotation_revision'], 'QUOTE_NOT_QUALIFYING')
            self.guards(quote,all_records)
            require(set(d['scope_item_ids'])=={i['item_id'] for i in quote['data']['items']} and
                    d['vendor_id']==quote['data']['vendor_id'] and d['total']['currency']==quote['data']['financials']['currency'] and
                    Decimal(d['total']['amount'])==Decimal(quote['data']['financials']['total_delivered_cost']), 'AWARD_SCOPE_MISMATCH')
            if d['selection_basis']=='LOWEST_QUALIFYING_TOTAL':
                competitors=[r for r in all_records.values() if r['record_type']=='quotation' and
                    r['data']['status']=='QUALIFYING' and r['data']['scope_digest']==quote['data']['scope_digest'] and
                    r['data']['financials']['currency']==d['total']['currency'] and
                    {i['item_id'] for i in r['data']['items']}==set(d['scope_item_ids'])]
                for competitor in competitors:self.guards(competitor,all_records)
                require(len({r['data']['vendor_id'] for r in competitors})>=2, 'SINGLE_OFFER_REQUIRES_EXCEPTION')
                totals=[Decimal(r['data']['financials']['total_delivered_cost']) for r in competitors]
                require(Decimal(d['total']['amount'])==min(totals) and totals.count(min(totals))==1, 'AWARD_RANKING_INVALID')
            if d['status'] in ('APPROVED','SENT'):self.check_approval(all_records.get(d['approval_id']),record,'award_order')
            if d['status']=='SENT':require(d['gmail_message_id'], 'SEND_NOT_CONFIRMED')
        if kind=='purchase_order':
            award=ref(d['award_id'],'award')['data']
            quotation=ref(award['quotation_id'],'quotation')['data']
            require(d['vendor_id']==award['vendor_id'] and set(ids)==set(award['scope_item_ids']) and
                    d['financials']['currency']==award['total']['currency'] and
                    Decimal(d['financials']['total_delivered_cost'])==Decimal(award['total']['amount']), 'ORDER_SCOPE_MISMATCH')
            quoted={i['item_id']:i for i in quotation['items']}
            require(d['financials']==quotation['financials'], 'ORDER_SCOPE_MISMATCH')
            for line in d['items']:
                item=ref(line['item_id'],'boq_item')['data'];q=quoted[line['item_id']]
                require(Decimal(line['ordered_quantity'])==Decimal(q['quantity']) and line['unit']==q['unit'] and
                        Decimal(line['unit_price'])==Decimal(q['unit_price']) and
                        line['specifications']==item['specifications'], 'ORDER_SCOPE_MISMATCH')
            if d['status'] not in ('DRAFT','CANCELLED'):
                require(award['status'] in ('APPROVED','SENT'), 'AWARD_NOT_APPROVED')
            if d['status']=='RELEASED':
                self.guards(ref(d['award_id'],'award'),all_records)
                self.check_approval(all_records.get(d['release_approval_id']),record,'release_po')
                require(d['gmail_message_id'] and d['gmail_thread_ids'] and (simulation or d['payment_terms']), 'RELEASE_NOT_CONFIRMED')
            for line in d['items']:
                quantities=[Decimal(line[k]) for k in ('buyer_accepted_quantity','delivered_quantity','dispatched_quantity','packed_quantity','ordered_quantity')]
                require(quantities==sorted(quantities), 'QUANTITY_ORDER_INVALID')
            progress=None
            for field,full,partial in (('delivered_quantity','DELIVERED','PARTIALLY_DELIVERED'),
                                      ('dispatched_quantity','DISPATCHED','PARTIALLY_DISPATCHED'),
                                      ('packed_quantity','PACKED','PARTIALLY_PACKED')):
                if any(Decimal(i[field])>0 for i in d['items']):
                    progress=full if all(Decimal(i[field])==Decimal(i['ordered_quantity']) for i in d['items']) else partial
                    break
            if d['status'] not in ('CLOSED','ON_HOLD','RESOLUTION_PENDING','CANCELLED'):
                require(progress is None or d['status']==progress, 'AGGREGATE_STATUS_INVALID')
            if d['status'] in ('ACCEPTED','PACKED','PARTIALLY_PACKED','DISPATCHED','PARTIALLY_DISPATCHED','DELIVERED','PARTIALLY_DELIVERED','CLOSED'):
                require(d['supplier_acceptance_confirmed'], 'ACCEPTANCE_REQUIRED')
            for status,key in (('PACKED','packed_quantity'),('DISPATCHED','dispatched_quantity'),('DELIVERED','delivered_quantity'),('CLOSED','buyer_accepted_quantity')):
                if d['status']==status:require(all(Decimal(i[key])==Decimal(i['ordered_quantity']) for i in d['items']), 'INCOMPLETE_QUANTITIES')
            if d['status']=='CLOSED':
                require(d['buyer_confirmation_evidence_ids'], 'BUYER_CONFIRMATION_REQUIRED')
                require(all(self.trusted_evidence(ref(i,'evidence'),'BUYER',simulation) for i in d['buyer_confirmation_evidence_ids']), 'BUYER_CONFIRMATION_REQUIRED')
                confirmations=[r['data'] for r in all_records.values() if r['record_type']=='fulfilment_event' and
                    r['data']['purchase_order_id']==record['record_id'] and r['data']['event_kind']=='BUYER_RECEIPT_CONFIRMED' and
                    r['data']['actor_role']=='BUYER' and r['data']['authority_state'] in
                    (('VERIFIED','SIMULATION_ONLY') if simulation else ('VERIFIED',))]
                sources={ref(i,'evidence')['data']['source_id'] for i in d['buyer_confirmation_evidence_ids']}
                require(any(c['source_message_id'] in sources or c['provider_event_id'] in sources for c in confirmations),
                        'BUYER_CONFIRMATION_REQUIRED')
            if old and old['data']!=d and d['status'] not in ('DRAFT','READY','CANCELLED','ON_HOLD'):
                require(record['evidence_ids'], 'TRANSITION_EVIDENCE_REQUIRED')
                events=[r for r in all_records.values() if r['record_type']=='fulfilment_event' and
                        r['data']['purchase_order_id']==record['record_id']]
                stages=[]
                if d['status']=='ACCEPTED' and old['data']['status']=='RELEASED':stages.append(('ACCEPTED',None))
                for field,stage in (('packed_quantity','PACKED'),('dispatched_quantity','DISPATCHED'),('delivered_quantity','DELIVERED')):
                    before={i['item_id']:i for i in old['data']['items']}
                    if any(Decimal(i[field])>Decimal(before[i['item_id']][field]) for i in d['items']):
                        stages.append((stage,field))
                for stage,field in stages:
                    matching=[]
                    for event in events:
                        ed=event['data']
                        if ed['event_kind']!=stage or ed['actor_role']!='SUPPLIER':continue
                        if ed['authority_state'] not in (('VERIFIED','SIMULATION_ONLY') if simulation else ('VERIFIED',)):continue
                        if not event['evidence_ids'] or not all(self.trusted_evidence(ref(i,'evidence'),'SUPPLIER',simulation)
                                                               for i in event['evidence_ids']):continue
                        reported={i['item_id']:Decimal(i['quantity']) for i in ed['item_quantities']}
                        if field and not all(reported.get(i['item_id'])==Decimal(i[field]) for i in d['items']):continue
                        matching.append(event)
                    require(matching, 'SUPPLIER_EVENT_REQUIRED')
                if any(stage=='DISPATCHED' for stage,field in stages):require(d['tracking_references'], 'TRACKING_REQUIRED')
        if kind=='fulfilment_event':
            order=ref(d['purchase_order_id'],'purchase_order')
            require(set(i['item_id'] for i in d['item_quantities'])<={i['item_id'] for i in order['data']['items']}, 'EVENT_SCOPE_MISMATCH')
            quantities=d['item_quantities'];require(len({i['item_id'] for i in quantities})==len(quantities), 'DUPLICATE_LINE')
            lines={i['item_id']:i for i in order['data']['items']}
            require(all(i['unit']==lines[i['item_id']]['unit'] and Decimal(i['quantity'])<=Decimal(lines[i['item_id']]['ordered_quantity'])
                        for i in quantities), 'EVENT_SCOPE_MISMATCH')
            if d['authority_state'] in ('VERIFIED','SIMULATION_ONLY'):
                require(record['evidence_ids'] and any(ref(i,'evidence')['data']['source_id'] in
                        (d['source_message_id'],d['provider_event_id']) for i in record['evidence_ids']), 'EVENT_SOURCE_MISMATCH')
            if d['authority_state']=='VERIFIED':
                require(record['evidence_ids'] and all(self.trusted_evidence(ref(i,'evidence'),d['actor_role'],simulation)
                        for i in record['evidence_ids']), 'TRUSTED_EVIDENCE_REQUIRED')
            require(simulation or d['authority_state']!='SIMULATION_ONLY', 'SIMULATION_AUTHORITY_DENIED')

    def financials(self, data, kind):
        finance=data['financials'];currency=finance['currency']
        require(currency in self.precision, 'CURRENCY_NOT_CONFIGURED')
        with localcontext() as ctx:
            ctx.prec=60;quantum=Decimal(1).scaleb(-self.precision[currency])
            rounding=lambda n:n.quantize(quantum,rounding=ROUND_HALF_UP)
            for line in data['items']:
                quantity=line['ordered_quantity' if kind=='purchase_order' else 'quantity']
                require(rounding(Decimal(quantity)*Decimal(line['unit_price']))==Decimal(line['line_total']), 'LINE_TOTAL_INVALID')
            require(sum(Decimal(i['line_total']) for i in data['items'])==Decimal(finance['subtotal']), 'SUBTOTAL_INVALID')
            total=Decimal(finance['subtotal'])-Decimal(finance['discount'])+sum(Decimal(finance[k]) for k in ('tax','shipping','other_charges'))
            require(total>=0 and rounding(total)==Decimal(finance['total_delivered_cost']), 'TOTAL_INVALID')

    def commit(self, workspace, project, key, changes, *, resources=(), sync_intents=()):
        """Atomically apply [{record, expected_revision}] and projection intentions."""
        self.scope(workspace,project)
        require(isinstance(key,str) and 1<=len(key)<=255, 'TRANSACTION_KEY_INVALID')
        changes=deepcopy(changes);resources=deepcopy(list(resources));sync_intents=deepcopy(list(sync_intents))
        require(isinstance(changes,list) and 1<=len(changes)<=1000, 'TRANSACTION_BOUNDS')
        fingerprint=hashlib.sha256(encoded([changes,resources,sync_intents]).encode()).hexdigest()
        with self.connection() as db:
            db.execute('BEGIN IMMEDIATE')
            replay=db.execute('SELECT fingerprint,result FROM transactions WHERE workspace=? AND project=? AND key=?',
                              (workspace,project,key)).fetchone()
            if replay:
                require(replay[0]==fingerprint, 'TRANSACTION_KEY_MISMATCH')
                return json.loads(replay[1])
            current={r['record_id']:r for r in (json.loads(row[0]) for row in db.execute(
                'SELECT body FROM records WHERE workspace=? AND project=?',(workspace,project)))}
            old=deepcopy(current);seen=set()
            for change in changes:
                require(isinstance(change,dict) and set(change)=={'record','expected_revision'}, 'CHANGE_INVALID')
                record=change['record'];require(not list(self.validator.iter_errors(record)), 'RECORD_SCHEMA_INVALID')
                require(record['workspace_id']==workspace and record['project_id']==project, 'SCOPE_MISMATCH')
                identifier=record['record_id'];require(identifier not in seen, 'DUPLICATE_CHANGE');seen.add(identifier)
                previous=old.get(identifier);expected=change['expected_revision']
                require(type(expected) is int and expected==(previous['revision'] if previous else 0) and
                        record['revision']==expected+1, 'REVISION_CONFLICT')
                require(timestamp(record['created_at'])<=timestamp(record['updated_at']), 'TIMESTAMP_INVALID')
                self.transition(previous,record);current[identifier]=record
            for change in changes:self.guards(change['record'],current,old.get(change['record']['record_id']))
            # Current dependencies are rechecked at selection/release. Revocation and
            # new source facts remain recordable even when they invalidate an old approval.
            now=self.clock().isoformat()
            for change in changes:
                r=change['record'];identity=(workspace,project,r['record_id']);body=encoded(r)
                db.execute('INSERT INTO records VALUES (?,?,?,?,?,?) ON CONFLICT(workspace,project,id) '
                           'DO UPDATE SET revision=excluded.revision,body=excluded.body',(*identity,r['record_type'],r['revision'],body))
                db.execute(f'INSERT INTO {TABLES[r["record_type"]]} VALUES (?,?,?,?) ON CONFLICT(workspace,project,id) '
                           'DO UPDATE SET body=excluded.body',(*identity,body))
                db.execute('INSERT INTO revisions VALUES (?,?,?,?,?)',(*identity,r['revision'],body))
                db.execute('INSERT INTO activity(workspace,project,transaction_key,record_id,revision,recorded_at) VALUES (?,?,?,?,?,?)',
                           (workspace,project,key,r['record_id'],r['revision'],now))
                d=r['data'];unique=[]
                if r['record_type']=='purchase_order':unique.append(('po_number',d['po_number']))
                if r['record_type']=='fulfilment_event':unique.append(('event',d['idempotency_key']))
                if r['record_type']=='quotation':unique.append(('quote_message',d['vendor_id']+':'+d['source_message_id']))
                if r['record_type']=='rfq' and r['revision']==1:unique.append(('rfq_scope',encoded([d['vendor_id'],d['scope_digest']])))
                if r['record_type']=='evidence':unique.append(('evidence',encoded([d['provider'],d['source_id'],d['locator'],d['content_sha256']])))
                for category,value in unique:
                    existing=db.execute('SELECT record_id FROM unique_refs WHERE workspace=? AND project=? AND category=? AND value=?',
                                        (workspace,project,category,value)).fetchone()
                    require(not existing or existing[0]==r['record_id'], 'DUPLICATE_SOURCE')
                    db.execute('INSERT OR IGNORE INTO unique_refs VALUES (?,?,?,?,?)',(workspace,project,category,value,r['record_id']))
            for link in resources:
                require(set(link)=={'record_id','provider','resource_type','resource_id','metadata'} and
                        link['record_id'] in current and link['provider'] in ('google_sheets','gmail','google_calendar') and
                        link['resource_type'] in ('spreadsheet','tab','message','thread','event') and
                        isinstance(link['resource_id'],str) and 1<=len(link['resource_id'])<=4096 and
                        isinstance(link['metadata'],dict), 'RESOURCE_LINK_INVALID')
                require(link['resource_type'] in {'google_sheets':('spreadsheet','tab'),
                        'gmail':('message','thread'),'google_calendar':('event',)}[link['provider']], 'RESOURCE_LINK_INVALID')
                prior=db.execute('SELECT metadata FROM resources WHERE workspace=? AND project=? AND record_id=? AND provider=? AND resource_type=? AND resource_id=?',
                                 (workspace,project,link['record_id'],link['provider'],link['resource_type'],link['resource_id'])).fetchone()
                require(not prior or prior[0]==encoded(link['metadata']), 'RESOURCE_LINK_CONFLICT')
                db.execute('INSERT OR IGNORE INTO resources VALUES (?,?,?,?,?,?,?)',
                           (workspace,project,link['record_id'],link['provider'],link['resource_type'],link['resource_id'],encoded(link['metadata'])))
            for intent in sync_intents:
                require(set(intent)=={'key','record_id','record_revision','target','payload'} and
                        isinstance(intent['key'],str) and 1<=len(intent['key'])<=255 and
                        intent['record_id'] in current and current[intent['record_id']]['revision']==intent['record_revision'] and
                        intent['target'] in ('sheets','calendar','gmail') and isinstance(intent['payload'],dict), 'SYNC_INTENT_INVALID')
                require(not db.execute('SELECT 1 FROM sync_intents WHERE workspace=? AND project=? AND key=?',
                                       (workspace,project,intent['key'])).fetchone(), 'SYNC_KEY_CONFLICT')
                db.execute('INSERT INTO sync_intents VALUES (?,?,?,?,?,?,?,?)',
                           (workspace,project,intent['key'],intent['record_id'],intent['record_revision'],intent['target'],encoded(intent['payload']),'PENDING_APPROVAL'))
            result={'workspace_id':workspace,'project_id':project,'transaction_key':key,
                    'revisions':{c['record']['record_id']:c['record']['revision'] for c in changes}}
            db.execute('INSERT INTO transactions VALUES (?,?,?,?,?)',(workspace,project,key,fingerprint,encoded(result)))
        return result
