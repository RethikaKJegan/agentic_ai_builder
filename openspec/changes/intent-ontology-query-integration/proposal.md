# Intent-scoped ontology query integration

## Why
Connected query discovery builds full account metadata before existing ontology retrieval; large scopes remove the generic query capability. A live Simpson diagnostic at 17:18:55 UTC on 9 November shows content.prepare binding context key validated_context with path [validated_context], absent from that namespace. Historical request correlation was not logged, so exact request attribution remains unproven.

## What Changes
Reuse KnowledgeRetrieval before bounded query catalogue construction. Keep complete selected source descriptors, reviewed joins, full metadata revision and runtime permission checks. Separate executable plan validation from model catalogue sizing. Add missing-binding diagnostics and one bounded correction for invalid internal bindings; genuine user inputs retain clarification. Preserve Questions, contracts, CrewAI and runtime.

## Impact
workflow_api query discovery, binding validation, focused tests. No shared contract or database migration. Controlled deployment with fresh verified backups and application-only rollback; no paid model calls or external writes.
