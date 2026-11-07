import {afterEach,it,expect,vi} from 'vitest';
import {render,screen,act} from '@testing-library/react';
import {api} from '@/api/client';
import {RunKnowledge,RecoveryEvidence,OperationalAlerts} from './ReliabilityEvidence';
afterEach(()=>vi.restoreAllMocks());
it('shows semantic predicates and stale pins without claiming current facts',async()=>{
 vi.spyOn(api,'runKnowledge').mockResolvedValue({projections:[{pin:{graph_id:'account',source_key:'source',revision:2,sha256:'hash'},current:false,reason:'Source changed.',nodes:[{node_id:'a',kind:'concept',label:'Inspection',status:'reported'},{node_id:'b',kind:'concept',label:'Complaint',status:'reported'}],edges:[{edge_id:'e',source:'a',target:'b',predicate:'investigates',status:'inferred'}]}],qualification:'Historical references only.'});
 render(<RunKnowledge runId="r"/>);
 expect(await screen.findByText(/Historical evidence — review freshness/)).toBeVisible();expect(screen.getByText('investigates')).toBeVisible();expect(screen.getByText('(inferred)')).toBeVisible();
});
it('shows uncertainty without a replay or success control',async()=>{
 vi.spyOn(api,'recoveryInspection').mockResolvedValue({run_id:'r',status:'blocked',required_action:'operator_reconciliation',automatic_replay_allowed:false,uncertain_invocations:[{node_id:'send',effect_reference:'r:send',required_action:'verify_provider'}],completed_checkpoints:[{}],consumed_usage:{},guidance:'Verify the provider.'});
 render(<RecoveryEvidence runId="r"/>);
 expect(await screen.findByText('Provider outcome requires reconciliation')).toBeVisible();expect(screen.getByText(/r:send/)).toBeVisible();expect(screen.queryByRole('button')).toBeNull();
});
it('does not show no alerts when monitoring fails',async()=>{
 vi.spyOn(api,'operationalAlerts').mockRejectedValue(new Error('Forbidden'));
 render(<OperationalAlerts/>);expect(await screen.findByText('Operational diagnostics are unavailable.')).toBeVisible();expect(screen.queryByText('No configured alert conditions are active.')).toBeNull();
});
it('does not commit a late response after switching run',async()=>{
 let resolve!:(value:Awaited<ReturnType<typeof api.runKnowledge>>)=>void;
 vi.spyOn(api,'runKnowledge').mockImplementationOnce(()=>new Promise(r=>{resolve=r;})).mockRejectedValue(new Error('Unavailable'));
 const {rerender}=render(<RunKnowledge runId="old"/>);rerender(<RunKnowledge runId="new"/>);
 expect(await screen.findByText(/Account knowledge is unavailable/)).toBeVisible();
 await act(async()=>resolve({projections:[],qualification:'Old account response'}));expect(screen.queryByText('Old account response')).toBeNull();
});
