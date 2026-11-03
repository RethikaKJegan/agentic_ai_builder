import {describe,it,expect} from 'vitest';
import {render,screen,fireEvent} from '@testing-library/react';
import {canResumeInvestigation,isInvestigationPrompt,nodeLabel,investigationPlanSchema,investigationRunSchema} from '@/api/investigations';
import {InvestigationEvidence,InvestigationReportView} from './InvestigationPanels';
import {investigationLayout} from './InvestigationCanvas';
const plan=investigationPlanSchema.parse({workflow_id:'investigation_test',revision:1,objective:'Compare complaint C123 with inspection.',version_id:'version_saved',knowledge_sha256:'private_hash_saved',created_at:'2026-11-03T00:00:00Z',read_only:true,graph:{nodes:[{id:'start',type:'start',capability:null,predicate:null,inputs:[],output_type:'context',constraints:{max_attempts:1,timeout_seconds:45},on_error:'stop',join_mode:'none'},{id:'condition',type:'condition',capability:null,predicate:'complaint_found',inputs:[],output_type:'control',constraints:{max_attempts:1,timeout_seconds:45},on_error:'stop',join_mode:'none'},{id:'end',type:'end',capability:null,predicate:null,inputs:[],output_type:'report',constraints:{max_attempts:1,timeout_seconds:45},on_error:'stop',join_mode:'none'}],edges:[{id:'e1',source:'start',target:'condition',outcome:null},{id:'e2',source:'condition',target:'end',outcome:'true'}]},planning:{mode:'model',validation:{valid:true}},ontology_context:{tasks:{complaints:{concepts:[{id:'complaints:ticket',label:'WarrantyTicket',definition:'A complaint record'}],mappings:[{id:'mapping:symptom',source_role:'service',collection:'tickets',field_path:'complaintRecord.symptom',concept_id:'complaints:ticket',attribute:'reported_description',conversion:'identity',provenance:{origin:'saved_mapping'}}],rules:[{id:'rule:readiness',label:'Assessment evidence requirements'}],dependencies:{relationship_ids:['inspection:report_complaint']},missing:[]}}},inputs:{identifiers:{complaint_id:'C123'}}});

describe('investigation presentation',()=>{
 it('only offers resume for retryable failures within their attempt budget',()=>{
  const run=investigationRunSchema.parse({run_id:'run_failed',workflow_id:plan.workflow_id,status:'failed',version_id:plan.version_id,knowledge_sha256:plan.knowledge_sha256,node_states:{start:'failed'},outputs:{},branches:{},edge_states:{},node_errors:{start:{code:'INVESTIGATION_AGENT_REFERENCE',message:'Invalid citation',retryable:false}},attempts:{start:0},pending_inputs:[],usage:{},events:[],created_at:plan.created_at,updated_at:plan.created_at});
  expect(canResumeInvestigation(plan,run)).toBe(false);
  run.node_errors['start']!.retryable=true;
  expect(canResumeInvestigation(plan,run)).toBe(true);
  run.attempts['start']=1;
  expect(canResumeInvestigation(plan,run)).toBe(false);
 });
 it('routes supported business prompts while preserving general automation',()=>{
  expect(isInvestigationPrompt('Compare complaint C123 with its inspection.')).toBe(true);
  expect(isInvestigationPrompt('Check warranty readiness for motor E123.')).toBe(true);
  expect(isInvestigationPrompt('Read a spreadsheet and email a report.')).toBe(false);
  expect(isInvestigationPrompt('Check warranty for engine E123.','automation')).toBe(false);
  expect(isInvestigationPrompt('Investigate this case.','investigation')).toBe(true);
 });
 it('lays out actual backend dependencies instead of a straight list',()=>{
  const positions=investigationLayout(plan);
  expect(positions['condition']!.y).toBeGreaterThan(positions['start']!.y);
  expect(positions['end']!.y).toBeGreaterThan(positions['condition']!.y);
  expect(nodeLabel(plan.graph.nodes[1]!)).toBe('Complaint found?');
 });
 it('keeps ontology hashes and field paths behind technical details',()=>{
  render(<InvestigationEvidence plan={plan} open onClose={()=>{}}/>);
  expect(screen.getByText('Business knowledge used')).toBeVisible();
  expect(screen.getByText('Warranty Ticket')).toBeVisible();
  expect(screen.getByText(/Knowledge hash:/)).not.toBeVisible();
  fireEvent.click(screen.getByText('Technical details'));
  expect(screen.getByText(/Knowledge hash:/)).toBeVisible();
 });
 it('rejects malformed run and plan payloads',()=>{
  expect(investigationPlanSchema.safeParse({...plan,graph:{nodes:[],edges:[{id:'a',source:'start',target:'end',outcome:12}]}}).success).toBe(false);
 });
 it('renders gaps and source references separately from approval',()=>{
  const report={completion_status:'completed_with_gaps',source_records:[],agent_interpretations:[],missing_information:[{fact:'policy_applicable',reason:'missing'}],configured_rule_outcomes:[],ambiguous_associations:[],conversion_issues:[],qualification:'Reported evidence only.',physical_engine_identity:'unresolved',warranty_approval:'not_performed'};
  render(<InvestigationReportView report={report} plan={plan}/>);
  expect(screen.getByText('Investigation completed — additional evidence required')).toBeVisible();
  expect(screen.getByText('policy applicable — missing')).toBeVisible();
  expect(screen.getByText(/Readiness does not approve/)).toBeVisible();
 });
});
