"""Build an immutable, non-executable Subway code-evidence draft. No model calls.

Original ZIPs are opened read-only. Only reviewed excerpts are extracted, to a new
private output directory. Archive applications are never imported or executed.
"""
import argparse
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys
import zipfile

ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
from scripts.integration_config import private_write
from workflow_api.google_connections import now
from workflow_api.business_compiler import check_snapshot,compile_snapshot

VERSION='bov_subway_code_v2'
ARCHIVES={
 'finance':'subway-finance-api-v2-gowtham-finance-v2-pr.zip',
 'intranet':'subway-intranet-api-master.zip',
 'cf':'subway-cf-approval-api-master.zip',
 'documents':'subway-docustorage-api-master.zip',
 'invoices':'subway-invoice-tracking-api-master.zip',
 'quality':'subway-qnet-api-master.zip',
 'franchise':'subway-subs-api-v2-master.zip',
 'technical':'subway-technet-api-master.zip'}
# Existing source record classes use database-qualified IDs. Separate service stores
# stay separate even when their model names or integer IDs happen to be the same.
MODELS={
 'finance':[
 ('Company','company','organization:finance_companies'),('Location','location','organization:finance_locations'),
 ('PurchaseOrder','purchase-order','procurement:finance_purchaseorders'),('Item','item','procurement:finance_items'),('Category','category','procurement:finance_categories'),('SubCategory','subcategory','procurement:finance_subcategories'),
 ('Budget','budget','budgets:finance_budgets'),('LineItem','line-item','budgets:finance_lineitems'),('BudgetModification','budget-modification','budgets:finance_budgetmodifications'),
 ('Grn','grn','receipts:finance_grns'),('InvoiceData','invoicedata','receipts:finance_invoicedatas'),('Approval','approval','approvals:finance_approvals'),('ApprovalConfig','approval-config','approvals:finance_approvalconfigs'),('Stage','stage','approvals:finance_stages'),
 ('PurchaseRequest','purchase-request','procurement:purchase_request'),('BudgetReservation','budget-reservation','budgets:budget_reservation'),('AllocationMovement','allocation-movement','procurement:allocation_movement')],
 'intranet':[('Store','store','stores:central_stores'),('StoreProperties','store-properties','stores:central_storeproperties'),('Department','department','organization:central_departments'),('Role','role','organization:central_roles'),('App','app','evidence:central_apps'),('AppDocument','app-document','evidence:central_appdocuments'),('AppDocumentCategory','app-document-category','evidence:central_appdocumentcategories'),('ConfirmAppDocument','confirm-app-document','evidence:central_confirmappdocuments'),('AppProperties','app-properties','evidence:central_appproperties')],
 'cf':[('CfApprovalV2','cf-approval-v2','cf_approvals:cf_record'),('CfStepMaster','cf-step-master','cf_approvals:step_configuration'),('CfExceptionApprovers','cf-exception-approvers','cf_approvals:exception_approver_configuration'),('CapexCalculation','capex-calculation','cf_approvals:capex_calculation'),('CfFinancial','cf-financial','cf_approvals:financial_record')],
 'documents':[('Restaurant','restaurant','document_storage:restaurant_record'),('Document','document','document_storage:document'),('Timeline','timeline','document_storage:document_timeline'),('CompanyDocument','company-document','document_storage:company_document')],
 'invoices':[('Invoice','invoice','invoice_tracking:invoice'),('Vendor','vendor','invoice_tracking:vendor'),('Voucher','petty-expense/voucher','invoice_tracking:voucher'),('LegalDoc','legal-doc','invoice_tracking:legal_document'),('Stage','stage','invoice_tracking:approval_stage')],
 'quality':[('Case','case','quality_cases:complaint_case'),('ComplaintType','complaint-type','quality_cases:complaint_type'),('Product','product','quality_cases:product'),('ProductCategory','product-category','quality_cases:product_category'),('Store','store','quality_cases:store_record')],
 'franchise':[('Store','store','franchise_records:store_record'),('StoreTransfer','store-transfer','franchise_records:store_transfer'),('StoreLease','lease','franchise_records:store_lease'),('FranchiseAgreement','franchise-agreement','franchise_records:franchise_agreement'),('Waiver','waivers','franchise_records:waiver'),('WaiverAssignment','waiver-assignment','franchise_records:waiver_assignment')],
 'technical':[('Ticket','ticket','technical_support:ticket'),('Department','department','technical_support:department'),('TicketCategory','ticket-cat','technical_support:ticket_category'),('Store','store','technical_support:store_record'),('ComplaintForm','complaint','technical_support:complaint_form'),('Escalation','escalation','technical_support:escalation'),('TicketTag','ticket-tag','technical_support:ticket_tag')]
}
MODULES={
 'cf_approvals':'CF approvals and capital planning','document_storage':'Restaurant document storage',
 'invoice_tracking':'Invoice tracking and legal documents','quality_cases':'Quality complaints and credit handling',
 'franchise_records':'Franchise, lease and store transfer records','technical_support':'Technical tickets and escalation'}
