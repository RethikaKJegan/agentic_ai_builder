"use client";

export function CustomerAutomationReview({ policy, emailPolicy }: { policy: unknown; emailPolicy: unknown }) {
  if (!policy || typeof policy !== "object" || !("mode" in policy) || policy.mode !== "automatic") return null;
  const manager = "manager_email" in policy ? String(policy.manager_email) : "Not configured";
  const field = emailPolicy && typeof emailPolicy === "object" && "field" in emailPolicy ? String(emailPolicy.field) : "Not configured";
  return <details className="relative">
    <summary className="cursor-pointer rounded-lg border px-2.5 py-1 text-sm">Automatic email policy</summary>
    <div className="absolute right-0 top-10 z-40 w-80 space-y-2 rounded-xl border bg-background p-4 shadow-lg">
      <p className="text-sm font-medium">Publishing authorizes routine customer emails.</p>
      <p className="text-sm">Customer address comes from: {field}</p>
      <p className="text-sm">Manager notifications go to: {manager}</p>
      <p className="text-sm">Replies receive automatic follow-ups or escalation. Closure requires an explicit customer confirmation.</p>
      <p className="text-sm">Refunds and replacements need manager authorization. Spreadsheets stay read-only.</p>
    </div>
  </details>;
}
