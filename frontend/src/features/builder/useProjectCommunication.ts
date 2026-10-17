import { useEffect, useState } from 'react';
import { api } from '@/api/client';
import type { ProjectCommunication } from '@/domain/procurement-communication';
export function useProjectCommunication(workflowId:string,version:number) {
  const [state,setState]=useState<{key:string;project:ProjectCommunication;status?: Awaited<ReturnType<typeof api.procurementStatus>> | undefined}>();
  const [error,setError]=useState<Error>();
  const [attempt,setAttempt]=useState(0);
  const key=workflowId+':'+version;
  useEffect(()=>{
    let disposed=false;let timer:ReturnType<typeof setTimeout>;
    const refresh=async()=>{
      try {const project=await api.procurementProjectCommunication(workflowId,version);const status=project.root_workflow.metadata?.['procurement_plan']?await api.procurementStatus(project.project_id).catch(()=>undefined):undefined;if(!disposed){setState({key,project,status});setError(undefined);}}
      catch(e){if(!disposed)setError(e instanceof Error?e:new Error('Project view could not be loaded.'));}
      finally {if(!disposed)timer=setTimeout(()=>void refresh(),8000);}
    };
    void refresh();return()=>{disposed=true;clearTimeout(timer);};
  },[workflowId,version,key,attempt]);
  return {project:state?.key===key?state.project:undefined,status:state?.key===key?state.status:undefined,error,retry:()=>setAttempt(n=>n+1)};
}
