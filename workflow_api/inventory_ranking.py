"""Bounded local arithmetic for stock evidence; never queries or changes a database."""
from math import isfinite
from connector_extension.catalog import definition, obj, CATALOG
from connector_extension.common import Connector, denied

RISK = obj({'finding': {'type': 'string', 'maxLength': 2000}, 'source_url': {'type': 'string', 'pattern': '^https?://', 'maxLength': 2000}}, ['finding','source_url'])
NUMBER = {'type': 'number', 'minimum': 0, 'maximum': 1e12}
RECORD = obj({
    'product_id': {'type': 'string', 'minLength': 1, 'maxLength': 200},
    'product_name': {'type': 'string', 'minLength': 1, 'maxLength': 500},
    'category': {'type': 'string', 'maxLength': 500},
    'supplier': {'type': 'string', 'maxLength': 500},
    'units_in_stock': NUMBER, 'units_on_order': NUMBER, 'reorder_level': NUMBER,
    'discontinued': {'type': 'boolean'}},
    ['product_id', 'product_name', 'category', 'supplier', 'units_in_stock',
     'units_on_order', 'reorder_level', 'discontinued'])
RANKED = obj({**RECORD['properties'], 'stock_position': {'type': 'number', 'minimum': 0, 'maximum': 2e12}, 'shortage': NUMBER},
             [*RECORD['required'], 'stock_position', 'shortage'])
TOOL = definition('extension_inventory_rank', 'builder_analysis', 'inventory.rank_restock',
    'Rank actual normalized stock evidence deterministically: stock_position=units_in_stock+units_on_order; '
    'shortage=max(reorder_level-stock_position,0). Exclude discontinued products; distinguish confirmed shortages from zero-shortage watchlist candidates. '
    'Sort confirmed shortages first, shortage descending, stock/reorder coverage ascending, stock_position ascending, product_id ascending; return at most five. '
    'Never infer missing quantities or fabricate rows. No database reads/writes.',
    obj({'records': {'type': 'array', 'maxItems': 1000, 'items': RECORD},
         'limited': {'type': 'boolean'}, 'external_risks': {'type': 'array', 'maxItems': 20, 'items': RISK}}, ['records', 'limited']),
    obj({'ranked_products': {'type': 'array', 'maxItems': 5, 'items': RANKED},
         'reviewed_records': {'type': 'integer'}, 'shortage_count': {'type': 'integer'},
         'limited': {'type': 'boolean'}, 'ranking_rule': {'type': 'string'},
         'tabs': CATALOG['extension_sheets_create_report']['input_schema']['properties']['tabs'],
         'summary': {'type': 'string', 'maxLength': 30000}},
        ['ranked_products', 'reviewed_records', 'shortage_count', 'limited', 'ranking_rule', 'tabs', 'summary']),
    [], 'workflow.read_input')
TOOL['authentication'] = {'mode': 'none', 'credential_reference_required': False, 'scopes': []}


def rank_inventory(records, limited=False, external_risks=()):
    seen, ranked = set(), []
    for record in records:
        identifier = record['product_id']
        if identifier in seen:
            denied('INVENTORY_EVIDENCE_AMBIGUOUS', 'Duplicate product identities require a corrected evidence query.', 422)
        seen.add(identifier)
        quantities = [record[k] for k in ('units_in_stock', 'units_on_order', 'reorder_level')]
        if any(type(n) not in (int, float) or not isfinite(n) or n < 0 or n > 1e12 for n in quantities):
            denied('INVENTORY_EVIDENCE_INVALID', 'Use finite nonnegative actual quantities; do not estimate missing stock.', 422)
        stock = record['units_in_stock'] + record['units_on_order']
        shortage = max(record['reorder_level'] - stock, 0)
        if not record['discontinued']:
            ranked.append({**record, 'stock_position': stock, 'shortage': shortage})
    from fractions import Fraction
    shortage_count = sum(r['shortage'] > 0 for r in ranked)
    ranked.sort(key=lambda r: (r['shortage'] <= 0, -r['shortage'],
        Fraction(str(r['stock_position'])) / Fraction(str(r['reorder_level'])) if r['reorder_level'] else float('inf'),
        r['stock_position'], r['product_id']))
    top = ranked[:5]
    headers = ['Product ID','Product','Category','Supplier','In stock','Already on order','Reorder level','Stock position','Shortage','Ranking reason']
    rows = [[r['product_id'],r['product_name'],r['category'],r['supplier'],r['units_in_stock'],r['units_on_order'],
             r['reorder_level'],r['stock_position'],r['shortage'],
             'Confirmed shortage after including stock on order' if r['shortage'] > 0 else 'Watchlist only: no confirmed shortage after including stock on order'] for r in top]
    if not rows: rows = [['No active products returned','','','',None,None,None,None,None,'No shortages found in the retrieved evidence']]
    notes = f'Reviewed {len(records)} records; {shortage_count} active products have confirmed shortages; showing {len(top)} review candidates. Zero-shortage candidates are watchlist only.'
    if limited: notes += ' Coverage is incomplete: ranking covers retrieved records only.'
    summary = notes + '\nStock position = stock + already on order. Shortage = max(reorder level - stock position, 0).'
    for r in top:
        summary += f"\n{r['product_name']}: stock {r['units_in_stock']}, on order {r['units_on_order']}, reorder {r['reorder_level']}, shortage {r['shortage']}; {r['category']}; {r['supplier']}."
    summary += f'\nExternal findings: {len(external_risks)}. See the separate External risks tab and its source links; these are separate from inventory facts.'
    risk_rows = [[r['finding'],r['source_url'],'External evidence; not an inventory fact'] for r in external_risks]
    if not risk_rows: risk_rows = [['No supported external findings returned','','No external claims made']]
    tabs = [{'title':'Inventory','headers':headers,'rows':rows},
            {'title':'External risks','headers':['Finding','Source URL','Evidence type'],'rows':risk_rows},
            {'title':'Method and coverage','headers':['Metric','Value'],'rows':[
                ['Reviewed records',len(records)],['Active products with shortages',shortage_count],['Coverage limited',limited],
                ['Ranking rule','Confirmed shortages first, shortage descending, stock/reorder coverage ascending, stock position ascending, product ID ascending; discontinued excluded'],
                ['Coverage note',notes]]}]
    return dict(ranked_products=top, reviewed_records=len(records), shortage_count=shortage_count, limited=limited,
                ranking_rule='confirmed shortages first, shortage descending, stock/reorder coverage ascending, stock position ascending, product ID ascending; discontinued excluded',
                tabs=tabs, summary=summary)


