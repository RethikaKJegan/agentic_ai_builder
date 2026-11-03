import {act,fireEvent,render,screen,waitFor,within} from '@testing-library/react';
import {afterEach,expect,it,vi} from 'vitest';
import {api} from '@/api/client';
import {ruleSnapshot,ruleCatalogue,ruleQueryResult} from '@/test/fixtures/business-rules';
import BusinessRulesPanel from './BusinessRulesPanel';
afterEach(()=>vi.restoreAllMocks());
it('shows candidate inputs, evidence and unresolved information',async()=>{
 vi.spyOn(api,'businessRuleCatalogue').mockResolvedValue(ruleCatalogue());const run=vi.spyOn(api,'runBusinessCompetency');
 render(<BusinessRulesPanel snapshot={ruleSnapshot()} moduleId="warranty"/>);
 const detail=await screen.findByRole('article',{name:'Candidate rule detail'});
 expect(within(detail).getByText(/Proposed logic · No matching handler/)).toBeVisible();
 fireEvent.click(within(detail).getByText('Required input definitions'));expect(within(detail).getByText(/Company-data availability has not been checked/)).toBeVisible();expect(within(detail).getByText(/hours · integer · Required/)).toBeVisible();
 fireEvent.click(within(detail).getByText('Rule evidence (1)'));expect(within(detail).getByRole('blockquote')).toHaveTextContent('Missing coverage information requires review.');
 fireEvent.click(within(detail).getByText('Unresolved rule information'));expect(within(detail).getByText('Exclusions have not been supplied.')).toBeVisible();
 fireEvent.change(screen.getByLabelText('Evidence basis'),{target:{value:'policy_statement'}});expect(screen.getByText('No saved candidate rules match these filters.')).toBeVisible();expect(run).not.toHaveBeenCalled();
});
it('runs an explicit bounded query and clears results when the question changes',async()=>{
 vi.spyOn(api,'businessRuleCatalogue').mockResolvedValue(ruleCatalogue());const run=vi.spyOn(api,'runBusinessCompetency').mockResolvedValue(ruleQueryResult());
 render(<BusinessRulesPanel snapshot={ruleSnapshot()} moduleId="warranty"/>);
 const button=await screen.findByRole('button',{name:'Run definition query'});expect(run).not.toHaveBeenCalled();
 fireEvent.change(screen.getByLabelText('Definition focus'),{target:{value:'warranty:review'}});fireEvent.click(button);
 const result=await screen.findByLabelText('Definition query result');expect(within(result).getByText('hours')).toBeVisible();expect(run).toHaveBeenCalledExactlyOnceWith('v2',{query_id:'rule_inputs',focus_id:'warranty:review',limit:20,offset:0});
 fireEvent.change(screen.getByLabelText('Definition question'),{target:{value:'rule_evidence'}});expect(screen.queryByLabelText('Definition query result')).not.toBeInTheDocument();expect(run).toHaveBeenCalledTimes(1);
});
it('disables unavailable queries and shows business prerequisites without auto-compilation',async()=>{
 vi.spyOn(api,'businessRuleCatalogue').mockResolvedValue(ruleCatalogue(ruleSnapshot(),false));const run=vi.spyOn(api,'runBusinessCompetency');const compile=vi.spyOn(api,'compileBusinessVersion');
 render(<BusinessRulesPanel snapshot={ruleSnapshot()} moduleId="warranty"/>);
 expect(await screen.findByRole('button',{name:'Run definition query'})).toBeDisabled();expect(screen.getByText('Compile and validate this saved version before running definition queries.')).toBeVisible();
 fireEvent.click(screen.getByText(/Business questions needing mapped company data/));expect(screen.getByText('Mapped failure dates and versioned policy/exclusions.')).toBeVisible();expect(run).not.toHaveBeenCalled();expect(compile).not.toHaveBeenCalled();
});
it('discards late query results after a version changes',async()=>{
 vi.spyOn(api,'businessRuleCatalogue').mockImplementation(async version=>ruleCatalogue(ruleSnapshot(version,version==='v3'?3:2)));
 let finish:(value:ReturnType<typeof ruleQueryResult>)=>void=()=>{};vi.spyOn(api,'runBusinessCompetency').mockImplementation(()=>new Promise(resolve=>{finish=resolve;}));
 const view=render(<BusinessRulesPanel snapshot={ruleSnapshot()} moduleId="warranty"/>);fireEvent.click(await screen.findByRole('button',{name:'Run definition query'}));
 view.rerender(<BusinessRulesPanel snapshot={ruleSnapshot('v3',3)} moduleId="warranty"/>);await waitFor(()=>expect(screen.getByText(/Revision 3 · Supported reference rules/)).toBeVisible());
 await act(async()=>finish(ruleQueryResult()));expect(screen.queryByLabelText('Definition query result')).not.toBeInTheDocument();
});
it('refreshes readiness after compilation without automatically querying',async()=>{
 const load=vi.spyOn(api,'businessRuleCatalogue').mockResolvedValueOnce(ruleCatalogue(ruleSnapshot(),false)).mockResolvedValue(ruleCatalogue());const run=vi.spyOn(api,'runBusinessCompetency');
 const view=render(<BusinessRulesPanel snapshot={ruleSnapshot()} moduleId="warranty" refreshToken={0}/>);expect(await screen.findByRole('button',{name:'Run definition query'})).toBeDisabled();
 view.rerender(<BusinessRulesPanel snapshot={ruleSnapshot()} moduleId="warranty" refreshToken={1}/>);await waitFor(()=>expect(screen.getByRole('button',{name:'Run definition query'})).toBeEnabled());expect(load).toHaveBeenCalledTimes(2);expect(run).not.toHaveBeenCalled();
});
it('keeps query failures visible and permits a safe catalogue refresh',async()=>{
 const load=vi.spyOn(api,'businessRuleCatalogue').mockResolvedValue(ruleCatalogue());vi.spyOn(api,'runBusinessCompetency').mockRejectedValue(new Error('query failed'));
 render(<BusinessRulesPanel snapshot={ruleSnapshot()} moduleId="warranty"/>);fireEvent.click(await screen.findByRole('button',{name:'Run definition query'}));
 expect(await screen.findByRole('alert')).toBeVisible();fireEvent.click(screen.getByRole('button',{name:'Retry read'}));await waitFor(()=>expect(load).toHaveBeenCalledTimes(2));expect(screen.queryByLabelText('Definition query result')).not.toBeInTheDocument();
});

it('shows all rules initially and preserves explicit rule filtering across module changes',async()=>{
 vi.spyOn(api,'businessRuleCatalogue').mockResolvedValue(ruleCatalogue());const run=vi.spyOn(api,'runBusinessCompetency');
 const view=render(<BusinessRulesPanel snapshot={ruleSnapshot()} moduleId="engines"/>);
 expect(await screen.findByRole('article',{name:'Candidate rule detail'})).toBeVisible();
 expect(screen.getByLabelText('Rule module')).toHaveValue('all');
 view.rerender(<BusinessRulesPanel snapshot={ruleSnapshot()} moduleId="warranty"/>);
 expect(await screen.findByRole('article',{name:'Candidate rule detail'})).toBeVisible();expect(run).not.toHaveBeenCalled();
});
