"""Metadata-only explanations derived from validated read plans."""
from .data_query_engine import expression


def dataset_label(dataset):
    connection = dataset['connection']
    return ' / '.join(str(part) for part in (
        connection['name'], dataset.get('database'), dataset.get('schema'), dataset['name']
    ) if part is not None and part != '')


def selection_preview(plan, context, needed, joins, mappings):
    graph, datasets, fields, relationships = context
    if plan['clarification']:
        return dict(catalog_dataset_count=len(datasets), sources=[], relationships=[],
                    business_mappings=[], warnings=graph['warnings'])
    uses = {}

    def mark(fid, purpose):
        uses.setdefault(fid, set()).add(purpose)

    for fid in plan['fields']:
        mark(fid, 'output')
    for item in plan['filters']:
        mark(item['field_id'], 'filter')
    for fid in plan['group_by']:
        mark(fid, 'group')
    for metric in plan['metrics']:
        if metric['expression']:
            for fid in expression(metric['expression'], set(fields))[1]:
                mark(fid, 'metric')
    selected_edges = []
    for target, pairs, rid in joins:
        for left, right in pairs:
            mark(left, 'join')
            mark(right, 'join')
        selected_edges.append(dict(
            relationship_id=rid,
            source_dataset_id=fields[pairs[0][0]]['dataset_id'],
            target_dataset_id=target,
            status=relationships[rid]['status'],
            field_pairs=[dict(source_field_id=a, target_field_id=b) for a, b in pairs],
        ))
    selected = []
    reason_text = dict(output='Provides requested output fields.', filter='Provides filter fields.',
                       group='Provides grouping fields.', metric='Provides calculation fields.',
                       join='Provides keys required to link selected datasets.',
                       row_count='Supplies rows for evaluation; an enumeration field is required.')
    for did, required in needed.items():
        dataset = datasets[did]
        label = dataset_label(dataset)
        selected_fields = [dict(field_id=f['field_id'], label=label+' / '+f['name'],
                                types=f['types'], purposes=sorted(uses.get(f['field_id'], {'row_count'})))
                           for f in required]
        purposes = {purpose for field in selected_fields for purpose in field['purposes']}
        selected.append(dict(dataset_id=did, connection_id=dataset['connection']['connection_id'],
                             engine=dataset['connection']['engine'], label=label,
                             reasons=[('Base dataset in the validated plan.' if did == plan['base_dataset_id']
                                       else 'Join target in the validated plan.'),
                                      *(reason_text[p] for p in sorted(purposes))],
                             fields=selected_fields))
    selected_ids = set(needed) | {f['field_id'] for source in selected for f in source['fields']}
    return dict(catalog_dataset_count=len(datasets), sources=selected, relationships=selected_edges,
                business_mappings=[m for m in mappings if m['node_id'] in selected_ids],
                warnings=graph['warnings'])
