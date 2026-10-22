-- Raises an exception on wrong row counts, flags or unvalidated constraints.
DO $check$
BEGIN
 IF (SELECT count(*) FROM northwind_graph_demo.business_regions) <> 8 THEN RAISE EXCEPTION 'Unexpected row count: business_regions'; END IF;
 IF EXISTS (SELECT 1 FROM northwind_graph_demo.business_regions WHERE NOT is_demo OR provenance <> 'SYNTHETIC graph demonstration only; not operational evidence.') THEN RAISE EXCEPTION 'Bad demo provenance: business_regions'; END IF;
 IF (SELECT count(*) FROM northwind_graph_demo.facility_types) <> 5 THEN RAISE EXCEPTION 'Unexpected row count: facility_types'; END IF;
 IF EXISTS (SELECT 1 FROM northwind_graph_demo.facility_types WHERE NOT is_demo OR provenance <> 'SYNTHETIC graph demonstration only; not operational evidence.') THEN RAISE EXCEPTION 'Bad demo provenance: facility_types'; END IF;
 IF (SELECT count(*) FROM northwind_graph_demo.handling_protocols) <> 8 THEN RAISE EXCEPTION 'Unexpected row count: handling_protocols'; END IF;
 IF EXISTS (SELECT 1 FROM northwind_graph_demo.handling_protocols WHERE NOT is_demo OR provenance <> 'SYNTHETIC graph demonstration only; not operational evidence.') THEN RAISE EXCEPTION 'Bad demo provenance: handling_protocols'; END IF;
 IF (SELECT count(*) FROM northwind_graph_demo.packaging_materials) <> 8 THEN RAISE EXCEPTION 'Unexpected row count: packaging_materials'; END IF;
 IF EXISTS (SELECT 1 FROM northwind_graph_demo.packaging_materials WHERE NOT is_demo OR provenance <> 'SYNTHETIC graph demonstration only; not operational evidence.') THEN RAISE EXCEPTION 'Bad demo provenance: packaging_materials'; END IF;
 IF (SELECT count(*) FROM northwind_graph_demo.packaging_profiles) <> 24 THEN RAISE EXCEPTION 'Unexpected row count: packaging_profiles'; END IF;
 IF EXISTS (SELECT 1 FROM northwind_graph_demo.packaging_profiles WHERE NOT is_demo OR provenance <> 'SYNTHETIC graph demonstration only; not operational evidence.') THEN RAISE EXCEPTION 'Bad demo provenance: packaging_profiles'; END IF;
 IF (SELECT count(*) FROM northwind_graph_demo.certification_standards) <> 10 THEN RAISE EXCEPTION 'Unexpected row count: certification_standards'; END IF;
 IF EXISTS (SELECT 1 FROM northwind_graph_demo.certification_standards WHERE NOT is_demo OR provenance <> 'SYNTHETIC graph demonstration only; not operational evidence.') THEN RAISE EXCEPTION 'Bad demo provenance: certification_standards'; END IF;
 IF (SELECT count(*) FROM northwind_graph_demo.transport_modes) <> 5 THEN RAISE EXCEPTION 'Unexpected row count: transport_modes'; END IF;
 IF EXISTS (SELECT 1 FROM northwind_graph_demo.transport_modes WHERE NOT is_demo OR provenance <> 'SYNTHETIC graph demonstration only; not operational evidence.') THEN RAISE EXCEPTION 'Bad demo provenance: transport_modes'; END IF;
 IF (SELECT count(*) FROM northwind_graph_demo.material_families) <> 12 THEN RAISE EXCEPTION 'Unexpected row count: material_families'; END IF;
 IF EXISTS (SELECT 1 FROM northwind_graph_demo.material_families WHERE NOT is_demo OR provenance <> 'SYNTHETIC graph demonstration only; not operational evidence.') THEN RAISE EXCEPTION 'Bad demo provenance: material_families'; END IF;
 IF (SELECT count(*) FROM northwind_graph_demo.supplier_sites) <> 48 THEN RAISE EXCEPTION 'Unexpected row count: supplier_sites'; END IF;
 IF EXISTS (SELECT 1 FROM northwind_graph_demo.supplier_sites WHERE NOT is_demo OR provenance <> 'SYNTHETIC graph demonstration only; not operational evidence.') THEN RAISE EXCEPTION 'Bad demo provenance: supplier_sites'; END IF;
 IF (SELECT count(*) FROM northwind_graph_demo.warehouses) <> 24 THEN RAISE EXCEPTION 'Unexpected row count: warehouses'; END IF;
 IF EXISTS (SELECT 1 FROM northwind_graph_demo.warehouses WHERE NOT is_demo OR provenance <> 'SYNTHETIC graph demonstration only; not operational evidence.') THEN RAISE EXCEPTION 'Bad demo provenance: warehouses'; END IF;
 IF (SELECT count(*) FROM northwind_graph_demo.inspection_checklists) <> 32 THEN RAISE EXCEPTION 'Unexpected row count: inspection_checklists'; END IF;
 IF EXISTS (SELECT 1 FROM northwind_graph_demo.inspection_checklists WHERE NOT is_demo OR provenance <> 'SYNTHETIC graph demonstration only; not operational evidence.') THEN RAISE EXCEPTION 'Bad demo provenance: inspection_checklists'; END IF;
 IF (SELECT count(*) FROM northwind_graph_demo.distribution_lanes) <> 72 THEN RAISE EXCEPTION 'Unexpected row count: distribution_lanes'; END IF;
 IF EXISTS (SELECT 1 FROM northwind_graph_demo.distribution_lanes WHERE NOT is_demo OR provenance <> 'SYNTHETIC graph demonstration only; not operational evidence.') THEN RAISE EXCEPTION 'Bad demo provenance: distribution_lanes'; END IF;
 IF (SELECT count(*) FROM northwind_graph_demo.site_certifications) <> 144 THEN RAISE EXCEPTION 'Unexpected row count: site_certifications'; END IF;
 IF EXISTS (SELECT 1 FROM northwind_graph_demo.site_certifications WHERE NOT is_demo OR provenance <> 'SYNTHETIC graph demonstration only; not operational evidence.') THEN RAISE EXCEPTION 'Bad demo provenance: site_certifications'; END IF;
 IF (SELECT count(*) FROM northwind_graph_demo.warehouse_capabilities) <> 96 THEN RAISE EXCEPTION 'Unexpected row count: warehouse_capabilities'; END IF;
 IF EXISTS (SELECT 1 FROM northwind_graph_demo.warehouse_capabilities WHERE NOT is_demo OR provenance <> 'SYNTHETIC graph demonstration only; not operational evidence.') THEN RAISE EXCEPTION 'Bad demo provenance: warehouse_capabilities'; END IF;
 IF (SELECT count(*) FROM northwind_graph_demo.material_packaging_rules) <> 96 THEN RAISE EXCEPTION 'Unexpected row count: material_packaging_rules'; END IF;
 IF EXISTS (SELECT 1 FROM northwind_graph_demo.material_packaging_rules WHERE NOT is_demo OR provenance <> 'SYNTHETIC graph demonstration only; not operational evidence.') THEN RAISE EXCEPTION 'Bad demo provenance: material_packaging_rules'; END IF;
 IF (SELECT count(*) FROM northwind_graph_demo.lane_site_assignments) <> 144 THEN RAISE EXCEPTION 'Unexpected row count: lane_site_assignments'; END IF;
 IF EXISTS (SELECT 1 FROM northwind_graph_demo.lane_site_assignments WHERE NOT is_demo OR provenance <> 'SYNTHETIC graph demonstration only; not operational evidence.') THEN RAISE EXCEPTION 'Bad demo provenance: lane_site_assignments'; END IF;
 IF (SELECT count(*) FROM northwind_graph_demo.site_material_approvals) <> 192 THEN RAISE EXCEPTION 'Unexpected row count: site_material_approvals'; END IF;
 IF EXISTS (SELECT 1 FROM northwind_graph_demo.site_material_approvals WHERE NOT is_demo OR provenance <> 'SYNTHETIC graph demonstration only; not operational evidence.') THEN RAISE EXCEPTION 'Bad demo provenance: site_material_approvals'; END IF;
 IF (SELECT count(*) FROM pg_constraint c JOIN pg_namespace n ON n.oid=c.connamespace WHERE n.nspname='northwind_graph_demo' AND c.contype='f' AND c.convalidated) <> 31 THEN RAISE EXCEPTION 'Unexpected validated foreign key count'; END IF;
