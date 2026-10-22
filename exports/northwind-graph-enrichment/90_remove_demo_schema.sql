-- OPTIONAL: removes only this demo schema. No CASCADE, no original tables.
BEGIN;
-- Synthetic graph-only demonstration package. Never an operational source.
SET LOCAL lock_timeout = '2s';
SET LOCAL statement_timeout = '60s';
SET LOCAL standard_conforming_strings = on;
DROP TABLE northwind_graph_demo.site_material_approvals;
DROP TABLE northwind_graph_demo.lane_site_assignments;
DROP TABLE northwind_graph_demo.material_packaging_rules;
DROP TABLE northwind_graph_demo.warehouse_capabilities;
DROP TABLE northwind_graph_demo.site_certifications;
DROP TABLE northwind_graph_demo.distribution_lanes;
DROP TABLE northwind_graph_demo.inspection_checklists;
DROP TABLE northwind_graph_demo.warehouses;
DROP TABLE northwind_graph_demo.supplier_sites;
DROP TABLE northwind_graph_demo.material_families;
DROP TABLE northwind_graph_demo.transport_modes;
DROP TABLE northwind_graph_demo.certification_standards;
DROP TABLE northwind_graph_demo.packaging_profiles;
DROP TABLE northwind_graph_demo.packaging_materials;
DROP TABLE northwind_graph_demo.handling_protocols;
DROP TABLE northwind_graph_demo.facility_types;
DROP TABLE northwind_graph_demo.business_regions;
DROP SCHEMA northwind_graph_demo;
COMMIT;