class InventoryRank(Connector):
    def execute(self, grant, inputs, effect_id, deadline):
        return rank_inventory(inputs['records'], inputs['limited'], inputs.get('external_risks', []))


DELIVERY = definition('extension_report_delivery', 'builder_analysis', 'inventory.prepare_delivery',
    'Prepare report delivery deterministically from a verified created spreadsheet URL, stock summary and exact approved times. No external action.',
    obj({'spreadsheet_url': {'type': 'string', 'pattern': '^https://docs\\.google\\.com/spreadsheets/d/[A-Za-z0-9_-]+/edit$', 'maxLength': 2000},
         'summary': {'type': 'string', 'maxLength': 30000}, 'start': {'type': 'string', 'maxLength': 50},
         'end': {'type': 'string', 'maxLength': 50}}, ['spreadsheet_url','summary','start','end']),
    obj({'subject': {'type': 'string'}, 'body': {'type': 'string'},
         'event': CATALOG['extension_calendar_create']['input_schema']['properties']['event']}, ['subject','body','event']),
    [], 'workflow.read_input')
DELIVERY['authentication'] = {'mode': 'none', 'credential_reference_required': False, 'scopes': []}


class ReportDelivery(Connector):
    def execute(self, grant, inputs, effect_id, deadline):
        from datetime import datetime
        try:
            start,end = datetime.fromisoformat(inputs['start']),datetime.fromisoformat(inputs['end'])
            if not start.utcoffset() or not end.utcoffset() or not 0 < (end-start).total_seconds() <= 8*3600: raise ValueError()
        except ValueError:
            denied('REPORT_MEETING_TIME_REQUIRED','Use a bounded meeting with explicit time zones.',422)
        body = inputs['summary'] + '\n\nReport: ' + inputs['spreadsheet_url']
        return {'subject':'Inventory restocking review','body':body,'event':{'summary':'Inventory restocking review',
            'description':body,'start':{'dateTime':inputs['start'],'timeZone':'Asia/Kolkata'},
            'end':{'dateTime':inputs['end'],'timeZone':'Asia/Kolkata'}}}


NORMALIZE = definition('extension_inventory_normalize', 'builder_analysis', 'inventory.normalize_evidence',
    'Normalize actual query rows using exact KG field IDs. Reject missing/invalid quantities and identities; never estimate records.',
    obj({'rows': {'type':'array','maxItems':500,'items':{'type':'object'}},
         'field_map_json': {'type':'string','maxLength':5000}, 'limited':{'type':'boolean'}}, ['rows','field_map_json','limited']),
    obj({'records': {'type':'array','maxItems':500,'items':RECORD},'limited':{'type':'boolean'}}, ['records','limited']),
    [], 'workflow.read_input')
NORMALIZE['authentication'] = {'mode':'none','credential_reference_required':False,'scopes':[]}


class InventoryNormalize(Connector):
    def execute(self,grant,inputs,effect_id,deadline):
        import json
        try:
            mapping=json.loads(inputs['field_map_json'])
            if set(mapping)!=set(RECORD['required']) or any(not isinstance(v,str) for v in mapping.values()):raise ValueError()
            records=[]
            for row in inputs['rows']:
                record={key:row[field] for key,field in mapping.items()}
                if type(record['product_id']) not in (str,int) or isinstance(record['product_id'],bool):raise ValueError()
                record['product_id']=str(record['product_id'])
                flag=record['discontinued']
                if type(flag) is bool:pass
                elif type(flag) is int and flag in (0,1):flag=bool(flag)
                elif isinstance(flag,str) and flag.lower() in ('true','false','0','1'):flag=flag.lower() in ('true','1')
                else:raise ValueError()
                record['discontinued']=flag
                for key in ('category','supplier'):
                    if record[key] is None:record[key]='Not recorded'
                records.append(record)
        except (ValueError,KeyError,TypeError):
            denied('INVENTORY_EVIDENCE_INVALID','The returned evidence lacks exact stock fields or scalar identities.',422)
        return {'records':records,'limited':inputs['limited']}