END;
$check$;
SELECT 'business_regions' AS table_name, count(*) AS row_count FROM northwind_graph_demo.business_regions
UNION ALL
SELECT 'facility_types' AS table_name, count(*) AS row_count FROM northwind_graph_demo.facility_types
UNION ALL
SELECT 'handling_protocols' AS table_name, count(*) AS row_count FROM northwind_graph_demo.handling_protocols
UNION ALL
SELECT 'packaging_materials' AS table_name, count(*) AS row_count FROM northwind_graph_demo.packaging_materials
UNION ALL
SELECT 'packaging_profiles' AS table_name, count(*) AS row_count FROM northwind_graph_demo.packaging_profiles
UNION ALL
SELECT 'certification_standards' AS table_name, count(*) AS row_count FROM northwind_graph_demo.certification_standards
UNION ALL
SELECT 'transport_modes' AS table_name, count(*) AS row_count FROM northwind_graph_demo.transport_modes
UNION ALL
SELECT 'material_families' AS table_name, count(*) AS row_count FROM northwind_graph_demo.material_families
UNION ALL
SELECT 'supplier_sites' AS table_name, count(*) AS row_count FROM northwind_graph_demo.supplier_sites
UNION ALL
SELECT 'warehouses' AS table_name, count(*) AS row_count FROM northwind_graph_demo.warehouses
UNION ALL
SELECT 'inspection_checklists' AS table_name, count(*) AS row_count FROM northwind_graph_demo.inspection_checklists
UNION ALL
SELECT 'distribution_lanes' AS table_name, count(*) AS row_count FROM northwind_graph_demo.distribution_lanes
UNION ALL
SELECT 'site_certifications' AS table_name, count(*) AS row_count FROM northwind_graph_demo.site_certifications
UNION ALL
SELECT 'warehouse_capabilities' AS table_name, count(*) AS row_count FROM northwind_graph_demo.warehouse_capabilities
UNION ALL
SELECT 'material_packaging_rules' AS table_name, count(*) AS row_count FROM northwind_graph_demo.material_packaging_rules
UNION ALL
SELECT 'lane_site_assignments' AS table_name, count(*) AS row_count FROM northwind_graph_demo.lane_site_assignments
UNION ALL
SELECT 'site_material_approvals' AS table_name, count(*) AS row_count FROM northwind_graph_demo.site_material_approvals;
