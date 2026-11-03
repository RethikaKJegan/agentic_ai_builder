"""Rebuild the curated Phase 1 authoring files from supplied reference evidence.

No model or company access. Run explicitly after editing this curated definition.
"""
from copy import deepcopy
import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
from workflow_api.business_knowledge_model import SCHEMA,digest
from workflow_api.business_knowledge import reference_sources


def build():
    directory=ROOT/'ontology/business-reference'
    bundle=json.loads((directory/'simpson-evidence.json').read_text())
    sources=reference_sources(bundle)
    def provenance(module,quote,code=False,configured=False):
        source=next(d for d in sources if module in d['module_ids'] and d['kind']==('application_code' if code else 'blueprint') and quote in d['text'])
        return dict(origin='configured_logic' if configured else 'application_behavior' if code else 'source_definition',evidence=[dict(source_id=source['source_id'],quote=quote)])
    arch=provenance('evidence','PhysicalEntity') if any('evidence' in d['module_ids'] and d['kind']=='blueprint' and 'PhysicalEntity' in d['text'] for d in sources) else dict(origin='source_definition',evidence=[dict(source_id='ref_c554e435203c2b79b6b7c8ea',quote='PhysicalEntity')])
    def concept(cid,label,definition,parent,layer,p):
        return dict(id=cid,label=label,definition=definition,parent_id=parent,layer=layer,evidence=p['evidence'],confidence=.7,unknowns=[],properties=[],module_id=cid.split(':')[0],status='draft')
    new=[
      concept('engines:physical_product','PhysicalProduct','A physical product, distinguished from its model and source records.','evidence:physical_entity','common',dict(origin='source_definition',evidence=[dict(source_id='ref_c554e435203c2b79b6b7c8ea',quote='Product')])),
      concept('engines:engine_invoice_record','EngineInvoiceRecord','An engine invoice entry, not a globally resolved physical engine identity.','evidence:information_object','domain',provenance('engines','engineSerialNumber',True)),
      concept('organization:oem_account','OEMAccount','An OEM application account; distinct from the OEM company.','evidence:information_object','organization',provenance('organization','oemNameId',True)),
      concept('replacement:replacement_dispatch','ReplacementDispatchRecord','Source dispatch information for a replacement engine.','evidence:information_object','domain',provenance('replacement','replacementEngineNumber',True)),
      concept('quality:analysis_record','FailedEngineAnalysisRecord','A source failed-engine analysis record; its status is not itself a confirmed root cause.','evidence:information_object','domain',provenance('quality','engineSerialNumber',True)),
      concept('effectivity:cut_in_record','InternalCutInRecord','Recorded cut-in scope and boundary; incorporation and serial ordering remain separate.','evidence:information_object','business',provenance('effectivity','cutInDate',True)),
    ]
    parents={'engines:engine_instance':'engines:physical_product','engines:engine_component':'evidence:physical_entity','engines:engine_model':'evidence:information_object','inspection:joint_inspection':'evidence:process','inspection:diagnostic_test':'evidence:process','inspection:inspection_report':'evidence:information_object','quality:quality_investigation':'evidence:process','quality:returned_engine_inspection':'evidence:process','replacement:replacement_engine':'engines:engine_instance','replacement:failed_engine':'engines:engine_instance','organization:organizational_role_assignment':'evidence:information_object','evidence:physical_entity':'evidence:entity','evidence:information_object':'evidence:entity','evidence:process':'evidence:entity','evidence:event':'evidence:entity','evidence:role':'evidence:entity'}
    changes={cid:dict(id=cid,parent_id=parent) for cid,parent in parents.items()}
    changes['engines:invoice']=dict(id='engines:invoice',parent_id='evidence:information_object',optional=True)
    changes['engines:engine_instance']['definition']='A physical engine. A serial is an identifier observation and does not alone resolve physical identity across source records.'
    changes['engines:engine_instance']['property_descriptions']={name:'An observed engine serial; physical identity requires source-scoped association evidence.' for name in ('serial_number','engine_serial_number')}
    for cid in ('organization:organization','organization:person'):changes[cid]=dict(id=cid,layer='common')
    k=dict(schema_version=SCHEMA,concept_details=[],relationship_details=[],source_mappings=[],identity_rules=[],state_models=[],temporal_models=[],structured_rules=[],dependencies=[])
    details={}
    def detail(cid,p,aliases=()):
        if cid not in details:details[cid]=dict(concept_id=cid,entity_kind='class',aliases=list(aliases),attributes=[],provenance=p)
        return details[cid]
    def attribute(cid,name,kind,meaning,p,unit=None,values=(),target=None,precision=None,origin='recorded'):
        change=changes.setdefault(cid,dict(id=cid));props=change.setdefault('properties',[])
        if name not in {x['name'] for x in props}:props.append(dict(name=name,datatype=kind,required=False,description=meaning))
        meta=dict(name=name,business_meaning=meaning,business_datatype=kind,stored_datatypes=[],unit=unit,allowed_values=list(values),nullable=True,missing_behavior='unknown',reference_target=target,min_count=0,max_count=1,date_precision=precision,measurement_origin=origin,provenance=p)
        detail(cid,p)['attributes'].append(meta)
        return meta
    def mapping(mid,cid,attr,kind,role,collection,path,types,p,unit=None,values=(),target=None,precision=None,conversion='identity',origin='recorded'):
        meta=attribute(cid,attr,kind,'Recorded '+attr.replace('_',' ')+' from '+collection+'.'+path+'.',p,unit,values,target,precision,origin)
        meta['stored_datatypes']=types
        m=dict(id='mapping:'+mid,concept_id=cid,attribute=attr,source_role=role,collection=collection,field_path=path,stored_datatypes=types,business_datatype=kind,conversion=conversion,unit=unit,missing_behavior='unknown',provenance=p)
        k['source_mappings'].append(m)
        if kind in ('date','datetime'):k['temporal_models'].append(dict(id='time:'+mid,concept_id=cid,attribute=attr,meaning=meta['business_meaning'],mapping_id=m['id'],precision=precision,fallback_mapping_id=None,provenance=p))
        return m['id']
    pc=provenance('complaints','engineNo',True);pi=provenance('inspection','ticketId',True);pe=provenance('engines','engineSerialNumber',True);pq=provenance('quality','engineSerialNumber',True);pr=provenance('replacement','ticketId',True);px=provenance('effectivity','cutInDate',True)
    mapping('ticket_serial','complaints:warranty_ticket','submitted_serial','string','service','tickets','engineNo',['string'],pc,origin='reported')
    mapping('complaint_symptom','complaints:reported_symptom','reported_description','string','service','tickets','complaintRecord.natureOfCustomerComplaint',['string'],provenance('complaints','natureOfCustomerComplaint',True),origin='reported')
    mapping('complaint_oem_notes','complaints:complaint_submission','oem_investigation_notes','string','service','tickets','complaintRecord.investigationDetailsByOem',['string'],provenance('complaints','investigationDetailsByOem',True),origin='reported')
    mapping('customer_complaint_date','complaints:complaint_submission','customer_complaint_date','date','service','tickets','complaintRecord.customerComplaintDate',['date','datetime','string'],provenance('complaints','customerComplaintDate',True),precision='calendar_day',conversion='iso_date',origin='reported')
    mapping('ticket_id','complaints:warranty_ticket','ticket_id','string','service','tickets','_id',['string'],pc)
    mapping('complaint_hours','complaints:reported_operating_hours','hours','decimal','service','tickets','complaintRecord.hmr',['string'],pc,unit='hour',conversion='parse_nonnegative_decimal',origin='reported')
    mapping('ticket_hours','complaints:warranty_ticket','recorded_hours','decimal','service','tickets','hmr',['integer','number','int','double'],pc,unit='hour',conversion='parse_nonnegative_decimal')
    mapping('sale_date','complaints:warranty_ticket','reported_sale_date','date','service','tickets','complaintRecord.dateOfSale',['date','datetime'],pc,precision='calendar_day',conversion='iso_date',origin='reported')
    mapping('complaint_created','complaints:warranty_ticket','registered_at','datetime','service','tickets','createdAt',['date','datetime'],pc,precision='instant',conversion='iso_datetime')
    mapping('complaint_status','complaints:warranty_ticket','case_status','enumeration','service','tickets','status',['string'],pc,values=['OPENED','RESOLVED','CLOSED','REOPENED'])
    mapping('engineer_reference','complaints:warranty_ticket','engineer_reference','reference','service','tickets','serviceEngineer',['string','ObjectId'],pc,target='organization:person')
    mapping('invoice_serial','engines:engine_invoice_record','serial_number','string','service','enginedetails','engineSerialNumber',['string'],pe)
    mapping('invoice_date','engines:engine_invoice_record','invoice_date','date','service','enginedetails','invoiceDate',['date','datetime'],pe,precision='calendar_day',conversion='iso_date')
    mapping('engine_build_date','engines:engine_invoice_record','build_date','date','service','enginedetails','buildDate',['date','datetime'],pe,precision='calendar_day',conversion='iso_date')
    mapping('invoice_model','engines:engine_invoice_record','model_observation','string','service','enginedetails','engineModel',['string'],pe)
    po=provenance('organization','oemNameId',True)
    mapping('oem_company_name','organization:oem','company_name','string','service','oemnames','name',['string'],po)
    mapping('oem_account_company','organization:oem_account','company_reference','reference','service','oems','oemNameId',['string','ObjectId'],po,target='organization:oem')
    mapping('inspection_status','inspection:inspection_report','report_status','enumeration','service','jointinspectionreports','status',['string'],pi,values=['DRAFTED','PUBLISHED'])
    mapping('inspection_failure_date','inspection:inspection_report','reported_failure_date','date','service','jointinspectionreports','dateOfFailure',['date','datetime','string'],pi,precision='calendar_day',conversion='iso_date',origin='reported')
    mapping('inspection_date','inspection:inspection_report','inspection_date','date','service','jointinspectionreports','dateOfInspection',['date','datetime','string'],pi,precision='calendar_day',conversion='iso_date')
    mapping('inspection_potential_cause','inspection:inspection_report','potential_cause','string','service','jointinspectionreports','potentialCause',['string'],pi)
    mapping('inspection_complaint_text','inspection:inspection_report','complaint_description','string','service','jointinspectionreports','complaintDescription',['string'],provenance('inspection','complaintDescription',True),origin='reported')
    mapping('inspection_defect_text','inspection:inspection_report','defect_description','string','service','jointinspectionreports','defectDescription',['string'],provenance('inspection','defectDescription',True))
    mapping('replacement_mode','replacement:replacement_case','request_mode','string','service','enginereplacements','mode',['string'],provenance('replacement','mode',True))
    mapping('part_replacement_mode','replacement:part_replacement_case','replacement_mode','string','service','partreplacements','mode',['string'],provenance('replacement','mode',True))
    mapping('dispatch_serial','replacement:replacement_dispatch','replacement_serial','string','service','floatengines','replacementEngineNumber',['string'],pr)
    mapping('dispatch_status','replacement:replacement_dispatch','dispatch_status','enumeration','service','floatengines','status',['string'],pr,values=['YET_TO_DISPATCH','ENGINE_DISPATCHED'])
    mapping('qa_serial','quality:analysis_record','serial_observation','string','quality','failedengineanalyses','engineSerialNumber',['string'],pq)
    mapping('qa_defect','quality:analysis_record','recorded_defect','string','quality','failedengineanalyses','defect',['string'],provenance('quality','defect',True))
    mapping('qa_status','quality:analysis_record','approval_status','enumeration','quality','failedengineanalyses','status',['string'],pq,values=['PENDING','APPROVED','REJECTED'])
    mapping('qa_effective_date','quality:analysis_record','cut_in_effective_date','date','quality','failedengineanalyses','cutInEffectiveDate',['date','datetime'],pq,precision='calendar_day',conversion='iso_date')
    mapping('cut_in_serial','effectivity:cut_in_record','serial_boundary','string','service','internalcutins','engineCutInNumber',['string'],px)
    # The source cut-in date is declared string; retain it until a supported format is known.
    mapping('cut_in_date_text','effectivity:cut_in_record','recorded_cut_in_date','string','service','internalcutins','cutInDate',['string'],px)
    mapping('cut_in_model','effectivity:cut_in_record','model_scope','string','service','internalcutins','engineModel',['string'],px)
    mapping('cut_in_plant','effectivity:cut_in_record','plant_scope','string','service','internalcutins','plant',['string'],px)
    mapping('cut_in_list','effectivity:cut_in_record','list_scope','string','service','internalcutins','listNo',['string'],px)
    for cid,name,meaning,p in [('warranty:warranty_assessment','assessed_at','Timestamp of the assessment; supplied explicitly, not substituted from failure or registration dates.',provenance('warranty','WarrantyAssessment',configured=True)),('inspection:inspection_report','published_at','Report publication timestamp; no exact source field is established.',provenance('inspection','InspectionReport',configured=True))]:
        attribute(cid,name,'datetime',meaning,p,precision='instant')
        k['temporal_models'].append(dict(id='time:'+name,concept_id=cid,attribute=name,meaning=meaning,mapping_id=None,precision='instant',fallback_mapping_id=None,provenance=p))
    # Every definition points to the existing field catalogue; do not invent fields.
    def bind(role,collection,field):return dict(source_role=role,collection=collection,field_path=field)
    def identity_rule(rid,kind,a,b,p):
        k['identity_rules'].append(dict(id='identity:'+rid,kind=kind,source=a,target=b,comparison={'source_identity':'source_scoped_native_id','direct_reference':'native_type_and_value','candidate':'exact_serial_candidate'}[kind],permits_physical_merge=False,provenance=p))
    identity_rule('source_record','source_identity',bind('service','tickets','_id'),None,pc)
    for rid,a,field,b,p in [('inspection_ticket','jointinspectionreports','ticketId','tickets',pi),('replacement_ticket','enginereplacements','ticket','tickets',pr),('dispatch_ticket','floatengines','ticketId','tickets',pr),('part_ticket','partreplacements','ticket','tickets',pr),('account_company','oems','oemNameId','oemnames',po),('ticket_account','tickets','oem','oems',pc),('ticket_company','tickets','oemOrg','oemnames',pc),('invoice_company','enginedetails','oem','oemnames',pe)]:identity_rule(rid,'direct_reference',bind('service',a,field),bind('service',b,'_id'),p)
    identity_rule('invoice_qa_serial','candidate',bind('service','enginedetails','engineSerialNumber'),bind('quality','failedengineanalyses','engineSerialNumber'),pq)
    relationships=[]
    def relation(rid,source,predicate,target,p,binding=None):
        relationships.append(dict(id=rid,label=predicate.replace('_',' ').capitalize()+' — '+source.split(':')[1],definition=source+' '+predicate+' '+target+'. This defines meaning; source traversal requires an explicit supported binding.',layer='domain',evidence=p['evidence'],confidence=.7,unknowns=[] if binding else ['Conceptual relationship; no direct source-reference traversal is established.'],source=source,target=target,predicate=predicate,module_id=rid.split(':')[0],status='draft'))
        k['relationship_details'].append(dict(relationship_id=rid,inverse_label='inverse of '+predicate,min_count=0,max_count=1 if binding else None,traversable=binding is not None,binding_id='identity:'+binding if binding else None,provenance=p))
    relation('inspection:report_complaint','inspection:inspection_report','documents_inspection_for','complaints:warranty_ticket',pi,'inspection_ticket')
    relation('inspection:activity_complaint','inspection:joint_inspection','investigates','complaints:warranty_ticket',provenance('inspection','JointInspection'))
    relation('inspection:report_activity','inspection:inspection_report','documents','inspection:joint_inspection',provenance('inspection','InspectionReport'))
    relation('inspection:activity_observation','inspection:joint_inspection','has_observation','inspection:inspection_observation',provenance('inspection','observedDuring'))
    relation('inspection:activity_engineer','inspection:joint_inspection','performed_by','organization:person',provenance('inspection','assignedServiceEngineer'))
    relation('organization:role_person','organization:organizational_role_assignment','assigns_role_to','organization:person',provenance('organization','Person'))
    relation('organization:role_kind','organization:organizational_role_assignment','assigns_role','evidence:role',arch)
    relation('organization:account_company','organization:oem_account','account_for_company','organization:oem',po,'account_company')
    relation('complaints:case_oem_account','complaints:warranty_ticket','filed_under_account','organization:oem_account',pc,'ticket_account')
    relation('complaints:case_oem_company','complaints:warranty_ticket','company_at_creation','organization:oem',pc,'ticket_company')
    relation('engines:invoice_company','engines:engine_invoice_record','billed_to_company','organization:oem',pe,'invoice_company')
    relation('replacement:case_complaint','replacement:replacement_case','requested_for','complaints:warranty_ticket',pr,'replacement_ticket')
    relation('replacement:dispatch_complaint','replacement:replacement_dispatch','dispatch_for','complaints:warranty_ticket',pr,'dispatch_ticket')
    relation('replacement:part_complaint','replacement:part_replacement_case','replacement_for','complaints:warranty_ticket',pr,'part_ticket')
    relation('replacement:case_dispatches','replacement:replacement_case','dispatches','replacement:replacement_engine',provenance('replacement','ReplacementCase DISPATCHES ReplacementEngine'))
    relation('replacement:case_returns','replacement:replacement_case','returns','replacement:failed_engine',provenance('replacement','ReplacementCase RETURNS FailedEngine'))
    relation('quality:investigation_engine','quality:quality_investigation','examines','replacement:failed_engine',provenance('quality','Returned Engine'))
    relation('quality:investigation_observation','quality:quality_investigation','has_observation','quality:quality_observation',provenance('quality','QualityObservation'))
    relation('quality:investigation_conclusion','quality:quality_investigation','produces','quality:quality_conclusion',provenance('quality','QualityConclusion'))
    relation('capa:cause_action','failure:root_cause','addressed_by','capa:corrective_action',provenance('capa','ADDRESSED_BY'))
    relation('capa:action_change','capa:corrective_action','implemented_through','effectivity:engineering_change',provenance('capa','IMPLEMENTED_THROUGH'))
    relation('effectivity:change_has_applicability','effectivity:engineering_change','has_applicability','effectivity:change_applicability',provenance('effectivity','ChangeApplicability'))
    relation('effectivity:change_has_effectivity','effectivity:engineering_change','has_effectivity','effectivity:change_effectivity',provenance('effectivity','ChangeEffectivity'))
    relation('effectivity:effectivity_range','effectivity:change_effectivity','has_serial_range','effectivity:serial_number_range',provenance('effectivity','SerialNumberRange'))
    relation('effectivity:incorporation','effectivity:engineering_change','has_production_verification','effectivity:production_verification',provenance('effectivity','ProductionVerification'))
    relation('monitoring:population','monitoring:monitoring_program','monitors','monitoring:monitored_engine_population',provenance('monitoring','MonitoredEnginePopulation'))
    # No transition is inferred from enum order. Empty activity/incorporation models are explicit unknowns.
    for rid,cid,kind,mid,values,p in [
      ('complaint','complaints:warranty_ticket','case','mapping:complaint_status',[('OPENED','Source case opened'),('RESOLVED','Source case resolved'),('CLOSED','Source case closed'),('REOPENED','Source case reopened')],pc),
      ('inspection_report','inspection:inspection_report','report','mapping:inspection_status',[('DRAFTED','Report draft'),('PUBLISHED','Report published; inspection completion not inferred')],pi),
      ('dispatch','replacement:replacement_dispatch','replacement','mapping:dispatch_status',[('YET_TO_DISPATCH','Not recorded as dispatched'),('ENGINE_DISPATCHED','Recorded as dispatched')],pr),
      ('qa_approval','quality:analysis_record','approval','mapping:qa_status',[('PENDING','QA approval pending'),('APPROVED','QA record approved; causal confirmation not inferred'),('REJECTED','QA record rejected')],pq),
      ('inspection_activity','inspection:joint_inspection','activity',None,[],provenance('inspection','inspectionStatus')),
      ('change_applicability','effectivity:change_applicability','change_applicability',None,[],provenance('effectivity','ChangeApplicability')),
      ('change_incorporation','effectivity:production_verification','incorporation',None,[],provenance('effectivity','ProductionVerification'))]:
        k['state_models'].append(dict(id='state:'+rid,concept_id=cid,semantic_kind=kind,mapping_id=mid,values=[dict(raw=a,meaning=b) for a,b in values],transitions=[],unknown_behavior='unknown',provenance=p))
    # All transitions remain undefined: supplied enum declarations do not establish allowed transitions.
    aliases={'engines:engine_instance':['engine','motor','physical engine'],'complaints:warranty_ticket':['complaint','ticket','service case'],'failure:symptom':['symptom','overheating','coolant loss'],'failure:failure_mode':['failure','breakdown'],'inspection:joint_inspection':['inspection','joint inspection','investigation'],'capa:corrective_action':['corrective action','fix'],'monitoring:recurrence_event':['recurrence','fault returned']}
    for cid,words in aliases.items():detail(cid,provenance('failure','Symptom') if cid.startswith('failure:') else arch)['aliases']=words
    # Store aliases, not a symptom-to-cause claim or automatic query selection.
    rules=[]
    def rule(rid,label,types,conditions,p,outcome):
        rules.append(dict(id=rid,label=label,provenance={**p,'origin':'configured_logic'},fact_types=types,required_facts=list(types),conditions=dict(all=conditions),parameters={},applicability=dict(oems=[],models=[]),outcomes=dict(satisfied=outcome,unsatisfied='requirements_not_met',missing='insufficient_information'),handler='typed_conditions_v1',executable_effects=False))
    rule('warranty:assessment_readiness','Warranty Assessment',dict(operating_hours='decimal',assessment_date='date',identity_resolved='boolean',policy_applicable='boolean'),[dict(fact='operating_hours',operator='is_nonnegative'),dict(fact='assessment_date',operator='is_present'),dict(fact='identity_resolved',operator='equals',value=True),dict(fact='policy_applicable',operator='equals',value=True)],provenance('warranty','WarrantyAssessment'),'assessment_inputs_ready')
    rule('replacement:readiness','Replacement Readiness',dict(inspection_evidence_present='boolean',authorization_recorded='boolean'),[dict(fact='inspection_evidence_present',operator='equals',value=True),dict(fact='authorization_recorded',operator='equals',value=True)],provenance('replacement','ReplacementApproval'),'replacement_inputs_ready')
    rule('inspection:report_readiness','Inspection Report Availability',dict(report_status='string'),[dict(fact='report_status',operator='equals',value='PUBLISHED')],pi,'published_report_available')
    def dependency(rid,subject,concepts=(),relationships=(),mappings=(),rules=(),facts=(),conditional=()):k['dependencies'].append(dict(id='dependency:'+rid,subject_id=subject,concepts=list(concepts),relationships=list(relationships),mappings=list(mappings),rules=list(rules),required_facts=list(facts),conditional=list(conditional)))
    dependency('warranty','warranty:warranty_assessment',['engines:engine_instance','warranty:warranty_policy','warranty:warranty_evidence','warranty:warranty_exclusion'],mappings=['mapping:complaint_hours'],rules=['warranty:assessment_readiness'],facts=['engine_identity','applicable_policy','assessment_date','operating_hours','exclusion_findings'],conditional=[dict(when='selected policy requires sale date',concepts=['complaints:warranty_ticket'],mappings=['mapping:sale_date'],required_facts=['sale_date']),dict(when='selected policy requires invoice date',concepts=['engines:engine_invoice_record'],mappings=['mapping:invoice_date'],required_facts=['invoice_date'])])
    dependency('inspection','inspection:joint_inspection',['complaints:warranty_ticket','inspection:inspection_report','inspection:inspection_observation','organization:person'],['inspection:activity_complaint','inspection:report_complaint','inspection:activity_engineer'],['mapping:inspection_status','mapping:engineer_reference'],['inspection:report_readiness'],['inspection_activity_completion_evidence'])
    dependency('replacement','replacement:replacement_case',['complaints:warranty_ticket','inspection:inspection_report','replacement:replacement_approval'],['replacement:case_complaint'],rules=['replacement:readiness'],facts=['technical_disposition','commercial_authorization'])
    dependency('recurrence','monitoring:recurrence_event',['effectivity:change_applicability','effectivity:production_verification','failure:failure_mechanism','failure:root_cause'],facts=['physical_identity','actual_incorporation','comparable_confirmed_failure','operating_exposure'])
    # Versioned retrieval bindings; resolved references confer no authority.
    contract=next(s for s in sources if s['source_id']=='ref_retrieval_contract_v2')
    cp=dict(origin='configured_logic',evidence=[dict(source_id=contract['source_id'],quote=contract['text'])])
    for mid,attr,collection,path,kind,types,cid in [
      ('code_value','controlled_code','simpsoncodes','code','string',['string'],'evidence:source_record'),
      ('code_description','controlled_description','simpsoncodes','description','string',['string'],'evidence:source_record'),
      ('code_type','controlled_code_type','simpsoncodes','codeType','string',['string'],'evidence:source_record'),
      ('code_active','controlled_code_active','simpsoncodes','active','boolean',['boolean'],'evidence:source_record'),
      ('engineer_name','recorded_name','users','name','string',['string'],'organization:person'),
      ('engineer_active','recorded_active','users','active','boolean',['boolean'],'organization:person'),
      ('timeline_stage','timeline_stage','tickettimelines','stage','string',['string'],'evidence:source_record'),
      ('timeline_description','timeline_description','tickettimelines','description','string',['string'],'evidence:source_record'),
      ('timeline_created','timeline_created','tickettimelines','createdAt','datetime',['date','datetime'],'evidence:source_record'),
      ('invoice_company_reference','invoice_company_reference','enginedetails','oem','reference',['string','ObjectId'],'engines:engine_invoice_record'),
      ('invoice_list','invoice_list','enginedetails','listNo','string',['string'],'engines:engine_invoice_record'),
    ]:
        mapping(mid,cid,attr,kind,'service',collection,path,types,cp,precision='instant' if kind=='datetime' else None,conversion='iso_datetime' if kind=='datetime' else 'identity')
    for mid,conversion in [('inspection_failure_date','source_dmy_date'),('inspection_date','iso_calendar_component')]:
        m=next(m for m in k['source_mappings'] if m['id']=='mapping:'+mid)
        m['conversion']=conversion;m['provenance']=deepcopy(cp)
    identity_rule('complaint_code','direct_reference',bind('service','tickets','complaintRecord.natureOfCustomerComplaint'),bind('service','simpsoncodes','_id'),cp)
    identity_rule('ticket_engineer','direct_reference',bind('service','tickets','serviceEngineer'),bind('service','users','_id'),cp)
    identity_rule('timeline_ticket','direct_reference',bind('service','tickettimelines','ticketId'),bind('service','tickets','_id'),cp)
    identity_rule('ticket_invoice_serial','candidate',bind('service','tickets','engineNo'),bind('service','enginedetails','engineSerialNumber'),cp)
    relation('complaints:symptom_code','complaints:reported_symptom','uses_controlled_record','evidence:source_record',cp,'complaint_code')
    relation('complaints:assigned_engineer','complaints:warranty_ticket','references_engineer','organization:person',cp,'ticket_engineer')
    relation('complaints:timeline_record','evidence:source_record','records_case_event_for','complaints:warranty_ticket',cp,'timeline_ticket')
    k['concept_details']=list(details.values())
    package=dict(package_id='simpson-connected-foundation',revision=2,schema_version=SCHEMA,evidence_bundle_sha256=digest(bundle),new_concepts=new,concept_changes=list(changes.values()),relationships=relationships,knowledge=k)
    return package,dict(revision=1,rules=rules)


if __name__=='__main__':
    pack,rules=build()
    for name,value in [('knowledge-pack.json',pack),('configured-rules.json',rules)]:
        (ROOT/'ontology/business-reference'/name).write_text(json.dumps(value,indent=2)+'\n')
    print(json.dumps(dict(new_concepts=len(pack['new_concepts']),relationships=len(pack['relationships']),mappings=len(pack['knowledge']['source_mappings']),structured_rules=len(rules['rules']))))
