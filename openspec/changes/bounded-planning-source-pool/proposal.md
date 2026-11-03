# Fit automatic planning source candidates to the metadata budget

## Why
A real Simpson Overview request failed as job plan_76383160b9374d4c86c54b22e08fd176 with KG_RETRIEVAL_LIMIT before model generation. The top twelve cached source schemas total about 105 KB; the retriever rejects them against a 70 KB budget even though useful relevant sources fit.

## What Changes
Automatically pack ranked complete source descriptors within the existing byte/source limits, excluding oversized candidates and reporting the omission. Preserve exact fields, identifiers, source authorization, accepted relationships and the four-source execution ceiling. Explicit manual selections retain their existing validation. Reproduce the production metadata failure without provider calls and cover the API planning context rather than just ontology-only generation.

## Impact
Backend retrieval and diagnostic error wording only. No company-record reads/writes, new provider transfer, fake successful job, credential change or frontend build required.
