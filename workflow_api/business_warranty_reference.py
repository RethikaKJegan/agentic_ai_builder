"""Reviewed supplied-code warranty branches, never written-policy authority."""
from hashlib import sha256
import re

SOURCE_SHA256='621995136ad5360339474d9234e72879b25d791babf440d76e77859120d72870'
REFERENCE_VERSION='simpson-warranty-implementation-v1'


def interpretations(source,clause_ids):
    text=source['text']
    if source['kind']!='application_code' or 'warranty' not in source['module_ids'] or source['sha256']!=SOURCE_SHA256 or sha256(text.encode()).hexdigest()!=SOURCE_SHA256:
        raise ValueError('The supplied warranty implementation source does not match the reviewed content.')
    blocks=list(re.finditer(r'maxDateOfSimpsonInvoiceToOEM = ([0-9]+);[^\n]*\n\s*maxDateOfMachineSaleByOEMToEndCustomer = ([0-9]+);[^\n]*\n\s*maxHmr = ([0-9]+);[^\n]*',text))
    names=re.findall(r"oemName.name.includes\('([^']+)'\)",text)
    if len(blocks)!=4 or len(names)!=3:raise ValueError('Warranty implementation branches changed.')
    condition=text[text.index('engineHmr <= maxHmr &&'):text.index('\n  ) {',text.index('engineHmr <= maxHmr &&'))]
    method=text[text.index('const monthDiff ='):text.index('\n};',text.index('const monthDiff ='))+3]
    at=next(line.strip() for line in text.splitlines() if 'const dateOfSaleDiff =' in line)
    result=[]
    for index,(key,block) in enumerate(zip(['tafe','cnh','terex','other'],blocks)):
        invoice,sale,hours=map(int,block.groups());clauses={k:dict(value=None,quote=None) for k in clause_ids}
        for k,value in [('invoice_months',invoice),('sale_months',sale),('max_hours',str(hours))]:clauses[k]=dict(value=value,quote=block.group(0))
        for k,value,quote in [('coverage_mode','sale_invoice_and_hours',condition),('coverage_date_basis','assessment_date',at),('period_method','calendar_month_difference',method),('period_boundary','inclusive',condition),('hours_boundary','inclusive',condition)]:clauses[k]=dict(value=value,quote=quote)
        selector=names[index] if index<3 else None
        result.append(dict(policy_key='implementation-'+key,title='Supplied application · '+(selector or 'Other OEM names (else branch)'),clauses=clauses,implementation_reference=dict(reference_version=REFERENCE_VERSION,branch=key,match='oem_name_contains' if selector else 'otherwise',selector=selector,source_sha256=SOURCE_SHA256)))
    return result
