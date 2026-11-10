"""Build immutable, cited v4 evidence guidance; never edit v4 or source records."""
from pathlib import Path
import hashlib,json,sys,zipfile
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from workflow_api.business_compiler import canonical

def build():
 v=json.loads((ROOT/'ontology/subway/business-ontology-v4.json').read_text())
 archive=ROOT/'subway-finance-api-v2-gowtham-finance-v2-pr.zip'
 expected=v['dump_grounding']['archives']['finance']['sha256']
 if hashlib.sha256(archive.read_bytes()).hexdigest()!=expected:raise ValueError('Original finance archive changed')
 sources=[]
 with zipfile.ZipFile(archive) as z:
  def cite(key,suffix,start,end):
   member=next(n for n in z.namelist() if n.endswith('/'+suffix));raw=z.read(member)
   text=''.join(raw.decode().splitlines(keepends=True)[start-1:end]).rstrip('\r\n')
   source=dict(source_id='subway_resolution_'+key,title='Subway '+suffix,kind='application_code',text=text,sha256=hashlib.sha256(text.encode()).hexdigest(),origin=dict(archive=archive.name,archive_sha256=expected,member=member,member_sha256=hashlib.sha256(raw).hexdigest(),start_line=start,end_line=end))
   sources.append(source);return source['source_id']
  budget=cite('budget_check','src/services/budget-reservation.service.js',7,50)
  pr=cite('conditional_pr','src/services/purchase-order-service/create-po-core.service.js',41,60)
  stage=cite('stage_facts','src/models/stage.model.js',13,107)
 entries={
  'budgets:code_rule_reservation_available':dict(
   finding='Budget feasibility can be checked from an existing line item and requested amounts; a historical BudgetReservation record is not an input to this comparison.',
   applicability='For a proposed request, aggregate its estimatedTotalAmount values by lineItem and compare with the freshly read LineItem.availableAmount (the code uses zero when the stored value is missing). This is a source-backed comparison, not transaction execution or proof of the balance at a past date.',
   available_evidence=[dict(concept_id='budgets:finance_lineitems',collection='lineitems',fields=['_id','budgetId','availableAmount','currentAmount','initialAmount'],role='Current balance and budget identity')],
   request_inputs=['Requested line-item IDs and corresponding amounts. These are request inputs, not missing database collections.'],
   conditional_requirements=['Actual BudgetReservation records are needed only to identify individual historical reservations, their PR ownership, or active/released/converted lifecycle. Current availableAmount alone does not reconstruct them.'],
   source_ids=[budget]),
  'procurement:code_rule_approved_pr':dict(
   finding='The requisition guard runs only inside if (body.purchaseRequestId). An independent purchase order follows the department branch without requiring a requisition record.',
   applicability='First read the actual purchase order or supplied request to establish whether it has purchaseRequestId. Only a populated link triggers requisition-specific approval validation; do not demand a PR for ordinary PO totals, vendor, amount, status, budget or receipt questions.',
   available_evidence=[dict(concept_id='procurement:finance_purchaseorders',collection='purchaseorders',fields=['_id','poNumber','status','budget','department'],role='Direct PO facts; inspect a requisition link only when supplied or actually present')],
   conditional_requirements=['A genuinely linked PR requires its own approval evidence; a PO approval is not a substitute for PR approval. Absence of the field in historical records does not prove why that historical application omitted it.'],
   source_ids=[pr]),
  'approvals:finance_stages':dict(
   finding='A stage is independently recorded evidence. Its history remains usable even when its approval parent cannot be retrieved.',
   applicability='Read stages using approvalId, retaining each source _id. Report recorded StageNumber, status, approved flag, actor fields, stageDate and comments directly. Try exact approvals._id, inverse approvals.stages, document approvalId backlinks and embedded report snapshots before requiring parent-only fields.',
   available_evidence=[dict(concept_id='approvals:finance_stages',collection='stages',fields=['_id','approvalId','StageNumber','status','approved','approvedBy','rejectedBy','stageDate','approvalComments','rejectionReason'],role='Stage facts and recorded action history'),dict(concept_id='approvals:finance_approvals',collection='approvals',fields=['_id','stages','documentId','document','status'],role='Exact parent/inverse relationship when available')],
   conditional_requirements=['An approved stage does not establish final parent approval. Never infer a document identity, configuration, final decision, approver identity beyond the stored actor, or unrecorded date from a coincident numeric ID.'],
   source_ids=[stage])}
 # The same guidance accompanies every saved stage-to-parent relationship.
 for r in v['relationships']:
  if r['source']=='approvals:finance_stages' and r['target']=='approvals:finance_approvals':entries[r['id']]=dict(entries['approvals:finance_stages'])
 result=dict(resolution_version='subway-evidence-resolution-v1',ontology_version=v['version_id'],definition_sha256=hashlib.sha256(canonical(v).encode()).hexdigest(),scope=dict(workspace_id='client-subway',subject_id='subway-client'),sources=sources,entries=entries)
 result['sha256']=hashlib.sha256(canonical(result).encode()).hexdigest();return result

if __name__=='__main__':
 p=ROOT/'ontology/subway/evidence-resolution-v1.json'
 if p.exists():raise SystemExit('Refusing to overwrite immutable resolution')
 p.write_text(json.dumps(build(),indent=2)+'\n');print(p)
