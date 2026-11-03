# Business Ontology foundation API — chunk 2

Status: implemented and verified locally; no live deployment or production workspace initialization performed.

## Separation and persistence

`workflow_api/business_ontology.py` owns three additive tables: `business_ontology_workspaces`, `business_ontology_versions`, and `business_ontology_events`. Every key includes trusted workspace and owner. These tables contain no copied company records or connector secrets. The original `ontology_*` tables, Semantic Intelligence component and existing Ontology tab retain their behavior.

An initialized foundation contains a namespace unique to the workspace/owner, explicit service and quality source bindings, their metadata revisions, and a foundation revision. Its immutable snapshot contains five layer descriptions and twelve module descriptions, with empty concepts, relationships and rules. A foundation snapshot is not a generated ontology release. No SME review gate is introduced; operational business approvals remain in the planned model.

## Endpoints

| Method and path | Behavior |
| --- | --- |
| GET `/business-ontology/v1` | Read the scoped workspace or null, catalogue, owned connected MongoDB choices, current source availability, snapshot summaries and actual zero generation counts. Does not initialize records. |
| POST `/business-ontology/v1/initialize` | Bind two distinct owned connected MongoDB sources and atomically save foundation + snapshot + initialization event. |
| GET `/business-ontology/v1/versions/{version_id}` | Read an immutable owned foundation snapshot; another owner or workspace receives not found. |

Initialization accepts exactly:

```json
{"sources":{"service":"<owned db1 connection ID>","quality":"<owned db2 connection ID>"}}
```

No title, namespace, status, identity, credential or approval values may be injected through this payload. Invalid payloads return 422; different bindings after initialization return 409. Repeating identical bindings returns the same revision and creates no duplicate snapshot/event. Binding a disconnected or foreign connection is rejected. Read access requires `tools.read` and `workspace:read`; initialization requires `tools.assign` plus `workspace:read` and `workspace:write`. Existing session/origin transport and no-store response envelopes apply.

The view exposes source bindings as connected, metadata_changed or unavailable, comparing current owned metadata with the initialization revision. No model calls, remote queries, source writes, graph construction, publication or workflow execution occur.

## Frontend

`SimpsonBusinessOntology.tsx` is mounted under the additional Business Ontology tab in Data Intelligence. Managers select both existing connections and explicitly create the workspace. Viewers can browse the catalogue and existing foundation without initialization controls. Five layer filters and twelve module selectors display descriptions and zero generated concept counts. Current source availability and foundation revision are visible after initialization. Loading/error/retry and desktop/mobile layouts are supported.

The older `BusinessOntology.tsx` component belongs to Semantic Intelligence and is unchanged. The existing Ontology tab continues to use `OntologyFoundation.tsx`.

## API contract and next chunk

`frontend/src/api/business-ontology.ts` validates the response with Zod; the API methods use the existing authenticated client. These are additive local interfaces, not changes to shared workflow/agent/tool contracts.

The next chunk will add OpenAI extraction and versioned structured definitions. Do not interpret the layer/module catalogue or foundation snapshot as generated business concepts or an executable warranty policy.
