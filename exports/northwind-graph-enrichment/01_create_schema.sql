-- Run inside a transaction; the import scripts do this automatically.
-- Synthetic graph-only demonstration package. Never an operational source.
SET LOCAL lock_timeout = '2s';
SET LOCAL statement_timeout = '60s';
SET LOCAL standard_conforming_strings = on;
CREATE SCHEMA northwind_graph_demo;
COMMENT ON SCHEMA northwind_graph_demo IS 'SYNTHETIC graph demonstration only; not operational evidence.';

CREATE TABLE northwind_graph_demo.business_regions (
  region_id integer PRIMARY KEY,
  region_name text NOT NULL UNIQUE,
  is_demo boolean NOT NULL DEFAULT true CHECK (is_demo),
  provenance text NOT NULL
);
COMMENT ON TABLE northwind_graph_demo.business_regions IS 'SYNTHETIC graph demonstration only; not operational evidence.';

CREATE TABLE northwind_graph_demo.facility_types (
  facility_type_id integer PRIMARY KEY,
  facility_type_name text NOT NULL UNIQUE,
  is_demo boolean NOT NULL DEFAULT true CHECK (is_demo),
  provenance text NOT NULL
);
COMMENT ON TABLE northwind_graph_demo.facility_types IS 'SYNTHETIC graph demonstration only; not operational evidence.';

CREATE TABLE northwind_graph_demo.handling_protocols (
  protocol_id integer PRIMARY KEY,
  protocol_name text NOT NULL UNIQUE,
  handling_description text NOT NULL,
  is_demo boolean NOT NULL DEFAULT true CHECK (is_demo),
  provenance text NOT NULL
);
COMMENT ON TABLE northwind_graph_demo.handling_protocols IS 'SYNTHETIC graph demonstration only; not operational evidence.';

CREATE TABLE northwind_graph_demo.packaging_materials (
  material_id integer PRIMARY KEY,
  material_name text NOT NULL UNIQUE,
  is_demo boolean NOT NULL DEFAULT true CHECK (is_demo),
  provenance text NOT NULL
);
COMMENT ON TABLE northwind_graph_demo.packaging_materials IS 'SYNTHETIC graph demonstration only; not operational evidence.';

CREATE TABLE northwind_graph_demo.packaging_profiles (
  packaging_id integer PRIMARY KEY,
  packaging_name text NOT NULL,
  material_id integer NOT NULL,
  protocol_id integer NOT NULL,
  is_demo boolean NOT NULL DEFAULT true CHECK (is_demo),
  provenance text NOT NULL,
  FOREIGN KEY (material_id) REFERENCES northwind_graph_demo.packaging_materials (material_id),
  FOREIGN KEY (protocol_id) REFERENCES northwind_graph_demo.handling_protocols (protocol_id)
);
COMMENT ON TABLE northwind_graph_demo.packaging_profiles IS 'SYNTHETIC graph demonstration only; not operational evidence.';
CREATE INDEX ON northwind_graph_demo.packaging_profiles (material_id);
CREATE INDEX ON northwind_graph_demo.packaging_profiles (protocol_id);

CREATE TABLE northwind_graph_demo.certification_standards (
  standard_id integer PRIMARY KEY,
  standard_name text NOT NULL UNIQUE,
  protocol_id integer NOT NULL,
  is_demo boolean NOT NULL DEFAULT true CHECK (is_demo),
  provenance text NOT NULL,
  FOREIGN KEY (protocol_id) REFERENCES northwind_graph_demo.handling_protocols (protocol_id)
);
COMMENT ON TABLE northwind_graph_demo.certification_standards IS 'SYNTHETIC graph demonstration only; not operational evidence.';
CREATE INDEX ON northwind_graph_demo.certification_standards (protocol_id);

CREATE TABLE northwind_graph_demo.transport_modes (
  mode_id integer PRIMARY KEY,
  mode_name text NOT NULL UNIQUE,
  is_demo boolean NOT NULL DEFAULT true CHECK (is_demo),
  provenance text NOT NULL
);
COMMENT ON TABLE northwind_graph_demo.transport_modes IS 'SYNTHETIC graph demonstration only; not operational evidence.';

CREATE TABLE northwind_graph_demo.material_families (
  family_id integer PRIMARY KEY,
  family_name text NOT NULL UNIQUE,
  protocol_id integer NOT NULL,
  is_demo boolean NOT NULL DEFAULT true CHECK (is_demo),
  provenance text NOT NULL,
  FOREIGN KEY (protocol_id) REFERENCES northwind_graph_demo.handling_protocols (protocol_id)
);
COMMENT ON TABLE northwind_graph_demo.material_families IS 'SYNTHETIC graph demonstration only; not operational evidence.';
CREATE INDEX ON northwind_graph_demo.material_families (protocol_id);

