# Preserve source-backed procurement routing

## Why
The BOQ creation rule captures the workshop prompt's "prepare the BOQ" even though it explicitly instructs discovery of existing Requirements and Vendors tabs. The resulting general draft has capability/setup blockers instead of native procurement setup.

## What Changes
Prioritize explicit instructions to read requirements/BOQ or use source tables over BOQ creation wording. Keep description-only BOQ generation on the general planner, including prompts with supplementary knowledge links. Preserve authorized discovery, Registry blockers, provider policy, and existing revisions.

## Impact
Procurement routing and regression coverage only. Verification may generate a draft and read sources; it must not save/publish/execute procurement or send supplier communications.
