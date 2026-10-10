# Contributor Onboarding and Handoff Protocol

When a contributor explicitly identifies themselves, Codex must provide a role-specific briefing before making changes.

## Required response structure

1. Identify the contributor and segment.
2. Show the current segment status.
3. List responsibilities and out-of-scope work.
4. List upstream inputs and contract versions.
5. List completed upstream work and verification evidence.
6. List known defects, unresolved decisions, blockers, and affected downstream owners.
7. List the next recommended actions.
8. Ask for an explicit implementation request before editing code.

## Identity routing

| Identification | Briefing scope |
| --- | --- |
| `I am Suprajha` | Planning pipeline only, plus shared contract status. |
| `I am Aravind` | Agent/Tool Registry work plus Suprajha’s planner handoff, defects, and dependencies. |
| `I am Harihar` | Existing UI/API integration plus accepted workflow, agent, and tool contracts. |
| `I am Rethika` | Complete accumulated context from Suprajha, Aravind, and Harihar, including all defects and integration dependencies. |

## Blocking rule

A handoff is a hard blocker when a contract violation makes the downstream input invalid or unsafe. Independent cosmetic or optional work is recorded as a warning and does not block unrelated work.

## No implicit implementation

Name recognition provides context only. It does not authorize code edits, external side effects, credential changes, or task completion claims.
