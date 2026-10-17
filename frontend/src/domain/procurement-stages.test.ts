import {expect,it} from 'vitest';
import {PROCUREMENT_STAGES,actionStage,stageActions,agentTeams} from './procurement-stages';
import type {ProjectCommunication} from './procurement-communication';
import fixture from '../../../shared/contracts/examples/workflows/support-triage.json';
it('keeps stage count fixed across many polling and send actions',()=>{
 const project={actions:Array.from({length:80},(_,i)=>({key:`read_quotes_thread_${i}`}))} as ProjectCommunication;
 expect(PROCUREMENT_STAGES).toHaveLength(11);
 expect(stageActions(project,'quotes')).toHaveLength(80);
 expect(actionStage('sync_sent_rfq_42')).toBe('rfqs');
 expect(actionStage('ful_extract_42')).toBe('fulfilment');
});
it('collapses repeated agent teams while preserving real role definitions',()=>{
 const workflow={...fixture,agents:[{agent_id:'master',hierarchy_role:'master',role:'Actual procurement master',goal:'Review requirements.'}]};
 const project={actions:[1,2,3].map(i=>({key:`ful_extract_${i}`,workflow:{...workflow,workflow_id:`child_${i}`},run:{run_id:`run_${i}`},events:[]}))} as unknown as ProjectCommunication;
 expect(agentTeams(project)).toHaveLength(1);
 expect(agentTeams(project)[0]?.workflow.workflow_id).toBe('child_3');
 expect(agentTeams({...project,actions:[]})).toHaveLength(0);
});
