import { afterEach, expect,it,vi } from 'vitest';
import { api } from './client';
import { useBackend } from './state';
afterEach(()=>{vi.restoreAllMocks();useBackend.setState({workflowCursor:null,workflowNextCursor:null,workflowTotal:null,workflowPageBusy:false});});
it('ignores a background overview response for a page that is no longer selected',async()=>{
 let finish:(value:{items:[];next_sequence:number;has_more:boolean})=>void=()=>{};
 vi.spyOn(api,'overview').mockImplementation(()=>new Promise(resolve=>{finish=resolve;}));
 useBackend.setState({workflowCursor:null,overview:{},error:null,overviewError:null});
 const pending=useBackend.getState().refreshOverview();
 useBackend.setState({workflowCursor:'page_0050',lastOverviewUpdate:'new-page'});
 finish({items:[],next_sequence:0,has_more:false});await pending;
 expect(useBackend.getState().workflowCursor).toBe('page_0050');expect(useBackend.getState().lastOverviewUpdate).toBe('new-page');
});
