/** Server-only, purpose-separated callback routing; grants no workspace session. */
import {createHash,createHmac,timingSafeEqual} from 'node:crypto';
import type {WorkspaceAccount} from './workspace-auth';
export const GOOGLE_ROUTE_COOKIE='builder_google_route';
export const GOOGLE_CALLBACK_PATH='/api/backend/integrations/google/callback';
function mac(value:string){
 const key=process.env['BUILDER_LOGIN_SECRET'];
 if(!key||key.length<32)throw new Error('Configure workspace signing key.');
 return createHmac('sha256',key).update('google-oauth-route:'+value).digest('hex');
}
const hash=(state:string)=>createHash('sha256').update(state).digest('hex');
export function googleRouteCookie(account:WorkspaceAccount,state:string,now=Date.now()){
 if(!/^[a-zA-Z0-9_-]{32,200}$/.test(state))throw new Error('Invalid OAuth state.');
 const value=`${account}.${Math.floor(now/1000)+600}.${hash(state)}`;
 return `${value}.${mac(value)}`;
}
export function googleRouteAccount(value:string,state:string,now=Date.now()):WorkspaceAccount|null{
 if(!/^(operator|simpsons|subway)\.\d{10}\.[a-f0-9]{64}\.[a-f0-9]{64}$/.test(value)||!/^[a-zA-Z0-9_-]{32,200}$/.test(state))return null;
 const [account,expires,digest,signature]=value.split('.');const remaining=Number(expires)-Math.floor(now/1000);
 if(remaining<=0||remaining>600||digest!==hash(state))return null;
 try{return timingSafeEqual(Buffer.from(signature!,'hex'),Buffer.from(mac(value.slice(0,value.lastIndexOf('.'))),'hex'))?account as WorkspaceAccount:null;}catch{return null;}
}
