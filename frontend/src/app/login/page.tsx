import { cookies } from "next/headers";
import { redirect } from "next/navigation";
import { validWorkspaceSession, WORKSPACE_COOKIE } from "@/lib/workspace-auth";
import Login from "@/screens/login";

export const dynamic = "force-dynamic";
export default async function LoginPage() {
  if (validWorkspaceSession((await cookies()).get(WORKSPACE_COOKIE)?.value)) redirect("/app");
  return <Login />;
}
