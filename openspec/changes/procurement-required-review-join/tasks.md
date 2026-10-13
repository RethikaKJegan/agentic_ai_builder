- [x] Join exhausted explicitly required specialist reviews before synthesis.
- [x] Clarify one-time review delegation and exhausted-task instructions.
- [x] Run focused join/concurrency tests and contract/spec checks.

Recorded run run_3b9d1ae3756c46ac86cb692650eace05 confirms the second master
input contained zero results, two pending tasks and zero remaining task slots;
its response attempted to delegate the same reviews again. Four focused tests
pass: required-review join, independent master continuation, overlapping child
tasks and actual bounded CrewAI accounting with offline responses. Contracts,
strict OpenSpec and diff checks pass. No services restarted or failed actions
replayed. The prior stopped project remains historical; use a new named project
after loading the runtime fix.
