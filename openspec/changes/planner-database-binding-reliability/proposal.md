# Database source binding reliability

## Why
The actual inspection workflow request failed with KG_SOURCE_BINDING_INVALID. Source binding collapses several different defects into that generic error. A concrete reproducible inconsistency exists: inspection source metadata is accepted into the 70 KB planning pool but its 48 KB full field list is later appended to each agent under a 16 KB hard rejection, so valid source selections can never bind.

## What Changes
Build a bounded task-relevant source reference from trusted catalog fields, preserving exact identities and reporting omitted metadata. Keep full source schema hashes and runtime authorization unchanged. Give correction feedback exact failed constraints and allowed source IDs; describe database selection/assignment fields explicitly in the model-request schema. Exercise actual wide cached schemas and full provider-boundary validation rather than claiming fixture output proves model reliability.

## Impact
Generic planner metadata handling, not Simpson-specific workflow templates. No hardcoded prompts, guessed sources/joins, source writes, automatic publishing or workflow execution. Additional model tests require the specific requested approval.
