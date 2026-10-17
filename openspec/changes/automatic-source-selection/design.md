# Design

The overview always requests automatic input inference. Backend enrichment overrides client workspace-source fields, uses the authenticated workspace and existing workspace read permission, bounds database reads and text sizes, and excludes disabled/invalid/secret-bearing documents. Additional supported source links in the objective take precedence but do not discard existing sources. Saved published source configurations are candidates, not proof of provider access. The model chooses relevant evidence, binds known settings and retains missing setup requirements.

Saved text knowledge is passed as data to the planner and loaded freshly for accepted runtime agents with data.read permission using their Registry-owned workspace. Knowledge is kept separate from validated agent input and registered instructions. It grants no tools or permissions. Source content never becomes system instructions. Unreadable or unsupported URL-only knowledge is not represented as fetched content. Existing read tools retrieve live external facts; discovery and execution retain access checks. Existing manually configured workflows keep their execution semantics.

Tests use isolated databases/offline models. Deployment retains a source/build checkpoint and only restarts scoped builder services after verification; no production business actions are needed.
