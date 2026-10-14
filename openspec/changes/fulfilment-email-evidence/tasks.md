- [x] Restrict generated extraction instructions to actual fresh-email evidence and explicitly reported dates.
- [x] Verify syntax and existing fulfilment guard tests.

Five existing fulfilment guard tests pass; strict scoped OpenSpec and diff checks pass. The recorded source/output confirms the model appended PO context as email evidence. Instructions now prohibit that and unreported date/tracking defaults. Actual fresh model extraction remains to be verified; no servers started, live records changed, or email sent.
