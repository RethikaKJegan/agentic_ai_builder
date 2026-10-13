import { expect, it, vi } from "vitest";
import { api, WorkflowClient } from "./client";

it("exports the real activation method and posts the reviewed policy with its exact owner", async () => {
  expect(typeof api.procurementFulfilmentActivate).toBe("function");
  const transport = vi.fn<typeof fetch>().mockResolvedValue(new Response(JSON.stringify({
    request_id: "req_test", status: 200, data: { project_id: "project_demo", phase: "FULFILMENT" },
  }), { status: 200 }));
  const client = new WorkflowClient(transport);
  const settings = { enabled: true as const, buyer_email: "buyer@example.com", manager_email: "manager@example.com",
    acceptance_hours: 24, reminder_hours: 24, allow_delivery_reschedule: false };
  await expect(client.procurementFulfilmentActivate("project_demo", "workflow_demo", 1, 0, settings))
    .resolves.toMatchObject({ phase: "FULFILMENT" });
  expect(transport).toHaveBeenCalledOnce();
  const [url, options] = transport.mock.calls[0]!;
  expect(url).toBe("/api/backend/procurement/projects/project_demo/fulfilment-activate");
  expect(options?.method).toBe("POST");
  expect(options?.credentials).toBe("same-origin");
  expect(JSON.parse(options?.body as string)).toMatchObject({ operation: "procurement_fulfilment_activate",
    payload: { settings, workflow_id: "workflow_demo", workflow_version: 1, expected_revision: 0 } });
});