# Every rule is explicitly reviewed against its exact branch, including qualifications.
RULES=[
 ('finance','approvals','config_update_pending','Approval configuration update protects pending approvals','services/approval-config.service.js',47,60,['approvals:finance_approvalconfigs','approvals:finance_approvals'],['An approval references this configuration with status APPROVAL_IN_PROGRESS.'],'Reject configuration update until those approvals close.'),
 ('finance','approvals','config_delete_pending','Approval configuration deletion protects pending approvals','services/approval-config.service.js',99,109,['approvals:finance_approvalconfigs','approvals:finance_approvals'],['An approval references this configuration with status APPROVAL_IN_PROGRESS.'],'Reject configuration deletion.'),
 ('finance','approvals','manager_location','Area and regional manager configuration restriction','services/approval-config.service.js',32,44,['approvals:finance_approvalconfigs','organization:finance_locations'],['The location type is absent or HO.','The configured approver role matches the configured area-manager or regional-manager ID.'],'Reject this approval configuration; resolve role IDs and location types from their authoritative configuration.'),
 ('finance','procurement','approved_pr','Linked requisition must be approved before purchase order creation','services/purchase-order-service/create-po-core.service.js',41,54,['procurement:purchase_request','procurement:finance_purchaseorders'],['The creation request supplies purchaseRequestId.'],'Require an existing APPROVED requisition, successful conversion permission check and delivery/item/rate-contract validation. Helper implementations determine their exact conditions.'),
 ('finance','procurement','independent_department','Independent purchase order requires department','services/purchase-order-service/create-po-core.service.js',55,58,['procurement:finance_purchaseorders'],['No linked purchaseRequestId is supplied.','body.department is absent or falsy.'],'Reject creation with Department is required.'),
 ('finance','procurement','budget_approval','Purchase order budget approval guard','services/purchase-order-service/create-po-core.service.js',73,76,['procurement:finance_purchaseorders','budgets:finance_budgets'],['The resolved budget.initialApproval is falsy.','The budget.status is not APPROVED.'],'Reject purchase order creation. A truthy initialApproval bypasses this particular guard; this is not an unconditional approved-budget rule.'),
 ('finance','procurement','ticket_category','Ticket metadata for ticket-required line-item category','services/line-item-service/po-line-item-check.js',45,64,['procurement:finance_purchaseorders','budgets:finance_lineitems'],['The line-item category has isTicketRequired.','The item lacks ticketNumber or ticketCreationDate.'],'Reject item validation. This does not establish a validated foreign key to the technical-ticket service.'),
 ('finance','procurement','creator_short_close','Requisition item short close requires creator and allowed state','services/purchase-request-service/short-close.service.js',21,29,['procurement:purchase_request'],['A user requests item short close.'],'Reject a user whose normalized ID differs from createdBy; allow this guard only for APPROVED or CONVERTED requisitions. Other short-close checks still apply.'),
 ('finance','budgets','reservation_available','Budget reservation requires available line-item amount','services/budget-reservation.service.js',25,65,['budgets:budget_reservation','budgets:finance_lineitems'],['Aggregated reservation amount for a line item exceeds its availableAmount, with missing availableAmount treated as zero.'],'Reject within the transaction. Otherwise the shown path decrements availableAmount and creates an active reservation; no concurrency proof is claimed.'),
 ('finance','budgets','positive_modification','Budget modification rejects nonpositive updated price','services/budget-modification.service.js',19,27,['budgets:finance_budgetmodifications'],['updatedPrice is less than or equal to zero.'],'Reject this modification. The excerpt also special-cases oldPrice zero in percentDiff calculation.'),
 ('finance','receipts','grn_duplicate','Active goods receipt uniqueness check','services/grn-service/index.js',26,41,['receipts:finance_grns'],['Another GRN has the same invoiceNumber, vendorCode and financialyear.','That GRN status is neither CANCELLED nor REJECTED.'],'Reject GRN creation. This application lookup is not proof of a unique database constraint or concurrency-safe duplicate prevention.'),
 ('finance','receipts','advance_maximum','Advance invoice update amount ceiling','services/invoice-data-service/index.js',92,103,['receipts:finance_invoicedatas','procurement:finance_purchaseorders'],['The stored invoice type is ADVANCE_INVOICE.','The incoming invoiceAmount exceeds the populated purchase order advance.advanceAmount.'],'Reject the update. Missing population or values require separate validation; no policy threshold is invented.'),
 ('intranet','evidence','document_department','Document confirmation requires configured department mapping','services/app-document.service.js',74,94,['evidence:central_appdocuments','evidence:central_confirmappdocuments','organization:central_departments'],['The application document configuration lists the user role in deptMappingRoles.'],'Require the user department in the document category departments; reject an existing confirmed user/document pair.'),
 ('intranet','evidence','invalidate_confirmations','Document update resets confirmations when enabled','services/app-document.service.js',21,55,['evidence:central_appdocuments','evidence:central_confirmappdocuments'],['The application properties allowConfirm flag is enabled during document update.'],'Set isConfirmed false for all confirmation records matching appDocumentId. Role/department filters in this path select notification recipients, not the reset target.'),
 ('cf','cf_approvals','typed_inputs','CF step inputs use configured type and requiredness','services/cf-v2.service.js',104,158,['cf_approvals:cf_record','cf_approvals:step_configuration'],['A CF step collects inputs against its configured inputFields.'],'Reject missing required values unless skipRequiredCheck applies, invalid configured dropdown choices, missing conditional uploads and numeric values converting to NaN.'),
 ('cf','cf_approvals','step_approval','CF approval enforces current step authority','services/cf-v2.service.js',1300,1325,['cf_approvals:cf_record','cf_approvals:step_configuration'],['The record is IN_PROGRESS and its current step is 1 or a later configured step.'],'Step 1 resubmission requires the creator; later steps call isAuthorizedForStep. That helper explicitly returns true for ADMIN and CF_READ_ONLY, otherwise checks configured user/regional-user/role matches. The read-only role bypass is a source concern, not an approved authorization policy.'),
 ('documents','document_storage','duplicate_document','Document upload rejects its matching key','services/document.service.js',9,24,['document_storage:document','document_storage:document_timeline'],['A document exists for the documentMatchingFilter assembled in this function.'],'Reject duplicate upload; otherwise create document and upload timeline records. Retain the actual matching filter rather than inventing a global document uniqueness key.'),
 ('documents','document_storage','document_timeline','Document update requires aligned document and timeline','services/document.service.js',27,45,['document_storage:document','document_storage:document_timeline'],['An update resolves document and timeline using their matching filters.'],'Reject missing records or denied edit access. License updates additionally call removeAppliedFor; its effect requires helper evidence.'),
 ('documents','document_storage','upsert_consistency','Document upsert refuses partial document/timeline state','services/document.service.js',48,76,['document_storage:document','document_storage:document_timeline'],['Exactly one of document or matching timeline exists.'],'Reject as out of sync. When neither exists the shown path creates both; existing pairs require editAccess.'),
 ('invoices','invoice_tracking','vendor_invoice_unique','Invoice tracking update checks invoice number and vendor','services/invoice.service.js',44,59,['invoice_tracking:invoice','invoice_tracking:vendor'],['The update supplies invoiceNumber or vendor.','The resolved pair matches another invoice excluding the current ID.'],'Reject update with Duplicate Invoice Number. This is separate from finance InvoiceData and not proof of a database unique index.'),
 ('invoices','invoice_tracking','resubmission_routing','Invoice resubmission resets approval routing','services/invoice.service.js',62,93,['invoice_tracking:invoice'],['resubmit is truthy.'],'If the incoming invoiceType is in AM_APPROVAL_REQUIRED_INVOICE_TYPES, assign AM and reset shown AM/RM fields; otherwise assign Finance and clear amApprovalRequired. Reset the shown Finance approval fields. The type list is configuration, not an invented threshold.'),
 ('quality','quality_cases','credit_authority','Quality credit issuance uses role and case participant checks','services/case.service.js',148,174,['quality_cases:complaint_case'],['The incoming status is CREDIT_ISSUED.'],'Require the shown DC/vegetable-vendor/admin checks, matching vendor/DC identities where applicable, and reject action-taker role. Branch-specific exceptions remain as coded.'),
 ('quality','quality_cases','closure_admin','Quality case closure requires prior admin closure','services/case.service.js',252,261,['quality_cases:complaint_case'],['The incoming status is CLOSED.'],'Require closedByAdminAt and an ADMIN or R&D role. The commented store-credit confirmation guard is not treated as enforced.'),
 ('quality','quality_cases','credit_information','Quality credit issuance requires credit information','services/case.service.js',286,322,['quality_cases:complaint_case'],['The incoming status is CREDIT_ISSUED and creditInfo is absent.'],'Reject as Credit information missing. Status progression is separately checked against nextValidStatuses.'),
 ('franchise','franchise_records','transfer_owner','Store transfer rejects an existing buyer owner','services/store-transfer.service.js',10,25,['franchise_records:store_transfer','franchise_records:store_record'],['The store is found by parsed storeNo.','An owner ID equals parsed buyerPersonNum.'],'Reject the transfer; a missing store is also rejected. Sequence/satellite identity is not established by this lookup alone.'),
 ('franchise','franchise_records','waiver_store','Waiver assignment requires an existing store','services/waiver-assignment.service.js',9,19,['franchise_records:waiver_assignment','franchise_records:store_record'],['The create request supplies a store identifier.'],'Reject if the store lookup returns no store; otherwise create the assignment. This does not prove waiver eligibility or lease compliance.'),
 ('technical','technical_support','sla_selection','SLA escalation selection observes holds and weekends','services/ticket.service.js',208,234,['technical_support:ticket','technical_support:department'],['The scheduler selects tickets for SLA escalation.'],'Use the shown OPENED/internal-or-external/hold/expiry filters. On Saturday or Sunday in Asia/Kolkata, exclude departments whose holdWeekEndEscalations is true.'),
 ('technical','technical_support','next_sla','Ticket escalation advances only to configured next level','services/escalation.service.js',159,181,['technical_support:ticket','technical_support:ticket_category','technical_support:escalation'],['The category has an escalation matrix with a next-level entry.'],'Set the next SLA level and compute expiry from current time plus the first next-level configured sla hours. Do not invent a fixed SLA duration or assert email delivery.')]


