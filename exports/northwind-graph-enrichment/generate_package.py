"""Regenerate the deterministic synthetic demo package. Does not connect to a database."""
from pathlib import Path
import csv, json, hashlib
ROOT=Path(__file__).resolve().parent
CSV=ROOT/'csv'; CSV.mkdir(exist_ok=True)
SCHEMA='northwind_graph_demo'
NOTE='SYNTHETIC graph demonstration only; not operational evidence.'
tables=[]
def add(name, columns, rows, refs=(), checks=()):
    columns=[*columns,('is_demo','boolean NOT NULL DEFAULT true CHECK (is_demo)'),('provenance','text NOT NULL')]
    rows=[[*row,True,NOTE] for row in rows]
    tables.append(dict(name=name,columns=columns,rows=rows,refs=list(refs),checks=list(checks)))
regions=['British Isles','Western Europe','Northern Europe','Mediterranean','East Asia','South Asia','North America','Oceania']
protocols=['Ambient dry handling','Chilled handling','Frozen handling','Fragile handling','Moisture barrier handling','Aroma protection','Light protection','Clean sealed handling']
add('business_regions',[('region_id','integer PRIMARY KEY'),('region_name','text NOT NULL UNIQUE')],[(i+1,n) for i,n in enumerate(regions)])
add('facility_types',[('facility_type_id','integer PRIMARY KEY'),('facility_type_name','text NOT NULL UNIQUE')],[(i+1,n) for i,n in enumerate(['Consolidation hub','Packing site','Distribution centre','Cold storage site','Inspection site'])])
add('handling_protocols',[('protocol_id','integer PRIMARY KEY'),('protocol_name','text NOT NULL UNIQUE'),('handling_description','text NOT NULL')],[(i+1,n,'Illustrative handling classification: '+n.lower()) for i,n in enumerate(protocols)])
add('packaging_materials',[('material_id','integer PRIMARY KEY'),('material_name','text NOT NULL UNIQUE')],[(i+1,n) for i,n in enumerate(['Corrugated board','Glass','Aluminium','Paper fibre','Reusable polymer','Barrier film','Wood fibre','Moulded pulp'])])
add('packaging_profiles',[('packaging_id','integer PRIMARY KEY'),('packaging_name','text NOT NULL'),('material_id','integer NOT NULL'),('protocol_id','integer NOT NULL')],[(i,f'Demo Packaging Profile {i:02d}',(i-1)%8+1,(i-1)%8+1) for i in range(1,25)],[('material_id','packaging_materials','material_id','uses packaging material'),('protocol_id','handling_protocols','protocol_id','follows handling protocol')])
add('certification_standards',[('standard_id','integer PRIMARY KEY'),('standard_name','text NOT NULL UNIQUE'),('protocol_id','integer NOT NULL')],[(i,f'DEMO-STD-{i:02d}',(i-1)%8+1) for i in range(1,11)],[('protocol_id','handling_protocols','protocol_id','documents handling protocol')])
add('transport_modes',[('mode_id','integer PRIMARY KEY'),('mode_name','text NOT NULL UNIQUE')],[(i+1,n) for i,n in enumerate(['Road','Rail','Sea','Air','Intermodal'])])
families=['Beverage containers','Dry goods cartons','Dairy containers','Frozen food packs','Confectionery packs','Seafood containers','Grain sacks','Produce crates','Spice containers','Sauce containers','Preserve jars','Gift assortments']
add('material_families',[('family_id','integer PRIMARY KEY'),('family_name','text NOT NULL UNIQUE'),('protocol_id','integer NOT NULL')],[(i+1,n,i%8+1) for i,n in enumerate(families)],[('protocol_id','handling_protocols','protocol_id','requires handling protocol')])
add('supplier_sites',[('site_id','integer PRIMARY KEY'),('site_name','text NOT NULL UNIQUE'),('region_id','integer NOT NULL'),('facility_type_id','integer NOT NULL'),('protocol_id','integer NOT NULL')],[(i,f'Demo Supplier Site {i:03d}',(i-1)%8+1,(i-1)%5+1,(i-1)%8+1) for i in range(1,49)],[('region_id','business_regions','region_id','is located in region'),('facility_type_id','facility_types','facility_type_id','has facility type'),('protocol_id','handling_protocols','protocol_id','uses handling protocol')])
add('warehouses',[('warehouse_id','integer PRIMARY KEY'),('warehouse_name','text NOT NULL UNIQUE'),('region_id','integer NOT NULL'),('facility_type_id','integer NOT NULL'),('protocol_id','integer NOT NULL')],[(i,f'Demo Warehouse {i:03d}',(i-1)%8+1,(i-1)%5+1,(i-1)%8+1) for i in range(1,25)],[('region_id','business_regions','region_id','is located in region'),('facility_type_id','facility_types','facility_type_id','has facility type'),('protocol_id','handling_protocols','protocol_id','uses handling protocol')])
add('inspection_checklists',[('checklist_id','integer PRIMARY KEY'),('checklist_name','text NOT NULL UNIQUE'),('standard_id','integer NOT NULL'),('protocol_id','integer NOT NULL')],[(i,f'Demo Checklist {i:03d}',(i-1)%10+1,((i-1)%10)%8+1) for i in range(1,33)],[('standard_id','certification_standards','standard_id','checks illustrative standard'),('protocol_id','handling_protocols','protocol_id','inspects handling protocol')])
add('distribution_lanes',[('lane_id','integer PRIMARY KEY'),('lane_name','text NOT NULL UNIQUE'),('origin_region_id','integer NOT NULL'),('destination_region_id','integer NOT NULL'),('mode_id','integer NOT NULL'),('protocol_id','integer NOT NULL')],[(i,f'Demo Distribution Lane {i:03d}',(i-1)%8+1,((i-1)%8+(i-1)//8%7+1)%8+1,(i-1)%5+1,(i-1)%8+1) for i in range(1,73)],[('origin_region_id','business_regions','region_id','starts in region'),('destination_region_id','business_regions','region_id','ends in region'),('mode_id','transport_modes','mode_id','uses transport mode'),('protocol_id','handling_protocols','protocol_id','follows handling protocol')],['CHECK (origin_region_id <> destination_region_id)'])
add('site_certifications',[('site_certification_id','integer PRIMARY KEY'),('site_id','integer NOT NULL'),('standard_id','integer NOT NULL'),('checklist_id','integer NOT NULL'),('claim_status',"text NOT NULL CHECK (claim_status = 'illustrative_only')")],[(i,(i-1)//3+1,(i-1)%10+1,(i-1)%10+1,'illustrative_only') for i in range(1,145)],[('site_id','supplier_sites','site_id','describes supplier site'),('standard_id','certification_standards','standard_id','references illustrative standard'),('checklist_id','inspection_checklists','checklist_id','uses inspection checklist')])
add('warehouse_capabilities',[('capability_id','integer PRIMARY KEY'),('warehouse_id','integer NOT NULL'),('protocol_id','integer NOT NULL'),('checklist_id','integer NOT NULL')],[(i,(i-1)//4+1,((i-1)%32%10)%8+1,(i-1)%32+1) for i in range(1,97)],[('warehouse_id','warehouses','warehouse_id','describes warehouse'),('protocol_id','handling_protocols','protocol_id','supports handling protocol'),('checklist_id','inspection_checklists','checklist_id','is described by checklist')])
add('material_packaging_rules',[('rule_id','integer PRIMARY KEY'),('family_id','integer NOT NULL'),('packaging_id','integer NOT NULL'),('protocol_id','integer NOT NULL')],[(i,(i-1)//8+1,(i-1)%24+1,(i-1)%8+1) for i in range(1,97)],[('family_id','material_families','family_id','applies to material family'),('packaging_id','packaging_profiles','packaging_id','specifies packaging profile'),('protocol_id','handling_protocols','protocol_id','follows handling protocol')])
lanes=tables[11]['rows']
assignments=[]
for i in range(1,145):
    lane=lanes[(i-1)%72]; origin,dest=lane[2:4]
    site=origin+8*((i-1)//8%6); warehouse=dest+8*((i-1)//8%3)
    assignments.append((i,lane[0],site,warehouse))
add('lane_site_assignments',[('assignment_id','integer PRIMARY KEY'),('lane_id','integer NOT NULL'),('site_id','integer NOT NULL'),('warehouse_id','integer NOT NULL')],assignments,[('lane_id','distribution_lanes','lane_id','assigns distribution lane'),('site_id','supplier_sites','site_id','originates at supplier site'),('warehouse_id','warehouses','warehouse_id','serves warehouse')])
add('site_material_approvals',[('approval_id','integer PRIMARY KEY'),('site_id','integer NOT NULL'),('family_id','integer NOT NULL'),('standard_id','integer NOT NULL'),('approval_status',"text NOT NULL CHECK (approval_status = 'illustrative_only')")],[(i,(i-1)//4+1,(i-1)%12+1,(i-1)%10+1,'illustrative_only') for i in range(1,193)],[('site_id','supplier_sites','site_id','describes supplier site'),('family_id','material_families','family_id','classifies material family'),('standard_id','certification_standards','standard_id','references illustrative standard')])
# Cross-check deterministic CSV references before emitting artifacts.
by_name={t['name']:t for t in tables}
for t in tables:
    names=[c[0] for c in t['columns']]
    assert len({r[0] for r in t['rows']})==len(t['rows'])
    for col,target,key,label in t['refs']:
        dest=by_name[target];target_index=[c[0] for c in dest['columns']].index(key)
        allowed={r[target_index] for r in dest['rows']}
        assert all(r[names.index(col)] in allowed for r in t['rows'])
    with (CSV/(t['name']+'.csv')).open('w',newline='',encoding='utf-8') as f:
        w=csv.writer(f); w.writerow(names);w.writerows(t['rows'])
header="-- Synthetic graph-only demonstration package. Never an operational source.\nSET LOCAL lock_timeout = '2s';\nSET LOCAL statement_timeout = '60s';\nSET LOCAL standard_conforming_strings = on;\n"
schema=header+f'CREATE SCHEMA {SCHEMA};\n'+f"COMMENT ON SCHEMA {SCHEMA} IS '{NOTE}';\n"
for t in tables:
    defs=[f'  {n} {typ}' for n,typ in t['columns']]
    defs += [f'  FOREIGN KEY ({col}) REFERENCES {SCHEMA}.{target} ({key})' for col,target,key,label in t['refs']]
    defs += ['  '+s for s in t['checks']]
    schema+=f"\nCREATE TABLE {SCHEMA}.{t['name']} (\n"+',\n'.join(defs)+'\n);\n'
    schema+=f"COMMENT ON TABLE {SCHEMA}.{t['name']} IS '{NOTE}';\n"
    for col,target,key,label in t['refs']:
        schema+=f'CREATE INDEX ON {SCHEMA}.{t["name"]} ({col});\n'
(ROOT/'01_create_schema.sql').write_text('-- Run inside a transaction; the import scripts do this automatically.\n'+schema)
checks="-- Raises an exception on wrong row counts, flags or unvalidated constraints.\nDO $check$\nBEGIN\n"
for t in tables:
    table=f'{SCHEMA}.{t["name"]}';n=len(t['rows'])
    checks+=f" IF (SELECT count(*) FROM {table}) <> {n} THEN RAISE EXCEPTION 'Unexpected row count: {t['name']}'; END IF;\n"
    checks+=f" IF EXISTS (SELECT 1 FROM {table} WHERE NOT is_demo OR provenance <> '{NOTE}') THEN RAISE EXCEPTION 'Bad demo provenance: {t['name']}'; END IF;\n"
fk=sum(len(t['refs']) for t in tables)
checks+=f" IF (SELECT count(*) FROM pg_constraint c JOIN pg_namespace n ON n.oid=c.connamespace WHERE n.nspname='{SCHEMA}' AND c.contype='f' AND c.convalidated) <> {fk} THEN RAISE EXCEPTION 'Unexpected validated foreign key count'; END IF;\nEND;\n$check$;\n"
checks+='\nUNION ALL\n'.join(f"SELECT '{t['name']}' AS table_name, count(*) AS row_count FROM {SCHEMA}.{t['name']}" for t in tables)+';\n'
(ROOT/'04_validate.sql').write_text(checks)
imports='\\set ON_ERROR_STOP on\nBEGIN;\n\\ir 01_create_schema.sql\n'
for t in tables:
    names=', '.join(c[0] for c in t['columns'])
    imports+=f"\\copy {SCHEMA}.{t['name']} ({names}) FROM 'csv/{t['name']}.csv' WITH (FORMAT csv, HEADER true, ENCODING 'UTF8')\n"
imports+='\\ir 04_validate.sql\nCOMMIT;\n'
(ROOT/'03_import_all.psql').write_text(imports)
def literal(v):
    if isinstance(v,bool): return 'true' if v else 'false'
    if isinstance(v,int): return str(v)
    return "'"+str(v).replace("'","''")+"'"
all_sql='-- SQL-editor alternative. Run this entire file as one batch, once.\nBEGIN;\n'+schema
for t in tables:
    names=', '.join(c[0] for c in t['columns'])
    all_sql+=f"\nINSERT INTO {SCHEMA}.{t['name']} ({names}) VALUES\n"+',\n'.join('('+', '.join(map(literal,r))+')' for r in t['rows'])+';\n'
all_sql+='\n'+checks+'\nCOMMIT;\n'
(ROOT/'02_setup_and_load_sql_editor.sql').write_text(all_sql)
remove='-- OPTIONAL: removes only this demo schema. No CASCADE, no original tables.\nBEGIN;\n'+header
for t in reversed(tables):remove+=f'DROP TABLE {SCHEMA}.{t["name"]};\n'
remove+=f'DROP SCHEMA {SCHEMA};\nCOMMIT;\n'
(ROOT/'90_remove_demo_schema.sql').write_text(remove)
with (ROOT/'relationship_guide.csv').open('w',newline='') as f:
    w=csv.writer(f);w.writerow(['source_table','source_column','target_table','target_column','suggested_business_label'])
    for t in tables:
        for c,d,k,l in t['refs']:w.writerow([t['name'],c,d,k,l])
manifest=dict(schema=SCHEMA,synthetic=True,table_count=len(tables),row_count=sum(len(t['rows']) for t in tables),declared_foreign_keys=fk,original_tables_modified=[],tables=[dict(name=t['name'],csv='csv/'+t['name']+'.csv',rows=len(t['rows']),columns=[c[0] for c in t['columns']],foreign_keys=len(t['refs'])) for t in tables])
(ROOT/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
print(json.dumps({k:v for k,v in manifest.items() if k!='tables'},indent=2))
