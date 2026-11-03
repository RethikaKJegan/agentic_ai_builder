"""Conservative categorization of explicit bounded read-only coverage notes.

Never infer that missing access, a required identity or a write is optional.
Original notes are preserved verbatim, with a recorded classification reason.
"""
import re

READ_TOOLS = {'database_read_query', 'database_read_record'}
READ_CAPABILITIES = {'database.read_query', 'database.read_record', 'classify_text', 'generate_report'}


def separate_coverage_notes(workflow):
    metadata = workflow.get('metadata', {})
    requirements = metadata.get('unresolved_requirements', [])
    if not isinstance(requirements, list) or not requirements:
        return
    if (workflow.get('inputs') or workflow.get('execution_policy', {}).get('allow_external_writes')
        or any(t.get('tool_id') not in READ_TOOLS for t in workflow.get('tools', []))
        or any(set(a.get('capabilities', [])) - READ_CAPABILITIES for a in workflow.get('agents', []))):
        return
    # Automatic no-input workflows must already have a real pinned source scope.
    if not metadata.get('database_scope', {}).get('sources'):
        return
    limits = metadata.get('report_limitations', [])
    if not isinstance(limits, list):
        return
    remaining = []
    audit = metadata.setdefault('requirement_classifications', [])
    for item in requirements:
        reason = None
        if isinstance(item, str):
            text = ' '.join(item.lower().split())
            actionable = re.search(r'\b(configure|credentials?|permission|destination|must supply|must provide|requires? access|requires? approval|required input|missing access|supply an?|provide an?)\b', text)
            if not actionable:
                if ('no declared relationships' in text and 'returned identifiers' in text and 'explicit evidence' in text):
                    reason = 'independent_read_evidence_only'
                elif (re.search(r'no specific .{0,60}identifier was supplied', text)
                      and 'available records' in text and 'disclose' in text):
                    reason = 'bounded_discovery_without_required_case_input'
                elif ('query-only' in text and re.search(r'sampled|limited metadata', text)
                      and re.search(r'not.{0,20}proof of absence|cannot be treated as proof of absence', text)):
                    reason = 'read_only_metadata_coverage'
        if reason:
            if item not in limits:
                limits.append(item)
            entry = {'text': item, 'from': 'unresolved_requirements', 'to': 'report_limitations', 'reason': reason}
            if entry not in audit:
                audit.append(entry)
        else:
            remaining.append(item)
    metadata['unresolved_requirements'] = remaining
    metadata['report_limitations'] = limits
    if not audit:
        metadata.pop('requirement_classifications', None)