CREATE TABLE northwind_graph_demo.supplier_sites (
  site_id integer PRIMARY KEY,
  site_name text NOT NULL UNIQUE,
  region_id integer NOT NULL,
  facility_type_id integer NOT NULL,
  protocol_id integer NOT NULL,
  is_demo boolean NOT NULL DEFAULT true CHECK (is_demo),
  provenance text NOT NULL,
  FOREIGN KEY (region_id) REFERENCES northwind_graph_demo.business_regions (region_id),
  FOREIGN KEY (facility_type_id) REFERENCES northwind_graph_demo.facility_types (facility_type_id),
  FOREIGN KEY (protocol_id) REFERENCES northwind_graph_demo.handling_protocols (protocol_id)
);
COMMENT ON TABLE northwind_graph_demo.supplier_sites IS 'SYNTHETIC graph demonstration only; not operational evidence.';
CREATE INDEX ON northwind_graph_demo.supplier_sites (region_id);
CREATE INDEX ON northwind_graph_demo.supplier_sites (facility_type_id);
CREATE INDEX ON northwind_graph_demo.supplier_sites (protocol_id);

CREATE TABLE northwind_graph_demo.warehouses (
  warehouse_id integer PRIMARY KEY,
  warehouse_name text NOT NULL UNIQUE,
  region_id integer NOT NULL,
  facility_type_id integer NOT NULL,
  protocol_id integer NOT NULL,
  is_demo boolean NOT NULL DEFAULT true CHECK (is_demo),
  provenance text NOT NULL,
  FOREIGN KEY (region_id) REFERENCES northwind_graph_demo.business_regions (region_id),
  FOREIGN KEY (facility_type_id) REFERENCES northwind_graph_demo.facility_types (facility_type_id),
  FOREIGN KEY (protocol_id) REFERENCES northwind_graph_demo.handling_protocols (protocol_id)
);
COMMENT ON TABLE northwind_graph_demo.warehouses IS 'SYNTHETIC graph demonstration only; not operational evidence.';
CREATE INDEX ON northwind_graph_demo.warehouses (region_id);
CREATE INDEX ON northwind_graph_demo.warehouses (facility_type_id);
CREATE INDEX ON northwind_graph_demo.warehouses (protocol_id);

CREATE TABLE northwind_graph_demo.inspection_checklists (
  checklist_id integer PRIMARY KEY,
  checklist_name text NOT NULL UNIQUE,
  standard_id integer NOT NULL,
  protocol_id integer NOT NULL,
  is_demo boolean NOT NULL DEFAULT true CHECK (is_demo),
  provenance text NOT NULL,
  FOREIGN KEY (standard_id) REFERENCES northwind_graph_demo.certification_standards (standard_id),
  FOREIGN KEY (protocol_id) REFERENCES northwind_graph_demo.handling_protocols (protocol_id)
);
COMMENT ON TABLE northwind_graph_demo.inspection_checklists IS 'SYNTHETIC graph demonstration only; not operational evidence.';
CREATE INDEX ON northwind_graph_demo.inspection_checklists (standard_id);
CREATE INDEX ON northwind_graph_demo.inspection_checklists (protocol_id);

CREATE TABLE northwind_graph_demo.distribution_lanes (
  lane_id integer PRIMARY KEY,
  lane_name text NOT NULL UNIQUE,
  origin_region_id integer NOT NULL,
  destination_region_id integer NOT NULL,
  mode_id integer NOT NULL,
  protocol_id integer NOT NULL,
  is_demo boolean NOT NULL DEFAULT true CHECK (is_demo),
  provenance text NOT NULL,
  FOREIGN KEY (origin_region_id) REFERENCES northwind_graph_demo.business_regions (region_id),
  FOREIGN KEY (destination_region_id) REFERENCES northwind_graph_demo.business_regions (region_id),
  FOREIGN KEY (mode_id) REFERENCES northwind_graph_demo.transport_modes (mode_id),
  FOREIGN KEY (protocol_id) REFERENCES northwind_graph_demo.handling_protocols (protocol_id),
  CHECK (origin_region_id <> destination_region_id)
);
COMMENT ON TABLE northwind_graph_demo.distribution_lanes IS 'SYNTHETIC graph demonstration only; not operational evidence.';
CREATE INDEX ON northwind_graph_demo.distribution_lanes (origin_region_id);
CREATE INDEX ON northwind_graph_demo.distribution_lanes (destination_region_id);
CREATE INDEX ON northwind_graph_demo.distribution_lanes (mode_id);
CREATE INDEX ON northwind_graph_demo.distribution_lanes (protocol_id);

CREATE TABLE northwind_graph_demo.site_certifications (
  site_certification_id integer PRIMARY KEY,
  site_id integer NOT NULL,
  standard_id integer NOT NULL,
  checklist_id integer NOT NULL,
  claim_status text NOT NULL CHECK (claim_status = 'illustrative_only'),
  is_demo boolean NOT NULL DEFAULT true CHECK (is_demo),
  provenance text NOT NULL,
  FOREIGN KEY (site_id) REFERENCES northwind_graph_demo.supplier_sites (site_id),
  FOREIGN KEY (standard_id) REFERENCES northwind_graph_demo.certification_standards (standard_id),
  FOREIGN KEY (checklist_id) REFERENCES northwind_graph_demo.inspection_checklists (checklist_id)
);
COMMENT ON TABLE northwind_graph_demo.site_certifications IS 'SYNTHETIC graph demonstration only; not operational evidence.';
CREATE INDEX ON northwind_graph_demo.site_certifications (site_id);
CREATE INDEX ON northwind_graph_demo.site_certifications (standard_id);
CREATE INDEX ON northwind_graph_demo.site_certifications (checklist_id);

