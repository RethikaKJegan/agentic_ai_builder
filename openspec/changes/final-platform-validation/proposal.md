# Integrated platform final validation

Run all available safe backend/PostgreSQL, contract, source and frontend/browser
checks on the current staged source without changing the index or production.
Use disposable stores and a separately built frontend, controlled model/provider
transports and independently recorded test results. Fix only reproduced defects
with focused regressions; do not rebuild the architecture or weaken assertions.
Classify release requirements PASS/FAIL/BLOCKED/NOT TESTED and issue an evidence-
based production/pilot readiness decision. Missing staging hosts, live targets,
SLO approval and external alert infrastructure remain explicit blockers.
