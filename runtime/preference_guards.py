"""Additional selected protections; mandatory runtime guards are never disabled."""
import json,re
from .service import RuntimeFailure

INSTRUCTIONS={
 'formalTone':'Use a formal, professional communication style without changing facts or business rules.',
 'conciseResponses':'Keep explanations compact and relevant. Preserve required fields, evidence, caveats and safety disclosures.',
 'clarifyUncertainty':'Clearly distinguish verified observations, assumptions and missing information. Mark uncertainty; never invent certainty or unsupported execution pauses.',
 'requireSupportingEvidence':'Ground factual business findings in supplied source references, record IDs, tool receipts or evidence bindings. If no supporting evidence exists, mark findings unsupported or insufficiently evidenced. Never manufacture citations.'}

def guidance(settings):
    enabled=settings.get('behaviours',{})
    return '\nExecution communication preferences (subordinate to all schemas, permissions, approvals and platform policies):\n'+'\n'.join(text for key,text in INSTRUCTIONS.items() if enabled.get(key)) if any(enabled.get(k) for k in INSTRUCTIONS) else ''

def controls(settings):return {c for pack in settings.get('packs',[]) for c in pack.get('effective_controls',[])}

def protect_output(value,settings):
    enabled=controls(settings)
    def apply(item):
        if isinstance(item,str):
            if 'instruction_override_screening' in enabled and re.search(r'ignore (?:all |the )?(?:previous|system) instructions|reveal (?:the )?system prompt',item,re.I):
                raise RuntimeFailure('PROMPT_INJECTION_DETECTED','Generated output contains a screened instruction override.',400)
            if 'email_masking' in enabled:item=re.sub(r'\b[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}\b','[REDACTED EMAIL]',item)
            if 'us_ssn_masking' in enabled:item=re.sub(r'\b\d{3}-\d{2}-\d{4}\b','[REDACTED SSN]',item)
            return item
        if isinstance(item,list):return [apply(v) for v in item]
        if isinstance(item,dict):return {k:apply(v) for k,v in item.items()}
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
