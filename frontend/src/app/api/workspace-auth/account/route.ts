import { NextRequest,NextResponse } from 'next/server';
import { workspaceAccount,WORKSPACE_COOKIE,WORKSPACE_EMAIL } from '@/lib/workspace-auth';
export async function GET(request:NextRequest) {
 const account=workspaceAccount(request.cookies.get(WORKSPACE_COOKIE)?.value);
 if(!account)return NextResponse.json({error:'Sign in required.'},{status:401,headers:{'Cache-Control':'no-store'}});
 const email=account==='operator'?WORKSPACE_EMAIL:process.env[`BUILDER_${account.toUpperCase()}_LOGIN_EMAIL`];
 return NextResponse.json({email:email??null,account,status:'authenticated',password_change:{available:false,reason:'Passwords are managed through secured deployment configuration. Self-service password changes are unavailable; contact your workspace administrator.'}},{headers:{'Cache-Control':'no-store'}});
}
