import {beforeEach,afterEach,it,expect,vi} from 'vitest';
import {act,cleanup,render,screen,fireEvent} from '@testing-library/react';
import {api} from '@/api/client';
import {useBackend} from '@/api/state';
import {knowledgeFixture} from '@/test/fixtures/knowledge-map';
import {KnowledgeMap} from './KnowledgeMap';

vi.mock('@xyflow/react',()=>({ReactFlowProvider:({children}:{children:React.ReactNode})=><>{children}</>,ReactFlow:({nodes,onNodeClick}:{nodes:{id:string;data:{label:string;state:string}}[];onNodeClick:(event:unknown,node:unknown)=>void})=><div>{nodes.map(n=><button key={n.id} data-state={n.data.state} onClick={()=>onNodeClick(null,n)}>{n.data.label}</button>)}</div>,Background:()=>null,Controls:()=>null,Handle:()=>null,useNodesInitialized:()=>false,useReactFlow:()=>({fitView:()=>{}}),Position:{Left:'left',Right:'right'},MarkerType:{ArrowClosed:'closed'}}));
function scope(workspace:string){useBackend.setState({session:{auth:{subject:{workspace_id:workspace,subject_id:'owner'}}} as never});}
beforeEach(()=>{vi.restoreAllMocks();scope('simpsons');vi.spyOn(api,'runKnowledge').mockResolvedValue({projections:[],qualification:'Saved references'});});
afterEach(cleanup);
it('loads the authorized version, supports steps, node details and relationship navigation',async()=>{
 const f=knowledgeFixture();vi.spyOn(api,'businessOntology').mockResolvedValue(f.ontology);vi.spyOn(api,'knowledgeSnapshot').mockResolvedValue(f.snapshot);
 render(<KnowledgeMap doc={f.doc} view={f.view}/>);
 await screen.findByRole('heading',{name:'The knowledge behind this workflow'});
 fireEvent.click(screen.getByRole('button',{name:'Complaint'}));expect(await screen.findByText('simpsons business definition for Complaint.')).toBeVisible();
 expect(screen.getByText('simpsons_records')).toBeVisible();
 fireEvent.click(screen.getByRole('button',{name:/Concerns.*Related Complaint/}));expect(await screen.findByText('simpsons business definition for Related Complaint.')).toBeVisible();
 fireEvent.click(screen.getByRole('button',{name:'Full ontology'}));fireEvent.change(screen.getByLabelText('Search ontology concepts'),{target:{value:'Related'}});
 expect(screen.queryByRole('button',{name:'Complaint'})).toBeNull();expect(api.knowledgeSnapshot).toHaveBeenCalledWith('simpsons_v1');
});
it('clears overlapping IDs and node selection on account changes and discards late responses',async()=>{
 const a=knowledgeFixture();const b=knowledgeFixture('subway','Purchase order');let finish!:(v:typeof a.snapshot)=>void;
 vi.spyOn(api,'businessOntology').mockResolvedValueOnce(a.ontology).mockResolvedValue(b.ontology);
 vi.spyOn(api,'knowledgeSnapshot').mockImplementationOnce(()=>new Promise(resolve=>{finish=resolve;})).mockResolvedValue(b.snapshot);
 const {rerender}=render(<KnowledgeMap doc={a.doc} view={a.view}/>);
 await act(async()=>{});act(()=>scope('subway'));rerender(<KnowledgeMap doc={b.doc} view={b.view}/>);
 await screen.findByRole('button',{name:'Purchase order'});await act(async()=>finish(a.snapshot));
 expect(screen.queryByRole('button',{name:'Complaint'})).toBeNull();expect(screen.queryByText('simpsons_records')).toBeNull();
});
it('rejects a mismatched workflow scope before requesting ontology data',()=>{
 const f=knowledgeFixture('subway','Purchase order');const read=vi.spyOn(api,'businessOntology');render(<KnowledgeMap doc={f.doc} view={f.view}/>);
 expect(screen.getByText('Knowledge is unavailable in this workspace.')).toBeVisible();expect(read).not.toHaveBeenCalled();
});
it('labels current ontology fallback and never upgrades it to historical execution',async()=>{
 const f=knowledgeFixture();vi.spyOn(api,'businessOntology').mockResolvedValue(f.ontology);vi.spyOn(api,'knowledgeSnapshot').mockRejectedValueOnce(new Error('Historical version unavailable')).mockResolvedValue(f.snapshot);
 render(<KnowledgeMap doc={f.doc} view={f.view}/>);
 await screen.findByText('Current ontology shown. Historical ontology version unavailable.');
 fireEvent.click(screen.getByRole('button',{name:'Complaint'}));expect(screen.queryByText(/Executed ·/)).toBeNull();
});

it('shows direct context separately and clears it when another step is selected',async()=>{
 const f=knowledgeFixture();const a=f.doc.action_plan.actions[0]!;
 f.doc.action_plan.actions.push({...a,action_id:'other',evidence_references:[]});
 vi.spyOn(api,'businessOntology').mockResolvedValue(f.ontology);vi.spyOn(api,'knowledgeSnapshot').mockResolvedValue(f.snapshot);
 render(<KnowledgeMap doc={f.doc} view={f.view}/>);
 const neighbour=await screen.findByRole('button',{name:'Related Complaint'});
 expect(neighbour).toHaveAttribute('data-state','context');
 expect(screen.getByRole('button',{name:'Complaint'})).toHaveAttribute('data-state','executed');
 expect(screen.getByText('1 with recorded execution evidence')).toBeVisible();
 fireEvent.click(neighbour);expect(screen.getByRole('heading',{name:'Connected context'})).toBeVisible();
 expect(screen.getByText(/This connection does not establish/)).toBeVisible();
 fireEvent.click(screen.getByRole('button',{name:'Full ontology'}));
 fireEvent.change(screen.getByLabelText('Knowledge workflow step'),{target:{value:'other'}});
 expect(screen.getByRole('button',{name:'Related Complaint'})).toHaveAttribute('data-state','available');
});
