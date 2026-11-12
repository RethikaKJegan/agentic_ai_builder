# Receipt-aware automation completion — deployed 12 November 2026

Release `receipt-completion-20261112-d5e9ec95e8a8` is deployed at https://praxi.bellcorpstudio.com/. Frontend build: `B2JdpnItKIgR_0CNe5G-h`. Only Subway and frontend services restarted; actual backend path is `.local/workflow-ui-release-20261112/app`.

The reported run `run_66c01b01c30c419095c8446b5ad147da` completed its approved Gmail send and stored the provider receipt, then failed a fifth evaluator turn. The rejected assessment was not retained, so the precise failed eligibility condition is unknown. The last accepted business assessment was eligible. A concrete defect classified completed delivery receipts as invalid business evidence.

Delivery receipts are now separate from business evidence. The runtime finalizes already validated business work deterministically when every approved completion action is completed, completed outputs retain matching fingerprints, connector receipts are verified, and the previous accepted assessment still validates against current source authority. This path performs no model request and no connector retry. Incomplete actions, tampered outputs, unverified receipts and revoked source evidence cannot pass. The existing failed occurrence remains preserved; no historical send or schedule was replayed or modified.

Recurring workflows show concise progress in the main view. Verified completed mail receipts show Email sent; saved blocked runs still indicate attention rather than claim success. Raw evaluator codes, verbose assessments and source internals are available in Background. Required business inputs and exact-payload approvals remain actionable. One-time workflow presentation is retained.

Verification:

- 34 backend tests passed from the actual active release, including real native recurring dispatch, approved fake delivery, post-delivery model-call prevention, receipt integrity, revoked evidence and duplicate protection.
- 30 UI tests passed, plus TypeScript and changed-component lint.
- Isolated production build passed. Four synthetic browser checks passed: desktop/mobile, completed/attention states; no page errors, overflow or backend mutation requests.
- The actual reported run was rehearsed on an in-memory copy with a read-only transaction using its recorded delivery receipt and source evidence. Corrected finalization completed with zero history writes, model requests or connector calls.
- Hosted desktop/mobile checks on the actual saved occurrence passed: confirmed delivery visible, raw error absent from the main view, diagnostics accessible, no writes or page errors.
- Authenticated hosted endpoints, account isolation, worker/service health, source credentials/bindings, ontology, knowledge packages, Subway automation records and histories passed preservation checks. Unrelated backend PIDs remained unchanged. Existing ephemeral query-job TTL cleanup was recorded separately.
- Canonical contracts, generated UI contracts, scoped strict OpenSpec and whitespace checks passed.

Private evidence and rollback build: `.local/receipt-aware-automation-20261112/`. External outages, missing evidence and revoked authority remain truthful execution states; technical messages are not used as the main automation progress display. No verification mail, Sheet or Calendar action was sent.
