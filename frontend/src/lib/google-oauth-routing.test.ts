import {afterEach,beforeEach,expect,it,vi} from 'vitest';
import {NextRequest} from 'next/server';
import {GET,POST} from '@/app/api/backend/[...path]/route';
import {googleRouteCookie,googleRouteAccount,GOOGLE_ROUTE_COOKIE} from './google-oauth-routing';
import {createClientSession,WORKSPACE_COOKIE} from './workspace-auth';
const base='http://127.0.0.1:3001/api/backend/';
const callback='integrations/google/callback';
const state='a'.repeat(43);
const context=(path:string)=>({params:Promise.resolve({path:path.split('/')})});
beforeEach(()=>{
 vi.stubEnv('BUILDER_LOGIN_SECRET','test-google-routing-secret-at-least-32-chars');
 for(const [client,port] of [['simpsons','8020'],['subway','8021']]){
  vi.stubEnv(`BUILDER_${client!.toUpperCase()}_API_URL`,'http://127.0.0.1:'+port);
  vi.stubEnv(`BUILDER_${client!.toUpperCase()}_PROXY_SECRET`,client+'-test-proxy-secret-at-least-32-chars');
 }
});
afterEach(()=>{vi.unstubAllGlobals();vi.unstubAllEnvs();});
it('rejects changed state, expiry and routing signature',()=>{
 const route=googleRouteCookie('subway',state);
 expect(googleRouteAccount(route,state)).toBe('subway');
 expect(googleRouteAccount(route,'b'.repeat(43))).toBeNull();
 expect(googleRouteAccount(route,state,Date.now()+601000)).toBeNull();
 expect(googleRouteAccount(route.replace('subway','simpsons'),state)).toBeNull();
});
it.each(['simpsons','subway'] as const)('keeps %s OAuth cookies and routes return without login to its initiating backend',async(client)=>{
 const authURL='https://accounts.google.com/o/oauth2/v2/auth?'+new URLSearchParams({state,redirect_uri:base+callback});
 const fetch=vi.fn().mockResolvedValueOnce(new Response(JSON.stringify({request_id:'oauth',status:200,data:{authorization_url:authURL}}),{headers:{'x-builder-client':client,'set-cookie':'builder_google_oauth=bound; Path=/api/backend/integrations/google; HttpOnly; SameSite=Lax'}})).mockResolvedValueOnce(new Response(null,{status:303,headers:{'x-builder-client':client,location:'http://127.0.0.1:3001/app/integrations?google=connected','set-cookie':'builder_google_oauth=; Path=/api/backend/integrations/google; Max-Age=0'}}));vi.stubGlobal('fetch',fetch);
 const result=await POST(new NextRequest(base+'integrations/google/authorize',{method:'POST',headers:{host:'127.0.0.1:3001',cookie:`${WORKSPACE_COOKIE}=${createClientSession(client)}`,origin:'http://127.0.0.1:3001','content-type':'application/json'},body:JSON.stringify({capabilities:['gmail_send']})}),context('integrations/google/authorize'));
 expect(result.status).toBe(200);
 const cookies=result.headers.getSetCookie();expect(cookies.some(c=>c.startsWith('builder_google_oauth=bound'))).toBe(true);
 const route=cookies.find(c=>c.startsWith(GOOGLE_ROUTE_COOKIE+'='))!.split(';')[0];
 // An intervening login to another tenant must not redirect the code to that tenant.
 const returned=await GET(new NextRequest(base+callback+'?state='+state+'&code=provider-code',{headers:{host:'127.0.0.1:3001',cookie:route+'; builder_google_oauth=bound; '+WORKSPACE_COOKIE+'='+createClientSession(client==='subway'?'simpsons':'subway'),'sec-fetch-site':'cross-site'}}),context(callback));
 expect(returned.status).toBe(303);
 expect(String(fetch.mock.calls[1]![0])).toContain(client==='simpsons'?':8020/':':8021/');
 expect(new Headers(fetch.mock.calls[1]![1].headers).get('cookie')).toBe('builder_google_oauth=bound');
 expect(returned.headers.getSetCookie().some(c=>c.startsWith(GOOGLE_ROUTE_COOKIE+'=;'))).toBe(true);
});
it('never forwards a callback code with forged routing evidence',async()=>{
 const fetch=vi.fn();vi.stubGlobal('fetch',fetch);
 const response=await GET(new NextRequest(base+callback+'?state='+state+'&code=private-code',{headers:{host:'127.0.0.1:3001',cookie:GOOGLE_ROUTE_COOKIE+'='+googleRouteCookie('subway',state).replace('subway','simpsons')}}),context(callback));
 expect(response.status).toBe(400);expect(fetch).not.toHaveBeenCalled();
});
