import type {ReactNode} from 'react';
import {render,screen,fireEvent,cleanup,waitFor,within,act} from '@testing-library/react';
import {afterEach,it,expect,vi} from 'vitest';
import {api} from '@/api/client';
import {useBackend} from '@/api/state';
import {knowledgeFixture} from '@/test/fixtures/knowledge-map';
import ClientOntology from './ClientOntology';
vi.mock('@xyflow/react',()=>({ReactFlowProvider:({children}:{children:ReactNode})=>children,ReactFlow:({nodes,onNodeClick,children}:{nodes:{id:string;data:{label:string}}[];onNodeClick:(event:null,node:{id:string;data:{label:string}})=>void;children:ReactNode})=><div>{nodes.map((n)=><button key={n.id} onClick={()=>onNodeClick(null,n)}>{n.data.label}</button>)}{children}</div>,Background:()=>null,Controls:()=>null,Handle:()=>null,Position:{Left:'left',Right:'right'},MarkerType:{ArrowClosed:'arrow'}}));
afterEach(()=>{cleanup();vi.restoreAllMocks();});
it.each([['client-simpsons','Complaint'],['client-subway','Purchase order']])('loads the full saved ontology for %s without workflow usage',async(tenant,title)=>{
 const f=knowledgeFixture(tenant,title);f.snapshot.knowledge={...f.snapshot.knowledge!,identity_rules:[{id:'actual_identity_definition'}]};
 useBackend.setState({session:{auth:{subject:{workspace_id:tenant,subject_id:'owner'}}} as never});
 vi.spyOn(api,'businessOntology').mockResolvedValue(f.ontology);const read=vi.spyOn(api,'knowledgeSnapshot').mockResolvedValue(f.snapshot);
 render(<ClientOntology/>);await within(await screen.findByLabelText('Ontology business areas')).findByRole('button',{name:'Operations'});expect(screen.queryByRole('button',{name:title})).toBeNull();
 fireEvent.click(within(screen.getByLabelText('Ontology business areas')).getByRole('button',{name:'Operations'}));fireEvent.click(screen.getByRole('button',{name:title}));
 expect(await screen.findByRole('heading',{name:title})).toBeVisible();expect(screen.getByText(f.snapshot.concepts[0]!.definition)).toBeVisible();expect(within(screen.getByLabelText('Concept source fields')).getByText(new RegExp(tenant+'_records'))).toBeVisible();expect(read).toHaveBeenCalledWith(tenant+'_v1');
 fireEvent.change(screen.getByLabelText('Search complete ontology'),{target:{value:'Related'}});expect(screen.queryByRole('button',{name:title})).toBeNull();expect(screen.getByRole('button',{name:'Related '+title})).toBeVisible();
});
it('does not show ontology from an account whose response arrived late',async()=>{
 const old=knowledgeFixture();let resolve!:(value:typeof old.ontology)=>void;
 vi.spyOn(api,'businessOntology').mockImplementationOnce(()=>new Promise(done=>{resolve=done;})).mockRejectedValue(new Error('Not authorized'));
 const read=vi.spyOn(api,'knowledgeSnapshot').mockResolvedValue(old.snapshot);
 useBackend.setState({session:{auth:{subject:{workspace_id:'simpsons',subject_id:'owner'}}} as never});const {rerender}=render(<ClientOntology/>);
 await waitFor(()=>expect(api.businessOntology).toHaveBeenCalledTimes(1));
 act(()=>useBackend.setState({session:{auth:{subject:{workspace_id:'subway',subject_id:'owner'}}} as never}));rerender(<ClientOntology/>);
 await screen.findByRole('alert');await act(async()=>resolve(old.ontology));await waitFor(()=>expect(screen.queryByRole('heading',{name:'simpsons'})).toBeNull());
});
