import {act,fireEvent,render,screen,waitFor} from '@testing-library/react';
import {afterEach,expect,it,vi} from 'vitest';
import {api} from '@/api/client';
import {businessCompilationSchema} from '@/api/business-ontology';
import BusinessCompilationPanel from './BusinessCompilationPanel';

function result(version='v2',revision=2){return businessCompilationSchema.parse({compilation:{version_id:version,compiler_version:'simpson-owl-shacl-v1',input_sha256:'input_hash',compiled_at:'2026-10-31',report:{status:'passed',compiler_version:'simpson-owl-shacl-v1',version_id:version,revision,checks:{rdf_syntax:'passed',shapes_meta_shacl:'passed',definition_shacl:'passed'},definition_conforms:true,instance_validation:'not_run',owl_reasoning:'not_run',business_policy_verified:false,counts:{concepts:2},issues:[],warnings:[{code:'REFERENCE_TARGET_UNSPECIFIED',focus:'warranty:engine',message:'Reference target is unspecified.'}]},artifacts:[{name:'ontology.ttl',media_type:'text/turtle',content:'<urn:engine> a <http://www.w3.org/2002/07/owl#Class> .\n',sha256:'artifact_hash'}]}});}
afterEach(()=>vi.restoreAllMocks());
it('loads a selected version without compiling until explicitly requested',async()=>{
 const load=vi.spyOn(api,'businessCompilation').mockResolvedValue({compilation:null});
 const compile=vi.spyOn(api,'compileBusinessVersion').mockResolvedValue(result());
 render(<BusinessCompilationPanel versionId="v2" revision={2} kind="draft" canManage/>);
 const button=await screen.findByRole('button',{name:'Compile & validate version'});await waitFor(()=>expect(button).toBeEnabled());
 expect(load).toHaveBeenCalledWith('v2');expect(compile).not.toHaveBeenCalled();fireEvent.click(button);
 expect(await screen.findByText('Definition validation passed · Revision 2')).toBeVisible();expect(compile).toHaveBeenCalledExactlyOnceWith('v2');
 expect(screen.getByText(/This compilation validates definitions only/)).toBeVisible();
 fireEvent.click(screen.getByText(/Unresolved information and mapping limits/));expect(screen.getByText('Reference target is unspecified.')).toBeVisible();
});
it('allows viewers to download saved artifacts without mutation controls',async()=>{
 vi.spyOn(api,'businessCompilation').mockResolvedValue(result());const compile=vi.spyOn(api,'compileBusinessVersion');
 const create=vi.fn(()=> 'blob:artifact');Object.defineProperty(URL,'createObjectURL',{value:create,configurable:true});Object.defineProperty(URL,'revokeObjectURL',{value:vi.fn(),configurable:true});
 const click=vi.spyOn(HTMLAnchorElement.prototype,'click').mockImplementation(()=>{});
 render(<BusinessCompilationPanel versionId="v2" revision={2} kind="draft" canManage={false}/>);
 fireEvent.click(await screen.findByRole('button',{name:'Download Ontology (Turtle)'}));expect(create).toHaveBeenCalledWith(expect.any(Blob));expect(click).toHaveBeenCalledTimes(1);
 const anchor=click.mock.instances[0] as HTMLAnchorElement;expect(anchor.download).toBe('simpson-revision-2-ontology.ttl');
 expect(screen.queryByRole('button',{name:'Compile & validate version'})).not.toBeInTheDocument();expect(compile).not.toHaveBeenCalled();
});
it('never presents failed checks as passed and recovers a failed load',async()=>{
 const failed=result();failed.compilation!.report.status='failed';failed.compilation!.report.definition_conforms=false;failed.compilation!.report.issues=[{focus:'Engine',path:'label',message:'A label is missing.'}];
 const load=vi.spyOn(api,'businessCompilation').mockRejectedValueOnce(new Error('Unavailable')).mockResolvedValueOnce(failed);
 render(<BusinessCompilationPanel versionId="v2" revision={2} kind="draft" canManage={false}/>);
 expect(await screen.findByRole('alert')).toBeVisible();fireEvent.click(screen.getByRole('button',{name:'Retry read'}));
 expect(await screen.findByText('Definition validation failed · Revision 2')).toBeVisible();expect(screen.getByText('A label is missing.')).toBeVisible();expect(load).toHaveBeenCalledTimes(2);
});
it('discards late reports when switching versions',async()=>{
 let finish:(value:ReturnType<typeof result>)=>void=()=>{};
 vi.spyOn(api,'businessCompilation').mockImplementation(id=>id==='v2'?new Promise(resolve=>{finish=resolve;}):Promise.resolve({compilation:null}));
 const view=render(<BusinessCompilationPanel versionId="v2" revision={2} kind="draft" canManage/>);
 view.rerender(<BusinessCompilationPanel versionId="v1" revision={1} kind="foundation" canManage/>);
 expect(await screen.findByText('Generate a module draft before compiling this version.')).toBeVisible();
 await act(async()=>finish(result()));expect(screen.queryByText(/Definition validation passed/)).not.toBeInTheDocument();
 expect(screen.queryByRole('button',{name:'Download Ontology (Turtle)'})).not.toBeInTheDocument();
});
it('retains the explicit action after a compilation failure without automatic retry',async()=>{
 vi.spyOn(api,'businessCompilation').mockResolvedValue({compilation:null});const compile=vi.spyOn(api,'compileBusinessVersion').mockRejectedValue(new Error('Invalid source evidence'));
 render(<BusinessCompilationPanel versionId="v2" revision={2} kind="draft" canManage/>);
 const button=await screen.findByRole('button',{name:'Compile & validate version'});await waitFor(()=>expect(button).toBeEnabled());fireEvent.click(button);
 expect(await screen.findByRole('alert')).toBeVisible();expect(compile).toHaveBeenCalledTimes(1);expect(button).toBeEnabled();
});
