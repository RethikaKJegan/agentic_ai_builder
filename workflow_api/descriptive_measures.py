"""Typed descriptive metrics do not establish an approved business definition."""

GUIDANCE = (' For descriptive counts, totals, averages and other summaries, multiple plausible '
    'recorded numeric measures are not by themselves a blocking business ambiguity. '
    'Apply supplied definitions and explicitly selected analytical defaults first. '
    'If neither those definitions nor the user select a basis, preserve each supported candidate as separately '
    'named statistics at the same source grain and grouping. Use business_resolution '
    'status descriptive_measures with exact base_dataset_id, group_by field IDs and every '
    'requested op/field_id metric pair, including count with empty field_id for record counts. '
    'An explicitly requested measure takes precedence: do not add alternatives to it. '
    'Never combine candidate measures, assert equivalence or select an approved basis. '
    'Keep currencies separate. Use this mode only for one aggregate query at a common '
    'source grain with grouping fields from that base source; preserve recorded '
    'reference IDs when no supported label mapping is established. '
    'Mixed tasks may use ready with an explicit plan preserving distinct measures. '
    'An authoritative policy, approval, discrepancy or spending decision still uses '
    'needs_definition when its actual business rule is missing. Missing units, cross-source '
    'identity and incomparable grain are not resolved by this descriptive mode.')


def pin(catalog):
    resolution=(catalog.get('interpretation') or {}).get('business_resolution',{})
    return resolution if resolution.get('status')=='descriptive_measures' else None


def validate_intent(resolution,catalog,selected):
    from .subway_queries import fail
    if resolution.get('status')!='descriptive_measures':return set()
    base=resolution['base_dataset_id'];groups=resolution['group_by'];metrics=resolution['metrics']
    def invalid():fail('Descriptive metrics require distinct supported operations and exact fields at the selected source grain.','SUBWAY_SELECTION_INVALID')
    if base not in selected or len(groups)!=len(set(groups)):invalid()
    pairs=[(m['op'],m['field_id']) for m in metrics]
    if len(pairs)!=len(set(pairs)):invalid()
    required=set(groups)|{fid for _,fid in pairs if fid}
    if any(fid not in catalog['fields'] or catalog['fields'][fid]['dataset_id']!=base for fid in required):invalid()
    for op,fid in pairs:
        if not fid and op!='count':invalid()
        if fid and op in {'sum','avg'}:
            types=set(catalog['fields'][fid]['types'])-{'null'}
            if not types or not types<={'integer','number','float','decimal','Decimal128','numeric'}:invalid()
    return required


def check(query,resolution):
    from collections import Counter
    from .subway_queries import fail
    expected=Counter((m['op'],m['field_id']) for m in resolution['metrics'])
    actual=Counter((m['op'],m['field_id']) for m in query.get('metrics',[]))
    if query.get('base_dataset_id')!=resolution['base_dataset_id'] or Counter(query.get('group_by',[]))!=Counter(resolution['group_by']) or actual!=expected:
        fail('Preserve every pinned descriptive metric, its distinct source field and exact grouping.','SUBWAY_QUERY_INVALID')
