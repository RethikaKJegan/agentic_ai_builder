import { test, expect, type Page } from "@playwright/test";
import { createHmac, randomBytes } from "node:crypto";
import { mkdirSync, writeFileSync } from "node:fs";
import path from "node:path";
const evidenceRoot = path.resolve(import.meta.dirname, "../../.local/frontend-phase4-evidence");
const origin = "http://127.0.0.1:3247";
async function login(page: Page) {
  const payload = `${Math.floor(Date.now() / 1000) + 3600}.${randomBytes(24).toString("hex")}`;
  await page
    .context()
    .addCookies([
      {
        name: "builder_workspace_access",
        value: `${payload}.${createHmac("sha256", process.env["BUILDER_LOGIN_SECRET"]!).update(payload).digest("hex")}`,
        domain: "127.0.0.1",
        path: "/",
      },
    ]);
  await page.request.get("/api/backend/session");
}
async function control(page: Page, path: string) {
  const cookies = await page.context().cookies();
  const r = await page.request.post("http://127.0.0.1:8028/__test/" + path, {
    headers: { Origin: origin, Cookie: cookies.map((c) => c.name + "=" + c.value).join("; ") },
  });
  expect(r.ok(), await r.text()).toBe(true);
  return r.json();
}
async function snapshot(page: Page, id: string) {
  const r = await page.request.get("/api/backend/business-ontology/v1/cases/" + id);
  expect(r.ok()).toBe(true);
  return (await r.json()).data;
}
async function startCase(page: Page, kind: string, missing = false) {
  await login(page);
  const setup = await control(page, "scenario/" + kind);
  await page.goto("/app/workflows/investigate?case=" + setup.case_id);
  await page.getByLabel("Adaptive ready stage").selectOption("first");
  const values = { ...setup.values, inspection_task: "inspection" };
  if (missing) delete values.recipient;
  await page.getByLabel("Adaptive user values").fill(JSON.stringify(values));
  await page.getByRole("button", { name: "Enable adaptive planning" }).click();
  await expect(page.getByLabel("Five-state orchestration")).toBeVisible();
  return setup;
}
async function advanceCase(
  page: Page,
  id: string,
  until: "wait" | "complete" | "input" | "blocked" = "complete",
) {
  const panel = page.getByRole("region", { name: "Adaptive case orchestration" });
  for (let i = 0; i < 28; i++) {
    const c = await snapshot(page, id);
    const a = c.adaptive;
    if (a.pending_wait && (until === "wait" || until === "input")) return c;
    if (a.status === "completed" || (until === "blocked" && a.status === "blocked")) return c;
    const review = panel.getByRole("button", { name: "Approve workflow", exact: true });
    const validate = panel.getByRole("button", { name: "Validate workflow", exact: true });
    const save = panel.getByRole("button", { name: "Save workflow draft", exact: true });
    const approve = panel.getByRole("button", { name: "Approve exact payload", exact: true });
    if ((await review.count()) && (await review.isEnabled())) {
      await review.click();
      await expect(review).toHaveCount(0);
    } else if ((await validate.count()) && (await validate.isEnabled())) {
      await validate.click();
      await expect(validate).toHaveCount(0);
    } else if ((await save.count()) && (await save.isEnabled())) {
      await save.click();
      await expect(save).toHaveCount(0);
    } else if ((await approve.count()) && (await approve.first().isEnabled())) {
      await panel.getByText("Actual action payload", { exact: true }).click();
      await expect(panel.getByText("Actual action payload", { exact: true })).toBeVisible();
      await approve.first().click();
      await expect(approve).toHaveCount(0);
    } else {
      const drive = panel.getByRole("button", { name: "Continue bounded evaluation" });
      await expect(drive).toBeEnabled();
      await Promise.all([page.waitForResponse(response=>response.request().method()==="POST"&&response.url().endsWith("/drive")),drive.click()]);
      await expect(panel.getByRole("button", { name: "Refresh adaptive state" })).toBeEnabled();
    }
    await panel.getByRole("button", { name: "Refresh adaptive state" }).click();
  }
  throw new Error("Bounded case did not reach expected state");
}
for (const mobile of [false, true])
  test(`A: real API, approved report/email, persisted reply continuation ${mobile ? "mobile" : "desktop"}`, async ({
    page,
  }) => {
    if (mobile) await page.setViewportSize({ width: 390, height: 844 });
    const errors: string[] = [];
    page.on("pageerror", (e) => errors.push(e.message));
    const setup = await startCase(page, "reply");
    const waiting = await advanceCase(page, setup.case_id, "wait");
    expect(waiting.adaptive.pending_wait.kind).toBe("event");
    const run = await page.request.get(
      "/api/backend/business-ontology/v1/compositions/" +
        waiting.adaptive.composition_id +
        "/view?run_id=" +
        waiting.adaptive.run_id,
    );
    const record = (await run.json()).data.run;
    const receipt = record["action_instances"]["send"]["output"];
    await page.reload();
    await expect(page.getByText("Waiting for external evidence", { exact: true })).toBeVisible();
    const automation = page.getByRole("region", { name: "Background automation" });
    await automation.getByText("Configure reviewed automation").click();
    await automation.getByLabel("Automation type").selectOption("subscriptions");
    await automation.getByLabel("Workflow Google account").selectOption(setup.connection_id);
    await automation
      .getByLabel("Approved workflow revision")
      .selectOption(waiting.stages.first.workflow.workflow_id + ":1");
    await automation.getByLabel("Deadline").fill(new Date(Date.now() + 7 * 86400000).toISOString());
    await automation.getByLabel("Business purpose").fill("Field inspection findings");
    await automation.getByLabel("Expected reply senders").fill("engineer@example.com");
    await automation.getByLabel("Gmail thread ID").fill(receipt.thread_id);
    await automation.getByLabel("Sent Gmail message ID").fill(receipt.message_id);
    await automation.getByLabel("Sent RFC Message-ID").fill(receipt.rfc_message_id);
    await automation.getByLabel("Reply field mapping").fill('{"finding":"text"}');
    await automation.getByRole("button", { name: "Review automation scope" }).click();
    await automation.getByRole("button", { name: "Confirm reviewed automation" }).click();
    await expect(automation.getByText(/Saved subscription:/)).toBeVisible();
    await control(page, "reply");
    await page.reload();
    const finished = await snapshot(page, setup.case_id);
    expect(finished.adaptive.status).toBe("completed");
    await expect(page.getByText(/EVALUATE · completed/)).toBeVisible();
    expect(finished.adaptive.run_id).toBe(waiting.adaptive.run_id);
    await page.getByRole("tab",{name:"steps",exact:true}).click();
    await expect(page.getByRole("link", { name: /Open verified artifact/ }).first()).toBeVisible();
    expect(errors).toEqual([]);
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(
      true,
    );
    mkdirSync(evidenceRoot, { recursive: true });
    writeFileSync(
      path.join(evidenceRoot, `reply-${mobile ? "mobile" : "desktop"}.json`),
      JSON.stringify({ case: finished, run: record }, null, 2),
    );
    await page.screenshot({
      path: path.join(evidenceRoot, `reply-${mobile ? "mobile" : "desktop"}.png`),
      fullPage: true,
    });
  });
