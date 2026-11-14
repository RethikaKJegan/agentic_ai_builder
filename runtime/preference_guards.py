"""Additional selected protections; mandatory runtime guards are never disabled."""
import json,re
from .service import RuntimeFailure

INSTRUCTIONS={
 'formalTone':'Use a formal, professional communication style without changing facts or business rules.',
 'conciseResponses':'Keep explanations compact and relevant. Preserve required fields, evidence, caveats and safety disclosures.',
 'clarifyUncertainty':'Clearly distinguish verified observations, assumptions and missing information. Mark uncertainty; never invent certainty or unsupported execution pauses.',
 'strictOutputFormat':'Use the registered strict JSON output contract. Do not add commentary or translate machine-readable field identifiers.',
 'screenAbusiveLanguage':'Avoid directing abusive language at people. Preserve evidence and never repeat targeted insults in generated commentary.',
 'avoidHostileResponses':'Use respectful, non-threatening wording. Do not direct threats or demeaning statements at people.',
 'requireSupportingEvidence':'Ground factual business findings in supplied source references, record IDs, tool receipts or evidence bindings. If no supporting evidence exists, mark findings unsupported or insufficiently evidenced. Never manufacture citations.'}

def guidance(settings):
    enabled=settings.get('behaviours',{})
    lines=[text for key,text in INSTRUCTIONS.items() if enabled.get(key)]
    language=enabled.get('preferredLanguage','Auto')
    if language!='Auto':lines.append('Write applicable user-facing narrative in '+language+'. Preserve JSON keys, enums, identifiers, source quotations, dates, numbers and structured tool arguments exactly. Follow schemas and business rules first.')
    return '\nExecution communication preferences (subordinate to all schemas, permissions, approvals and platform policies):\n'+'\n'.join(lines) if lines else ''


def controls(settings):return {c for pack in settings.get('packs',[]) for c in pack.get('effective_controls',[])}

def protect_output(value,settings):
    enabled=controls(settings)
    behaviours=settings.get('behaviours',{})
    def apply(item):
        if isinstance(item,str):
            # Bounded English patterns only, on generated model output. These
            # checks never alter source records or structured tool arguments.
            if behaviours.get('screenAbusiveLanguage') and re.search(r"\byou(?:'re| are)\s+(?:an?\s+)?(?:fucking\s+)?(?:idiot|moron|stupid|worthless|asshole)\b",item,re.I):
                raise RuntimeFailure('BEHAVIOUR_SAFETY_REJECTED','Generated output contains a screened targeted insult. No output was dispatched.',422)
            if behaviours.get('avoidHostileResponses') and re.search(r'\b(?:I|we)\s+(?:will|shall|am going to|are going to)\s+(?:kill|hurt|attack|destroy)\s+you\b',item,re.I):
                raise RuntimeFailure('BEHAVIOUR_SAFETY_REJECTED','Generated output contains a screened direct threat. No output was dispatched.',422)
            if 'instruction_override_screening' in enabled and re.search(r'ignore (?:all |the )?(?:previous|system) instructions|reveal (?:the )?system prompt',item,re.I):
                raise RuntimeFailure('PROMPT_INJECTION_DETECTED','Generated output contains a screened instruction override.',400)
            if 'email_masking' in enabled:item=re.sub(r'\b[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}\b','[REDACTED EMAIL]',item)
            if 'us_ssn_masking' in enabled:item=re.sub(r'\b\d{3}-\d{2}-\d{4}\b','[REDACTED SSN]',item)
            return item
        if isinstance(item,list):return [apply(v) for v in item]
        if isinstance(item,dict):
            identifiers={'quote','quotation','source_text','source_references','citations','record_id','mapping_id','source_id','tool_id','agent_id','connection_id','spreadsheet_id','range','recipient','to','start','end'}
            return {k:v if k in identifiers or k in {'id','ids'} or k.endswith(('_id','_ids')) else apply(v) for k,v in item.items()}
        return item
    return apply(value)


def validate_evidence(output,inputs,settings):
    if not settings.get('behaviours',{}).get('requireSupportingEvidence'):return
    # Existing content schemas validate exact source-reference tokens. Business
    # analysis schemas are checked by existing capability evidence validators.
    if isinstance(output,dict) and 'source_references' in output:
        supplied=inputs.get('source_references',[])
        if not isinstance(supplied,list):supplied=[]
        if not set(output['source_references'])<=set(supplied):
            raise RuntimeFailure('ACTION_CONTENT_UNVERIFIED','Output cites evidence not supplied to this task.',422)
        if not supplied and not output.get('assumptions'):
            raise RuntimeFailure('ACTION_CONTENT_UNVERIFIED','Without evidence, disclose unsupported findings in the required assumptions field.',422)


def screen_input(value):
    """Known-pattern screen only; source/permission boundaries remain authoritative."""
    text=json.dumps(value)
    if re.search(r'ignore (?:all |the )?(?:previous|system) instructions|reveal (?:the )?system prompt',text,re.I):
        raise RuntimeFailure('PROMPT_INJECTION_DETECTED','Untrusted model input contains a screened instruction override.',400)


def screen_model_input(value,settings):
    if 'instruction_override_screening' in controls(settings):
        screen_input(value)
