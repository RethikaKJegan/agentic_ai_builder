# One prompt, automatic runs

Describe the process, trigger, source and business rules in the Overview prompt. Include a source URL or ID and its range when relevant. The planner saves fixed settings in the workflow's existing node configuration. Changing data comes from the actual trigger event or an authorized connector read.

For example:

> When I manually start this workflow, read Google Sheet [your Sheet URL], range Sheet1!A:D. Its headers are product, actual_stock, reorder_threshold, target_stock. Retrieve fresh inventory through the Sheets connector. For products below their reorder threshold, delegate restock calculations to a specialist while the master continues reviewing the other products. Combine the findings into a report. Do not send email or modify the Sheet.

Or an event workflow:

> When a new row is added to Google Sheet [your Sheet URL], range Sheet1!A:D, review the expense. Headers are expense_id, category, amount, notes; expense_id is the unique record ID. If an expense needs a closer check, delegate the analysis to a specialist and combine its findings into the final expense report. Do not send email or modify the Sheet.

Review and publish the generated draft. Manual workflows run with **Run published**, without input prompts. Published event workflows activate their source and start when a new event arrives; inspect **Runs**, the editor's execution trace and **Agent communication**. The initial Sheets polling baseline does not run existing rows.

Connector accounts and resource access must already be configured. Missing or ambiguous settings remain setup requirements before publication; agents cannot invent resource IDs or permissions. Existing action approvals still apply.

New UI planning requests opt into automatic inputs. Existing saved revisions are preserved; regenerate an old manual-input workflow to use the new mode. No shared v1 contract was changed: this uses existing constants, event mappings and extensible metadata.
