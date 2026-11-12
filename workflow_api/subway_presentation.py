"""Clean delivery content, preserving canonical source/audit and execution authority."""
from copy import deepcopy
import re
from .subway_demo_data import LABEL

GUIDANCE = ('Use clean business report text in subjects, bodies, titles, descriptions and spreadsheet cells. '
            'Do not add Demo, Demo data, demonstration prefixes or repeated dataset/policy disclaimers. '
            'Display Demo Supplier N as Supplier N. Preserve all figures, separate currency groups, '
            'source citations, missing evidence and coverage facts as concise notes. '
            'Full source provenance remains in audit receipts; do not claim official policy or actual operations.')


def compact_text(value):
    value = value.replace(LABEL, '')
    patterns = (
        r'These records come from the MODELED SUBWAY DEMONSTRATION[^\n]*?(?:illustrative policies\.|$)',
        r'They are not actual Subway operations, official company policy, or operational company evidence\.',
        r'generated records and illustrative policies; not actual Subway operations or official company policy\.?',
        r'MODELED SUBWAY DEMONSTRATION',
        r'(?:This is|These are)\s+Demo data\.?\s*',
        r'The result provides descriptive measures only and does not establish policy or operational outcomes\.',
        r'This is not verified operational evidence\.',
    )
    for pattern in patterns:
        value = re.sub(pattern, '', value, flags=re.IGNORECASE)
    value = re.sub(r'\bDemo\s+Supplier\s+(\d+)\b', r'Supplier \1', value, flags=re.IGNORECASE)
    value = re.sub(r'\bDemo\s+data\b\s*(?:[·:—–-]\s*)?', '', value, flags=re.IGNORECASE)
    value = re.sub(r'\bDemo(?:nstration)?\s+', '', value, flags=re.IGNORECASE)
    value = re.sub(r'\blimitations?\b', 'Notes', value, flags=re.IGNORECASE)
    value = re.sub(r'(^|\n)\s*Notes:\s*(?=\n|$)', r'\1', value)
    value = re.sub(r'[ \t]+\n', '\n', value)
    return re.sub(r'\n{3,}', '\n\n', value).strip()


def compact(value):
    if isinstance(value, str):
        return compact_text(value)
    if isinstance(value, list):
        return [compact(v) for v in value]
    if isinstance(value, dict):
        return {k: compact(v) for k, v in value.items()}
    return value


def prepare_content(output):
    """Normalize visible generated fields before downstream payload review/digests."""
    result = deepcopy(output)
    for field in ('summary', 'subject', 'body', 'title', 'description', 'findings', 'questions', 'assumptions', 'tabs'):
        if field in result:
            result[field] = compact(result[field])
    # Source references are identifiers, never presentation strings.
    if isinstance(result.get('assumptions'), list):
        result['assumptions'] = [v for v in result['assumptions'] if v]
    for field in ('title', 'subject'):
        if field in result and not result[field]:
            result[field] = 'Report'
    for tab in result.get('tabs', []):
        tab['title'] = (tab.get('title') or 'Report')[:100]
    return result


def prepare_delivery(inputs, capability):
    """Supported content fields only; run before schema validation and exact approval."""
    fields = {
        'tool.extension_mail_send': ('subject', 'body'),
        'tool.extension_mail_draft': ('subject', 'body'),
        'tool.extension_sheets_create_report': ('title', 'tabs'),
        'tool.extension_sheets_create': ('title',),
    }.get(capability, ())
    result = deepcopy(inputs)
    for field in fields:
        if field in result:
            result[field] = compact(result[field])
    if capability == 'tool.extension_calendar_create' and isinstance(result.get('event'), dict):
        for field in ('summary', 'description'):
            if field in result['event']:
                result['event'][field] = compact(result['event'][field])
    return result
