## ADDED Requirements

### Requirement: Additive isolation
The extension SHALL use new files, separate state and opt-in startup without modifying existing application files or saved workflows.

#### Scenario: Existing startup
- **WHEN** the original launcher is used
- **THEN** existing behavior and connector registration remain unchanged

### Requirement: Authorized provider operations
Connector operations SHALL validate exact Registry bindings, input/output schemas, resource restrictions and bounded provider responses. External writes SHALL retain runtime approvals and never automatically retry uncertain effects.

#### Scenario: Unauthorized resource
- **WHEN** a tool requests a spreadsheet, calendar, recipient or artifact outside operator policy
- **THEN** the operation fails before a provider write

### Requirement: Sheets Calendar Mail and search
The extension SHALL support scoped multi-sheet reads and record writes, Calendar list/create/update/cancel, Gmail search/message/thread/attachment/draft/send/reply and optional bounded web search. Inference and procurement decisions SHALL remain agent/workflow responsibilities.

#### Scenario: Connector execution evidence
- **WHEN** an approved workflow invokes an extension tool
- **THEN** the existing runtime records its intent, result and handoff through canonical events

### Requirement: Independent credentials
OAuth setup SHALL save verified grants only in extension-owned private token files. Secrets SHALL remain outside workflow documents and tool responses.

#### Scenario: Missing additional consent
- **WHEN** Google credentials lack the selected operation's scopes
- **THEN** the connector reports an authorization failure without altering existing project credentials

### Requirement: Generalized spreadsheet selection
The extension SHALL accept Google spreadsheet links and discover actual tabs and headers using the connected Google account. Spreadsheet IDs SHALL NOT be required in operator configuration. Optional nonempty operator lists SHALL only restrict access; reviewed workflow targets SHALL authorize exact write tables and columns.

#### Scenario: Different spreadsheets without reconfiguration
- **WHEN** workflows supply different accessible spreadsheet links with the same extension configuration
- **THEN** reads and discovery use their supplied links and writes require each workflow's reviewed targets

#### Scenario: Missing reviewed write access
- **WHEN** a write has no workflow target and no legacy operator target
- **THEN** the connector denies the write before provider invocation

### Requirement: Generalized Calendar Mail and search selection
Enabled connectors SHALL use account connections without preset calendar IDs, sender addresses or recipients. Workflow inputs SHALL select resources and search filters. Discovery SHALL return actual account calendars and Gmail identity. Optional restrictions and exact write approvals SHALL remain enforced.

#### Scenario: Different resources with one connection
- **WHEN** reviewed workflows use different calendars and email recipients with the same connection configuration
- **THEN** the connectors use those workflow-selected resources without configuration edits

#### Scenario: Provider consent and restrictions
- **WHEN** account consent or an explicit operator restriction denies a selected resource
- **THEN** the connector fails before an unauthorized write and does not fabricate discovery results

### Requirement: Provider attachment identifiers
Gmail attachment downloads SHALL accept URL-safe opaque provider attachment IDs up to 4096 characters. They SHALL reject oversized or invalid-character identifiers before provider access, while keeping message identifiers and artifact namespaces unchanged.

#### Scenario: Long actual Gmail attachment ID
- **WHEN** Gmail returns an attachment ID longer than 255 characters within the supported bound
- **THEN** the reviewed download tool accepts it and retrieves only that message attachment

### Requirement: Stable message attachment references
Message and thread reads SHALL expose a stable MIME-part reference when Google supplies a part ID. Downloads SHALL resolve that reference against exactly one part of the requested message and use its current provider attachment ID. Legacy provider IDs SHALL remain supported when they match the fetched message.

#### Scenario: Changing provider attachment IDs
- **WHEN** repeated reads return different opaque attachment IDs for the same message part
- **THEN** the stable part reference still downloads that exact attachment without widening message access