CREATE TABLE northwind_graph_demo.warehouse_capabilities (
  capability_id integer PRIMARY KEY,
  warehouse_id integer NOT NULL,
  protocol_id integer NOT NULL,
  checklist_id integer NOT NULL,
  is_demo boolean NOT NULL DEFAULT true CHECK (is_demo),
  provenance text NOT NULL,
  FOREIGN KEY (warehouse_id) REFERENCES northwind_graph_demo.warehouses (warehouse_id),
  FOREIGN KEY (protocol_id) REFERENCES northwind_graph_demo.handling_protocols (protocol_id),
  FOREIGN KEY (checklist_id) REFERENCES northwind_graph_demo.inspection_checklists (checklist_id)
);
COMMENT ON TABLE northwind_graph_demo.warehouse_capabilities IS 'SYNTHETIC graph demonstration only; not operational evidence.';
CREATE INDEX ON northwind_graph_demo.warehouse_capabilities (warehouse_id);
CREATE INDEX ON northwind_graph_demo.warehouse_capabilities (protocol_id);
CREATE INDEX ON northwind_graph_demo.warehouse_capabilities (checklist_id);

CREATE TABLE northwind_graph_demo.material_packaging_rules (
  rule_id integer PRIMARY KEY,
  family_id integer NOT NULL,
  packaging_id integer NOT NULL,
  protocol_id integer NOT NULL,
  is_demo boolean NOT NULL DEFAULT true CHECK (is_demo),
  provenance text NOT NULL,
  FOREIGN KEY (family_id) REFERENCES northwind_graph_demo.material_families (family_id),
  FOREIGN KEY (packaging_id) REFERENCES northwind_graph_demo.packaging_profiles (packaging_id),
  FOREIGN KEY (protocol_id) REFERENCES northwind_graph_demo.handling_protocols (protocol_id)
);
COMMENT ON TABLE northwind_graph_demo.material_packaging_rules IS 'SYNTHETIC graph demonstration only; not operational evidence.';
CREATE INDEX ON northwind_graph_demo.material_packaging_rules (family_id);
CREATE INDEX ON northwind_graph_demo.material_packaging_rules (packaging_id);
CREATE INDEX ON northwind_graph_demo.material_packaging_rules (protocol_id);

CREATE TABLE northwind_graph_demo.lane_site_assignments (
  assignment_id integer PRIMARY KEY,
  lane_id integer NOT NULL,
  site_id integer NOT NULL,
  warehouse_id integer NOT NULL,
  is_demo boolean NOT NULL DEFAULT true CHECK (is_demo),
  provenance text NOT NULL,
  FOREIGN KEY (lane_id) REFERENCES northwind_graph_demo.distribution_lanes (lane_id),
  FOREIGN KEY (site_id) REFERENCES northwind_graph_demo.supplier_sites (site_id),
  FOREIGN KEY (warehouse_id) REFERENCES northwind_graph_demo.warehouses (warehouse_id)
);
COMMENT ON TABLE northwind_graph_demo.lane_site_assignments IS 'SYNTHETIC graph demonstration only; not operational evidence.';
CREATE INDEX ON northwind_graph_demo.lane_site_assignments (lane_id);
CREATE INDEX ON northwind_graph_demo.lane_site_assignments (site_id);
CREATE INDEX ON northwind_graph_demo.lane_site_assignments (warehouse_id);

CREATE TABLE northwind_graph_demo.site_material_approvals (
  approval_id integer PRIMARY KEY,
  site_id integer NOT NULL,
  family_id integer NOT NULL,
  standard_id integer NOT NULL,
  approval_status text NOT NULL CHECK (approval_status = 'illustrative_only'),
  is_demo boolean NOT NULL DEFAULT true CHECK (is_demo),
  provenance text NOT NULL,
  FOREIGN KEY (site_id) REFERENCES northwind_graph_demo.supplier_sites (site_id),
  FOREIGN KEY (family_id) REFERENCES northwind_graph_demo.material_families (family_id),
  FOREIGN KEY (standard_id) REFERENCES northwind_graph_demo.certification_standards (standard_id)
);
COMMENT ON TABLE northwind_graph_demo.site_material_approvals IS 'SYNTHETIC graph demonstration only; not operational evidence.';
CREATE INDEX ON northwind_graph_demo.site_material_approvals (site_id);
CREATE INDEX ON northwind_graph_demo.site_material_approvals (family_id);
CREATE INDEX ON northwind_graph_demo.site_material_approvals (standard_id);
