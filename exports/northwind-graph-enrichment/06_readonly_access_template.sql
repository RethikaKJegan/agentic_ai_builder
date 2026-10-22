-- OPTIONAL. Edit YOUR_EXISTING_READONLY_ROLE before running.
-- Use an existing app-owned role; this file does not create/reset users/passwords.
-- This is not an automatic graph-only exclusion from the workflow planner.
BEGIN;
SET LOCAL lock_timeout = '2s';
GRANT USAGE ON SCHEMA northwind_graph_demo TO "YOUR_EXISTING_READONLY_ROLE";
GRANT SELECT ON ALL TABLES IN SCHEMA northwind_graph_demo TO "YOUR_EXISTING_READONLY_ROLE";
COMMIT;