test("C: actual missing-recipient wait, typed supply and completion", async ({ page }) => {
  const setup = await startCase(page, "missing", true);
  await advanceCase(page, setup.case_id, "input");
  await page.getByLabel("Requested recipient").fill("engineer@example.com");
  await page.getByRole("button", { name: "Supply requested information" }).click();
  await expect(page.getByLabel("Requested recipient")).toHaveCount(0);
  const done = await advanceCase(page, setup.case_id);
  expect(done.adaptive.status).toBe("completed");
});
test("D: evaluator adds retrieval, revises plan and preserves the completed read", async ({
  page,
}) => {
  const setup = await startCase(page, "gather");
  const done = await advanceCase(page, setup.case_id);
  expect(done.adaptive.plan_revision).toBe(2);
  expect(done.adaptive.revision_history).toHaveLength(2);
  await page.getByRole("tab",{name:"steps",exact:true}).click();
  await expect(page.getByText(/more_evidence/).first()).toBeVisible();
  const run = (
    await (
      await page.request.get(
        "/api/backend/business-ontology/v1/compositions/" +
          done.adaptive.composition_id +
          "/view?run_id=" +
          done.adaptive.run_id,
      )
    ).json()
  ).data.run;
  expect(run.action_instances.read.state).toBe("completed");
  expect(run.action_instances.more_evidence.verified_receipt).toBe(true);
});
test("B: prompt planning, reviewed recurring consent and two fresh occurrences", async ({
  page,
}) => {
  await login(page);
  const setup = await control(page, "scenario/daily");
  await page.goto("/app/workflows/investigate?connected=1");
  await page
    .getByLabel("Business goal")
    .fill("Investigate complaint C123, create a report and email engineer@example.com the findings daily.");
  await page.getByLabel("Workflow Google account").first().selectOption(setup.connection_id);
  await expect(page.getByLabel("Explicit user values")).toHaveCount(0);
  await expect(page.getByLabel("Optional connected action")).toHaveCount(0);
  await page.getByRole("button", { name: "Propose connected plan" }).click();
  await expect(page.getByRole("heading", { name: "Investigation workflow" })).toBeVisible();
  await page.getByRole("button", { name: "Review plan", exact: true }).click();
  await page.getByRole("button", { name: "Approve workflow", exact: true }).click();
  const currentPlanId=new URL(page.url()).searchParams.get('composition');
  const planResponse=await page.request.get('/api/backend/business-ontology/v1/action-plans/'+currentPlanId);
  expect(planResponse.ok()).toBe(true);const approvedPlan=(await planResponse.json()).data;
  const reportAction=approvedPlan.action_plan.actions.find((action:{action_id:string})=>action.action_id==='sheet');
  const projectBinding=reportAction.bindings.find((binding:{target:string[]})=>binding.target.join('.')==='project_id');
  const reportProject=approvedPlan.binding_context.configuration[projectBinding.key];
  expect(reportProject).toMatch(/^goal_/);
  const a = page.getByRole("region", { name: "Background automation" });
  await a.getByText("Configure reviewed automation").click();
  await a.getByLabel("Automation type").selectOption("authorizations");
  await a.getByLabel("Workflow Google account").selectOption(setup.connection_id);
  await a.getByLabel("Five-field cron").fill("0 9 * * *");
  await a.getByLabel("Deadline").fill(new Date(Date.now() + 30 * 86400000).toISOString());
  await a.getByLabel("Business purpose").fill("Daily source-backed report");
  await a.getByLabel("Authorized content scope").fill("Complaint findings and verified Sheet URL");
  await a
    .getByLabel("Permitted operations")
    .fill(
      JSON.stringify({
        extension_sheets_create_report: {
          type: "object",
          required: ["project_id"],
          properties: { project_id: { const: reportProject } },
        },
        extension_mail_send: {
          type: "object",
          required: ["to", "subject", "body"],
          properties: {
            to: { const: "engineer@example.com" },
            subject: { type: "string", maxLength: 1000 },
            body: { type: "string", maxLength: 12000 },
          },
          additionalProperties: false,
        },
      }),
    );
  await a.getByRole("button", { name: "Review automation scope" }).click();
  await a.getByRole("button", { name: "Confirm reviewed recurring consent" }).click();
  await expect(a.getByText(/Saved authorization:/)).toBeVisible();
  await a.getByLabel("Automation type").selectOption("schedules");
  const choices = a.getByLabel("Approved workflow revision");
  await expect(choices.locator("option")).not.toHaveCount(1);
  const plannedId = new URL(page.url()).searchParams.get("composition")!;
  await choices.selectOption("cw_" + plannedId.replace(/^composition_/, "") + ":1");
  await a.getByRole("button", { name: "Review automation scope" }).click();
  await a.getByRole("button", { name: "Confirm reviewed automation" }).click();
  await expect(a.getByText(/Saved schedule:/)).toBeVisible();
  const one = await control(page, "occurrence");
  const two = await control(page, "occurrence");
  expect(two.occurrences).toHaveLength(2);
  expect(new Set(two.occurrences.map((o: { run_id: string }) => o.run_id)).size).toBe(2);
  const cid = new URL(page.url()).searchParams.get("composition");
  const runs = await Promise.all(
    two.occurrences.map(
      async (o: { run_id: string }) =>
        (
          await (
            await page.request.get(
              "/api/backend/business-ontology/v1/compositions/" + cid + "/view?run_id=" + o.run_id,
            )
          ).json()
        ).data.run,
    ),
  );
  expect(runs[0].action_instances.read.output).not.toEqual(runs[1].action_instances.read.output);
  expect(runs.every((r) => r.action_instances.send.verified_receipt)).toBe(true);
  expect(one.occurrences).toHaveLength(1);
  await a.getByRole("button", { name: "Refresh automation" }).click();
  await expect(a.getByText(/occurrence ·/)).toHaveCount(2);
});

