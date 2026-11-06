import {afterEach,expect,it,vi} from 'vitest';
import {render,screen,waitFor} from '@testing-library/react';
import {useBackend} from '@/api/state';
import {ReplyCases} from './ReplyCases';
afterEach(()=>vi.unstubAllGlobals());
it('does not poll an explicitly unavailable inbox monitor',()=>{
 useBackend.setState({status:'connected',session:{reply_monitor_available:false} as never});
 const fetch=vi.fn();vi.stubGlobal('fetch',fetch);render(<ReplyCases/>);
 expect(screen.queryByRole('region',{name:'Customer reply cases'})).not.toBeInTheDocument();expect(fetch).not.toHaveBeenCalled();
});
it('continues showing the configured inbox monitor',async()=>{
 useBackend.setState({status:'connected',session:{reply_monitor_available:true,auth:{decision:'allow',permissions:['workflow.approve']}} as never});
 const fetch=vi.fn().mockResolvedValue(new Response(JSON.stringify({request_id:'reply_cases',status:200,data:{items:[],monitor:{state:'ready'}}}),{status:200}));vi.stubGlobal('fetch',fetch);
 render(<ReplyCases/>);expect(await screen.findByRole('region',{name:'Customer reply cases'})).toBeVisible();
 await waitFor(()=>expect(screen.getByText('No sent customer cases yet.')).toBeVisible());expect(fetch).toHaveBeenCalledTimes(1);
});
