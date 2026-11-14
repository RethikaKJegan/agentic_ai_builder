import { existsSync, mkdirSync, writeFileSync } from "node:fs";
import { join } from "node:path";
/** Server-side only. Never import into client components. */
import { createHash, createHmac, randomBytes, scrypt, timingSafeEqual } from "node:crypto";
import { promisify } from "node:util";

export const WORKSPACE_COOKIE = "builder_workspace_access";
export const WORKSPACE_EMAIL = "engineering@bellcorpstudio.com";
export const SESSION_SECONDS = 8 * 60 * 60;
const derive = promisify(scrypt);

function signingKey() {
  const key = process.env["BUILDER_LOGIN_SECRET"];
  if (!key || key.length < 32) throw new Error("Configure BUILDER_LOGIN_SECRET with at least 32 random characters.");
  return key;
}
function signature(value: string) {
  return createHmac("sha256", signingKey()).update(value).digest("hex");
}
export function createWorkspaceSession(now = Date.now()) {
  const payload = `${Math.floor(now / 1000) + SESSION_SECONDS}.${randomBytes(24).toString("hex")}`;
  return `${payload}.${signature(payload)}`;
}
export type DedicatedClient = "simpsons" | "subway";
export type WorkspaceAccount = "operator" | DedicatedClient;
export function createClientSession(account: WorkspaceAccount, now = Date.now()) {
  if (account === "operator") return createWorkspaceSession(now);
  const payload = `${account}.${Math.floor(now / 1000) + SESSION_SECONDS}.${randomBytes(24).toString("hex")}`;
  return `${payload}.${signature(payload)}`;
}
function revocationPath(value:string) {
  return join(process.env['BUILDER_AUTH_STATE_DIR']||join(process.cwd(),'.local','auth-revocations'),createHash('sha256').update(value).digest('hex'));
}
export function revokeWorkspaceSession(value:string|undefined) {
  if(!value||!workspaceAccount(value))return;
  const root=process.env['BUILDER_AUTH_STATE_DIR']||join(process.cwd(),'.local','auth-revocations');
  mkdirSync(root,{recursive:true,mode:0o700});
  try{writeFileSync(revocationPath(value),'revoked\n',{mode:0o600,flag:'wx'});}catch(error){if((error as NodeJS.ErrnoException).code!=='EEXIST')throw error;}
}
export function workspaceAccount(value: string | undefined, now = Date.now()): WorkspaceAccount | null {
  if(value&&(value.length>256||existsSync(revocationPath(value))))return null;
  if (!value) return null;
  if (/^(simpsons|subway)\.\d{10}\.[a-f0-9]{48}\.[a-f0-9]{64}$/.test(value)) {
    const parts = value.split(".");
    const remaining = Number(parts[1]) - Math.floor(now / 1000);
    if (remaining <= 0 || remaining > SESSION_SECONDS) return null;
    try {
      return timingSafeEqual(Buffer.from(parts[3]!, "hex"), Buffer.from(signature(parts.slice(0, 3).join(".")), "hex")) ? parts[0] as DedicatedClient : null;
    } catch { return null; }
  }
  return validOperatorSession(value, now) ? "operator" : null;
}
export function clientAssertion(client: DedicatedClient = "simpsons") {
  const key = process.env[`BUILDER_${client.toUpperCase()}_PROXY_SECRET`];
  if (!key || key.length < 32) throw new Error("Configure the Simpsons proxy secret.");
  const payload = `${client}.${Math.floor(Date.now() / 1000) + 60}.${randomBytes(24).toString("hex")}`;
  return `${payload}.${createHmac("sha256", key).update(payload).digest("hex")}`;
}
export function validWorkspaceSession(value: string | undefined, now = Date.now()) {
  return workspaceAccount(value, now) !== null;
}
function validOperatorSession(value: string | undefined, now = Date.now()) {
  if (!value || !/^\d{10}\.[a-f0-9]{48}\.[a-f0-9]{64}$/.test(value)) return false;
  const [expires, nonce, mac] = value.split(".");
  const remaining = Number(expires) - Math.floor(now / 1000);
  if (remaining <= 0 || remaining > SESSION_SECONDS) return false;
  try {
    return timingSafeEqual(Buffer.from(mac!, "hex"), Buffer.from(signature(`${expires}.${nonce}`), "hex"));
  } catch { return false; }
}
export async function authenticateWorkspace(email: unknown, password: unknown): Promise<WorkspaceAccount | null> {
  // Configuration failures fail closed, never fall back to browser-only authentication.
  signingKey();
  if (typeof email !== "string" || typeof password !== "string" || password.length > 128) return null;
  const normalized = email.trim().toLowerCase();
  const clients: DedicatedClient[] = ['simpsons', 'subway'];
  const emails = clients.map(client => process.env[`BUILDER_${client.toUpperCase()}_LOGIN_EMAIL`]?.trim().toLowerCase());
  const configured = emails.filter((value): value is string => !!value);
  if (configured.includes(WORKSPACE_EMAIL) || new Set(configured).size !== configured.length) throw new Error("Client and operator accounts must differ.");
  const index = emails.findIndex(value => !!value && normalized === value);
  const account: WorkspaceAccount = index >= 0 ? clients[index]! : "operator";
  const encoded = process.env[account !== "operator" ? `BUILDER_${account.toUpperCase()}_LOGIN_PASSWORD_HASH` : "BUILDER_LOGIN_PASSWORD_HASH"] || "";
  if (!/^[a-f0-9]{32}:[a-f0-9]{128}$/.test(encoded)) throw new Error("Configure BUILDER_LOGIN_PASSWORD_HASH.");
  const [salt, hash] = encoded.split(":");
  const actual = await derive(password, salt!, 64) as Buffer;
  return timingSafeEqual(actual, Buffer.from(hash!, "hex")) && normalized === (account !== "operator" ? emails[index] : WORKSPACE_EMAIL) ? account : null;
}
export async function verifyWorkspacePassword(email: unknown, password: unknown) {
  return (await authenticateWorkspace(email, password)) !== null;
}