test("E: refresh and worker reconstruction retain uncertain sends without replay", async ({
  page,
}) => {
  const setup = await startCase(page, "daily");
  const before = await control(page, "state");
  await control(page, "uncertain");
  const stopped = await advanceCase(page, setup.case_id, "blocked");
  expect(stopped.adaptive.status).toBe("blocked");
  const state = await control(page, "state");
  expect(state.sent - before.sent).toBe(1);
  const restarted = await control(page, "restart-worker");
  expect(restarted.sent).toBe(state.sent);
  await page.reload();
  await expect(page.getByText(/Unknown writes and interrupted evaluator calls/)).toBeVisible();
  await expect(page.getByRole("button", { name: "Continue bounded evaluation" })).toBeDisabled();
  await control(page, "tick");
  const final = await control(page, "state");
  expect(final.sent).toBe(state.sent);
  const run = (
    await (
      await page.request.get(
        "/api/backend/business-ontology/v1/compositions/" +
          stopped.adaptive.composition_id +
          "/view?run_id=" +
          stopped.adaptive.run_id,
      )
    ).json()
  ).data.run;
  expect(run.error_code).toBe("ACTION_EFFECT_UNVERIFIED");
});

test("Main prompt: account and goal produce a verified report/email without technical inputs",async({page})=>{
  await login(page);
  const setup=await control(page,'scenario/daily');
  const before=await control(page,'state');
  let interrupted=false;
  await page.route('**/api/backend/business-ontology/v1/compositions/*/view*',async route=>{if(!interrupted){interrupted=true;await route.abort('failed');}else await route.continue();});
  await page.goto('/app');
  await page.getByLabel('Workflow Google account').first().selectOption(setup.connection_id);
  await expect(page.getByLabel('Optional connected action')).toHaveCount(0);
  await page.getByLabel('Process description').fill('Investigate complaint C123, create a Sheet of evidence-backed findings and email engineer@example.com the verified link.');
  await page.getByRole('button',{name:'Generate workflow',exact:true}).click();
  await expect(page.getByRole('heading',{name:'Investigation workflow',exact:true})).toBeVisible();
  expect(new URL(page.url()).searchParams.get('connected')).toBe('1');
  await expect(page.getByLabel('Dynamic investigation workflow canvas')).toBeVisible();
  expect(interrupted).toBe(true);
  await page.getByRole('button',{name:'Agents and tools',exact:true}).click();
  await expect(page.getByRole('heading',{name:'Agents and tools',exact:true})).toBeVisible();
  await page.keyboard.press('Escape');
  await page.getByRole('button',{name:'Review plan',exact:true}).click();
  await page.getByRole('button',{name:'Approve workflow',exact:true}).click();
  await page.getByRole('button',{name:'Run reviewed plan',exact:true}).click();
  for(let i=0;i<2;i++){
    await control(page,'tick');
    await page.getByRole('button',{name:'Refresh plan',exact:true}).click();
    await expect(page.getByRole('button',{name:'Approve exact payload',exact:true})).toBeVisible();
    await page.getByRole('button',{name:'Approve exact payload',exact:true}).click();
  }
  await control(page,'tick');await page.getByRole('button',{name:'Refresh plan',exact:true}).click();
  const url=new URL(page.url()),cid=url.searchParams.get('composition'),rid=url.searchParams.get('run');
  const response=await page.request.get('/api/backend/business-ontology/v1/compositions/'+cid+'/view?run_id='+rid);
  expect(response.ok()).toBe(true);const view=(await response.json()).data;
  expect(view.run.status).toBe('completed');
  expect(view.run.action_instances.sheet.resolved_inputs.project_id).toMatch(/^goal_/);
  expect(view.run.action_instances.sheet.resolved_inputs.creation_key).toMatch(/^action_/);
  expect(view.run.action_instances.sheet.verified_receipt).toBe(true);
  expect(view.run.action_instances.send.resolved_inputs.body).toContain(view.run.action_instances.sheet.output.spreadsheet_url);
  const after=await control(page,'state');expect(after.sheets-before.sheets).toBe(1);expect(after.sent-before.sent).toBe(1);
  await page.getByRole('tab',{name:'report',exact:true}).click();
  await expect(page.getByRole('tabpanel',{name:'Investigation report'})).toBeVisible();
  await expect(page.getByRole('link',{name:'Open verified artifact: '+view.run.action_instances.sheet.output.spreadsheet_url,exact:true})).toBeVisible();
  await page.setViewportSize({width:390,height:844});
  expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1)).toBe(true);
});

test("E: revoked selected account blocks planning and never substitutes another account", async ({
  page,
}) => {
  await login(page);
  const setup = await control(page, "scenario/daily");
  await page.goto("/app/workflows/investigate?connected=1");
  await page
    .getByLabel("Business goal")
    .fill("Investigate complaint C123, create a Sheet and email engineer@example.com the findings.");
  await page.getByLabel("Workflow Google account").first().selectOption(setup.connection_id);
  await expect(page.getByLabel("Explicit user values")).toHaveCount(0);
  await expect(page.getByLabel("Optional connected action")).toHaveCount(0);
  const before = await control(page, "state");
  await control(page, "revoke-account");
  await page.getByRole("button", { name: "Propose connected plan" }).click();
  await expect(page.getByRole("alert").first()).toBeVisible();
  await expect(page.getByRole("heading", { name: "Investigation workflow" })).toHaveCount(0);
  const after = await control(page, "state");
  expect(after.sent).toBe(before.sent);
  expect(after.sheets).toBe(before.sheets);
  await expect(page.getByLabel("Workflow Google account").first()).toHaveValue(setup.connection_id);
});
