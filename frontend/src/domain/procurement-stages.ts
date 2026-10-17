import type { ProjectCommunication } from './procurement-communication';
export const PROCUREMENT_STAGES = [
  ['requirements', 'Read requirements', 'Read the supplied source tables.'],
  ['boq', 'Prepare BOQ', 'Organize quantities and specifications.'],
  ['vendors', 'Match vendors', 'Review supplier contacts and coverage.'],
  ['rfqs', 'Send RFQs', 'Prepare and submit quotation requests.'],
  ['quotes', 'Collect quotations', 'Match replies and validate their evidence.'],
  ['comparison', 'Compare offers', 'Assess qualifying delivered costs and terms.'],
  ['awards', 'Award orders', 'Record selection and notify winning suppliers.'],
  ['pos', 'Release POs', 'Issue purchase orders with reviewed terms.'],
  ['fulfilment', 'Track fulfilment', 'Monitor acceptance, packing, dispatch and delivery.'],
  ['buyer', 'Confirm receipt', 'Collect buyer receipt, acceptance and resolution.'],
  ['closure', 'Close orders', 'Close confirmed orders and notify the manager.'],
] as const;
export type StageId = typeof PROCUREMENT_STAGES[number][0];
export type ProjectAction = ProjectCommunication['actions'][number];
export function actionStage(key: string, workflow?: ProjectAction['workflow']): StageId {
  if (/^sync_ful_/.test(key)) return 'fulfilment';
  if (/^ful_/.test(key)) {
    if (/buyer|receipt/.test(key)) return 'buyer';
    if (/clos/.test(key)) return 'closure';
    return 'fulfilment';
  }
  if (/award/.test(key)) return 'awards';
  if (/calendar_po|(?:^|_)po_/.test(key)) return 'pos';
  if (/compar|recommend|select/.test(key)) return 'comparison';
  if (/calendar_quotes|read_quotes|extract_|sync_quote|remind_/.test(key)) return 'quotes';
  if (/rfq|draft_/.test(key)) return 'rfqs';
  const identityColumn=workflow?.nodes.find(n=>n.kind==='tool')?.configuration?.['input'];
  const column=identityColumn&&typeof identityColumn==='object'&&'identity_column' in identityColumn?identityColumn.identity_column:undefined;
  if(column==='event_id')return 'fulfilment';
  if(column==='vendor_id')return 'vendors';
  if(column==='item_id')return 'boq';
  if (/vendor|research|supplier/.test(key)) return 'vendors';
  if (/tracking|sync_initial|boq/.test(key)) return 'boq';
  return 'requirements';
}
export function stageActions(project: ProjectCommunication, id: StageId) {
  return project.actions.filter(a => actionStage(a.key,a.workflow) === id || (id==='vendors'&&a.key==='ingestion'));
}
export function stageState(actions: ProjectAction[]) {
  if (actions.some(a => ['running','queued'].includes(a.run.status))) return 'Running';
  if (actions.some(a => ['paused_for_approval','blocked','rejected','failed','cancelled'].includes(a.run.status))) return 'Needs attention';
  return actions.length ? 'Recorded' : 'Not started';
}
export function agentTeams(project: ProjectCommunication) {
  const candidates = project.actions.map(a => ({workflow:a.workflow, events:a.events, run:a.run, stage:actionStage(a.key,a.workflow)}));
  if (!candidates.length && project.configured_workflow) candidates.push({workflow:project.configured_workflow,events:[],run:null as unknown as ProjectAction['run'],stage:'requirements'});
  const teams = new Map<string, typeof candidates[number]>();
  for (const candidate of candidates) {
    const masters = candidate.workflow.agents.filter(a => a.hierarchy_role === 'master');
    if (!masters.length) continue;
    const signature = candidate.stage+':'+masters.map(a => a.role+':'+a.goal).join('|');
    teams.set(signature,candidate);
  }
  return [...teams.values()];
}
