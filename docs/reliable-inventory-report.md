# Inventory report planning and execution

The normal Northwind restocking prompt selects current owned KG sources automatically. A bounded compiler handles inventory restocking plus a new Google spreadsheet, email summary and dated IST review. Other workflow families keep the general planner. This does not create or execute a workflow during deployment.

The compiler resolves exact metadata field IDs and accepted/declared technical links for products, categories and suppliers. A fixed bounded read queries those sources at execution time, then validates and normalizes the resulting evidence. It never copies example business rows or invents dataset identities. Unknown or ambiguous metadata fails with a specific requirement.

Ranking uses `stock_position = units_in_stock + units_on_order` and `shortage = max(reorder_level - stock_position, 0)`. Discontinued products are excluded. Confirmed shortages rank first, followed by shortage descending, stock/reorder coverage ascending, stock position ascending and product identity. Up to five real candidates are shown; candidates with no confirmed shortage are explicitly marked as watchlist only. Truncated evidence and fewer than five confirmed shortages are disclosed. This is a stock-based rule, not demand forecasting.

A coordinator delegates public supply-risk research to a specialist. Actual search/page results provide external source links. Research cannot rewrite inventory arithmetic or execute Google writes. Inventory, external findings, and method/coverage have separate report tabs. External content remains untrusted evidence.

The report tool creates a new Sheet with literal validated cells and verifies its saved content. Only its verified URL enters deterministic email/calendar preparation. The email recipient defaults to the bound account's actual profile address, as requested by the user. The existing explicitly selected Google account is saved as an owner-scoped workflow default; explicit future account selections override it. Disconnected defaults fail rather than silently using another account.

For the requested 30-minute meeting inside 19 October 2026, 15:00–16:00 IST, the confirmed preference is the final fitting slot: **15:30–16:00 Asia/Kolkata**, on the account's primary calendar. Supported explicit date/window changes are parsed from the prompt. Unsupported date forms fail rather than inventing a time.

Spreadsheet creation, email sending and calendar creation each have their own approval gate. Rejection stops subsequent writes. Both Registry validation and the connector require the immediate approval evidence, even if legacy procurement settings permit automatic writes. Legacy procurement behavior is unchanged. Fixed steps have separate least-privilege execution agents so waiting at one approval does not consume another step's action timeout.

## Check in the UI

1. Refresh the website and create a **new** workflow using the original prompt. Previously generated drafts are not rewritten.
2. Check that products, categories and suppliers are selected automatically, and inspect the read/query and research nodes.
3. Check the three approval gates and the meeting time before submitting the workflow for review/publishing through the existing controls.
4. Run it. Review actual inventory evidence and the report preview before approving spreadsheet creation.
5. Open the returned Sheet; check separate inventory and external-risk tabs, real source links, stock arithmetic and watchlist labels.
6. Approve the email and meeting separately. Confirm the email arrives in the selected account's own inbox and the primary calendar contains the 15:30–16:00 IST meeting with the verified report link.

Offline runtime tests cover the full graph with mocked database/research/Google responses and every rejection stage. Live readiness checks cover database connectivity, real cached metadata/query validation and public web search/page reads. Live Google writes remain for the user's own workflow test; no deployment check creates a workflow, spreadsheet, email or event.
