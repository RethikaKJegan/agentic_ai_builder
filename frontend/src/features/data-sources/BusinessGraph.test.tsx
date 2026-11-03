import {executionCatalogue} from '@/test/fixtures/business-rule-execution';
import {policyLibrary} from '@/test/fixtures/business-policy';
import {act,fireEvent,render,screen,waitFor} from '@testing-library/react';
import {afterEach,beforeEach,expect,it,vi} from 'vitest';
import {api} from '@/api/client';
import {intelligenceCatalogue} from '@/test/fixtures/business-intelligence';
import {ruleSnapshot} from '@/test/fixtures/business-rules';
import {graphPlan,sourceGraph} from '@/test/fixtures/business-graph';
import BusinessGraphPanel from './BusinessGraphPanel';
vi.mock('./BusinessGraphCanvas',()=>({default:()=> <div>Source graph canvas</div>}));
beforeEach(()=>{vi.spyOn(api,'businessRuleExecutionCatalogue').mockResolvedValue({...executionCatalogue(),rules:[]});vi.spyOn(api,'businessPolicies').mockResolvedValue(policyLibrary());vi.spyOn(api,'businessIntelligenceCatalogue').mockResolvedValue(intelligenceCatalogue());});
afterEach(()=>vi.restoreAllMocks());
it('never reads company records on open and requires explicit concept/field binding',async()=>{
 vi.spyOn(api,'businessGraphPlan').mockResolvedValue(graphPlan());const build=vi.spyOn(api,'buildBusinessGraph').mockResolvedValue(sourceGraph());
 render(<BusinessGraphPanel snapshot={ruleSnapshot()} canManage/>);
 const button=await screen.findByRole('button',{name:'Build & save source graph'});expect(button).toBeDisabled();expect(build).not.toHaveBeenCalled();
 fireEvent.click(screen.getByText('Configure source mappings (0 selected)'));fireEvent.change(screen.getByLabelText('Concept for tickets'),{target:{value:'warranty:engine'}});
 fireEvent.change(screen.getByLabelText('tickets → hours · integer · Required'),{target:{value:'hmr'}});fireEvent.change(screen.getByLabelText('Exact engine serial'),{target:{value:'SER-1'}});fireEvent.click(button);
 await waitFor(()=>expect(build).toHaveBeenCalledTimes(1));expect(build.mock.calls[0]?.[1]).toMatchObject({serial:'SER-1',plan_hash:'fixture_plan',bindings:{tickets:{concept_id:'warranty:engine',attributes:{hours:'hmr'}}},request_key:expect.any(String)});
 expect(await screen.findByText(/Monitoring unavailable/)).toBeVisible();expect(screen.getByRole('article',{name:'Graph record detail'})).toHaveTextContent('hmr12');
});
it('viewers only inspect saved snapshots',async()=>{
 const plan=graphPlan();plan.snapshots=[{graph_id:'g1',created_at:'2026-10-31',serial:'SER-1',records:2,version_id:'v2'}];vi.spyOn(api,'businessGraphPlan').mockResolvedValue(plan);
 const read=vi.spyOn(api,'businessSourceGraph').mockResolvedValue(sourceGraph());const build=vi.spyOn(api,'buildBusinessGraph');
 render(<BusinessGraphPanel snapshot={ruleSnapshot()} canManage={false}/>);const select=await screen.findByLabelText('Saved source graph');
 expect(read).not.toHaveBeenCalled();expect(screen.queryByLabelText('Exact engine serial')).not.toBeInTheDocument();fireEvent.change(select,{target:{value:'g1'}});
 expect(await screen.findByText(/Monitoring unavailable/)).toBeVisible();expect(build).not.toHaveBeenCalled();
});
it('discards late graph results when the saved version changes',async()=>{
 const plan=graphPlan();plan.snapshots=[{graph_id:'g1',created_at:'2026-10-31',serial:'SER-1',records:2,version_id:'v2'}];vi.spyOn(api,'businessGraphPlan').mockImplementation(async id=>({...plan,version_id:id}));
 let finish:(value:ReturnType<typeof sourceGraph>)=>void=()=>{};vi.spyOn(api,'businessSourceGraph').mockImplementation(()=>new Promise(resolve=>{finish=resolve;}));
 const view=render(<BusinessGraphPanel snapshot={ruleSnapshot()} canManage={false}/>);fireEvent.change(await screen.findByLabelText('Saved source graph'),{target:{value:'g1'}});
 view.rerender(<BusinessGraphPanel snapshot={ruleSnapshot('v3',3)} canManage={false}/>);await act(async()=>finish(sourceGraph()));expect(screen.queryByRole('article',{name:'Graph record detail'})).not.toBeInTheDocument();
});
