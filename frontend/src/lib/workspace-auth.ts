/** Server-side only. Never import into client components. */
import { createHmac, randomBytes, scrypt, timingSafeEqual } from "node:crypto";
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
export function validWorkspaceSession(value: string | undefined, now = Date.now()) {
  if (!value || !/^\d{10}\.[a-f0-9]{48}\.[a-f0-9]{64}$/.test(value)) return false;
  const [expires, nonce, mac] = value.split(".");
  const remaining = Number(expires) - Math.floor(now / 1000);
  if (remaining <= 0 || remaining > SESSION_SECONDS) return false;
  try {
    return timingSafeEqual(Buffer.from(mac!, "hex"), Buffer.from(signature(`${expires}.${nonce}`), "hex"));
  } catch { return false; }
}
export async function verifyWorkspacePassword(email: unknown, password: unknown) {
  // Configuration failures fail closed, never fall back to browser-only authentication.
  signingKey();
  const encoded = process.env["BUILDER_LOGIN_PASSWORD_HASH"] || "";
  if (!/^[a-f0-9]{32}:[a-f0-9]{128}$/.test(encoded)) throw new Error("Configure BUILDER_LOGIN_PASSWORD_HASH.");
  if (typeof email !== "string" || typeof password !== "string" || password.length > 128) return false;
  const [salt, hash] = encoded.split(":");
  const actual = await derive(password, salt!, 64) as Buffer;
  return timingSafeEqual(actual, Buffer.from(hash!, "hex")) && email.trim().toLowerCase() === WORKSPACE_EMAIL;
}
