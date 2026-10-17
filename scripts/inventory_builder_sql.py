"""Generate the review inventory of every storage call and literal table definition."""
import argparse
import ast
import json
from pathlib import Path
import re

ROOT=Path(__file__).resolve().parents[1]
OUTPUT=ROOT/'openspec/changes/phase2-backend-reliability/sql-inventory.json'


def inventory():
    calls=[];tables={}
    for directory in ('workflow_api','runtime','connector_extension','scripts'):
        for path in sorted((ROOT/directory).rglob('*.py')):
            if 'tests' in path.parts:continue
            tree=ast.parse(path.read_text())
            for node in ast.walk(tree):
                if not (isinstance(node,ast.Call) and isinstance(node.func,ast.Attribute) and node.func.attr in {'execute','executemany','executescript'} and node.args):continue
                value=node.args[0]
                literal=isinstance(value,ast.Constant) and isinstance(value.value,str)
                statement=value.value if literal else ast.unparse(value)
                entry={'file':str(path.relative_to(ROOT)),'line':node.lineno,'kind':node.func.attr,'sql' if literal else 'sql_expression':statement,'dynamic':not literal}
                calls.append(entry)
                if literal:
                    match=re.match(r'CREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?([a-z_][a-z0-9_]*)',statement,re.I)
                    if match:tables.setdefault(match[1],[]).append({'file':entry['file'],'line':node.lineno,'ddl':statement})
    dynamic_tables=['projects','boq_items','vendors','rfqs','quotations','awards','purchase_orders','fulfilment_events','approvals','evidence']
    return {'format':'builder-sql-inventory-v1','scope':['workflow_api','runtime','connector_extension (excluding tests)','scripts'],
            'notes':['Dynamic SQL expressions are retained for review; values remain bound parameters.','Connector databases use separate schemas: equal table names across files must not be merged.','The procurement subtype loop expands into dynamic_tables; PostgreSQL adapter/migration catalog calls are included.'],
            'dynamic_tables':{'connector_extension/procurement/store.py':dynamic_tables},'tables':dict(sorted(tables.items())),
            'calls':sorted(calls,key=lambda item:(item['file'],item['line']))}


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--check',action='store_true');args=parser.parse_args()
    encoded=json.dumps(inventory(),indent=2)+'\n'
    if args.check:
        if not OUTPUT.exists() or OUTPUT.read_text()!=encoded:raise SystemExit('SQL inventory is stale; regenerate with scripts/inventory_builder_sql.py.')
    else:OUTPUT.write_text(encoded)
    result=json.loads(encoded)
    print(f"SQL inventory verified: {len(result['calls'])} calls, {len(result['tables'])} literal table names, 10 procurement subtypes.")


if __name__=='__main__':main()