def build(output,baseline):
    output=Path(output).resolve();output.mkdir(mode=0o700,parents=True,exist_ok=False)
    snapshot=deepcopy(baseline)
    if snapshot['workspace']['ontology_id']!='subway':raise ValueError('Subway baseline required.')
    manifest={'archives':{},'excerpts':[],'excluded_rule_defects':[]};bundles={};texts={};model_refs={}
    for key,name in ARCHIVES.items():
        path=ROOT/name
        with zipfile.ZipFile(path) as archive:
            if archive.testzip():raise ValueError('Archive integrity failed.')
            manifest['archives'][key]=dict(name=name,sha256=hashlib.sha256(path.read_bytes()).hexdigest(),bytes=path.stat().st_size)
            # Read only relevant source text. Do not import supplied modules/config.
            for info in archive.infolist():
                if info.is_dir() or '/src/' not in info.filename or not info.filename.endswith('.js'):continue
                suffix=info.filename.split('/src/',1)[1]
                if suffix.startswith(('models/','services/')):
                    texts[(key,suffix)]=(info.filename,archive.read(info).decode('utf8','strict'))
        bundles[key]=[]
    scan_inputs=[dict(key=key+'|'+path,text=text) for (key,path),(member,text) in texts.items() if path.startswith('models/')]
    scans=json.loads(subprocess.check_output(['node',str(ROOT/'scripts/subway_code_model_scan.mjs')],input=json.dumps(dict(sources=scan_inputs)),text=True))
    def excerpt(key,path,start,end):
        member,text=texts[(key,path)];lines=text.splitlines(keepends=True)
        if not 1<=start<=end<=len(lines):raise ValueError(f'Invalid excerpt {key}/{path}:{start}-{end}')
        quote=''.join(lines[start-1:end]).rstrip('\r\n')
        # Evidence must not carry credentials, endpoints or personal account values.
        from registry.safety import reject_secrets
        try:reject_secrets({'text':quote})
        except Exception:raise ValueError(f'Sensitive excerpt requires narrower bounds: {key}/{path}:{start}-{end}') from None
        if re.search(r'https?://|[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}',quote):raise ValueError(f'Review sensitive excerpt {key}/{path}:{start}')
        digest=hashlib.sha256(text.encode()).hexdigest();eid=f'{key}:{path}:{start}-{end}'
        if not any(x['excerpt_id']==eid for x in manifest['excerpts']):
            item=dict(excerpt_id=eid,archive=ARCHIVES[key],archive_sha256=manifest['archives'][key]['sha256'],member=member,member_sha256=digest,start_line=start,end_line=end,excerpt_sha256=hashlib.sha256(quote.encode()).hexdigest())
            manifest['excerpts'].append(item);bundles[key].append(f'FILE {member} LINES {start}-{end}\n'+quote)
            target=output/'excerpts'/key/(path+f'.L{start}-{end}.txt');target.parent.mkdir(mode=0o700,parents=True,exist_ok=True);private_write(target,quote+'\n')
        # Evidence schema bounds quotes, preserving an exact prefix of the snippet.
        return dict(source_id='subway_code_'+key,quote=quote[:1150]),dict(archive=ARCHIVES[key],member=member,start_line=start,end_line=end,member_sha256=digest)
    for mid,label in MODULES.items():
        snapshot['modules'].append(dict(id=mid,label=label,description='Source-code model and implemented workflow evidence; corresponding database not supplied.',layers=['domain','organization','business']))
        snapshot['questions'][mid]=['Which deployed release and data sources match this archived application code?','Which authoritative policy documents confirm these implemented behaviors?']
    concepts={c['id']:c for c in snapshot['concepts']};aliases={}
    for key,models in MODELS.items():
        aliases[key]={name:cid for name,_,cid in models}
        for name,file,cid in models:
            path='models/'+file+'.model.js'
            if (key,path) not in texts:path='models/'+file+'.js'
            _,text=texts[(key,path)]
            scan=scans[key+'|'+path];model_refs[(key,cid)]=(path,scan['references'])
            lines=text.splitlines();start=next((i+1 for i,l in enumerate(lines) if re.search(r'(?:const|let)\s+\w*[Ss]chema\s*=|mongoose\.Schema\(',l)),1);end=min(start+20,len(lines))
            if key=='technical' and name=='Store':start,end=8,15
            evidence,provenance=excerpt(key,path,start,end)
            if cid in concepts:
                concepts[cid]['evidence'].append(evidence);concepts[cid].setdefault('code_provenance',[]).append(provenance)
                concepts[cid]['data_availability']='restored_collection'
            else:
                mid=cid.split(':')[0]
                label=re.sub(r'(?<!^)([A-Z])',r' \1',name)+' record'
                if key=='quality' and name=='Case':label='Quality complaint case'
                if key=='technical' and name=='Ticket':label='Technical support ticket'
                concept=dict(id=cid,label=label,definition=f'{name} model declared in the {key} application archive. This is a code-described record, with no corresponding collection connected by this onboarding.',layer='business' if key=='cf' else 'domain',parent_id='evidence:business_record',properties=[],evidence=[evidence],confidence=.9,unknowns=['No matching database snapshot was supplied for this model.','Code archive version has not been confirmed as the deployed production release.'],module_id=mid,status='draft',data_availability='code_only_not_connected',code_provenance=[provenance])
                snapshot['concepts'].append(concept);concepts[cid]=concept
    # Declare only explicit model refs within the same service's model namespace.
    relationships=[]
    for (key,cid),(path,refs) in model_refs.items():
        for n,ref in enumerate(refs):
            target=aliases[key].get(ref['target'])
            if not target:continue
            if len(ref['quote'])>1150:continue
            evidence,provenance=excerpt(key,path,ref['start_line'],ref['end_line'])
            mid=cid.split(':')[0];field=ref['path']
            rid=f'{mid}:code_ref_'+hashlib.sha256((key+cid+field+target).encode()).hexdigest()[:16]
            if any(r['id']==rid for r in relationships):continue
            relationships.append(dict(id=rid,label=f'{cid.split(":")[1]} {field} reference',definition=f'The {key} application model declares {field} with ref {ref["target"]}. This establishes model intent; MongoDB referential integrity, archive-version alignment and cross-service identity equivalence are not asserted.',layer='domain',source=cid,target=target,predicate='references_'+ref['field'].lower(),evidence=[evidence],confidence=.95,unknowns=['No foreign-key enforcement or executable join authority is granted.','Native identifier and deployed-version compatibility must be checked before traversal.'],module_id=mid,status='draft',relationship_basis='declared_model_reference',code_provenance=[provenance],source_field=field))
    snapshot['relationships']+=relationships
    for key,mid,rid,label,path,start,end,inputs,conditions,outcome in RULES:
        evidence,provenance=excerpt(key,path,start,end)
        full=''.join(texts[(key,path)][1].splitlines(keepends=True)[start-1:end]).rstrip('\r\n')
        rule_evidence=[dict(source_id=evidence['source_id'],quote=full[i:i+1100]) for i in range(0,len(full),1100)]
        if len(rule_evidence)>8:raise ValueError('Rule citation limit exceeded.')
        snapshot['rules'].append(dict(id=mid+':code_rule_'+rid,label=label,definition='Descriptive behavior in the supplied '+key+' application source. Applies only to the cited code path; not independently verified business policy.',layer='business',inputs=inputs,conditions=conditions,outcome=outcome,basis='descriptive_implementation',evidence=rule_evidence,confidence=.9,unknowns=['Code was statically inspected, not executed.','Production release equivalence and authoritative policy approval are unverified.'],module_id=mid,status='draft',executable=False,code_provenance=[provenance]))
    helper_evidence,helper_provenance=excerpt('cf','services/cf-v2.service.js',74,95)
    cf_rule=next(r for r in snapshot['rules'] if r['id']=='cf_approvals:code_rule_step_approval')
    cf_rule['evidence'].append(helper_evidence);cf_rule['code_provenance'].append(helper_provenance)
    cf_rule['unknowns'].append('CF_READ_ONLY is accepted by the shared step-authority helper; intended approve permissions require confirmation.')
    # Preserve actual defective implementation as a limitation, never an enforcement rule.
    evidence,provenance=excerpt('finance','services/smallware-grn.service.js',98,114)
    manifest['excluded_rule_defects'].append(dict(code='SMALLWARE_APPROVER_GUARD',reason='!stage.approverRole === role negates the role before comparison; approver.status also refers to an unresolved name in this excerpt. Do not assert effective approver enforcement.',evidence=evidence,provenance=provenance))
    concepts['smallwares:finance_smallwaregrns']['unknowns'].append('Supplied smallware GRN approval guard has a precedence defect; approver authority enforcement is not verified.')
    evidence,provenance=excerpt('finance','services/invoice-data-service/index.js',105,111)
    manifest['excluded_rule_defects'].append(dict(code='ADVANCE_ZERO_AMOUNT_GUARD',reason='The positivity guard tests updateBody.invoiceAmount for truthiness first; numeric zero bypasses that specific guard. Do not assert unconditional positive amount enforcement.',evidence=evidence,provenance=provenance))
    for key,parts in bundles.items():
        text='\n\n'.join(parts)
        snapshot['sources'].append(dict(source_id='subway_code_'+key,title='Subway '+key+' source implementation excerpts',kind='application_code',module_ids=sorted({c['module_id'] for name,file,cid in MODELS[key] for c in [concepts[cid]]}),text=text,sha256=hashlib.sha256(text.encode()).hexdigest(),origin=dict(archive=ARCHIVES[key],archive_sha256=manifest['archives'][key]['sha256'],basis='read_only_static_code_excerpts'),created_at=now()))
    snapshot.update(version_id=VERSION,revision=baseline['revision']+1,created_at=now(),kind='draft',workspace={**baseline['workspace'],'revision':baseline['revision']+1,'status':'draft'},code_enrichment=dict(previous_version=baseline['version_id'],archives=manifest['archives'],added_relationships=len(relationships),added_rules=len(RULES),instance_validation='not_run',business_policy_verified=False,model_calls=0))
    check_snapshot(snapshot);report,artifacts=compile_snapshot(snapshot)
    if report['status']!='passed':raise ValueError('Definition compilation failed.')
    for module in snapshot['modules']:module['concept_count']=sum(c['module_id']==module['id'] for c in snapshot['concepts'])
    private_write(output/'ontology.json',json.dumps(snapshot,indent=2)+'\n');private_write(output/'source-manifest.json',json.dumps(manifest,indent=2)+'\n');private_write(output/'validation-report.json',json.dumps(report,indent=2)+'\n')
    for artifact in artifacts:private_write(output/artifact['name'],artifact['content'])
    print(json.dumps(dict(version=snapshot['version_id'],concepts=len(snapshot['concepts']),relationships=len(snapshot['relationships']),rules=len(snapshot['rules']),archives=len(manifest['archives']),compilation=report['status'])))
    return snapshot,manifest

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--baseline',type=Path,required=True);parser.add_argument('--output',type=Path,required=True);args=parser.parse_args();build(args.output,json.loads(args.baseline.read_text()))
