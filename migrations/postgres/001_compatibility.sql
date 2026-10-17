-- Version 1: inventoried JSON/scalar compatibility functions.

CREATE OR REPLACE FUNCTION builder_scalar_max(a bigint,b bigint) RETURNS bigint LANGUAGE SQL IMMUTABLE STRICT AS $$ SELECT GREATEST(a,b) $$;

CREATE OR REPLACE FUNCTION json_extract(document text,path text) RETURNS text LANGUAGE SQL IMMUTABLE STRICT AS $$ SELECT document::jsonb #>> string_to_array(substring(path from 3),'.') $$;

CREATE OR REPLACE FUNCTION json_each(document text,path text) RETURNS TABLE(value text) LANGUAGE SQL IMMUTABLE STRICT AS $$ SELECT item::text FROM jsonb_array_elements(COALESCE(document::jsonb #> string_to_array(substring(path from 3),'.'),'[]'::jsonb)) AS item $$;

CREATE OR REPLACE FUNCTION json_set(document text,path text,value text) RETURNS text LANGUAGE SQL IMMUTABLE AS $$ SELECT jsonb_set(document::jsonb,string_to_array(substring(path from 3),'.'),COALESCE(to_jsonb(value),'null'::jsonb),true)::text $$;

CREATE OR REPLACE FUNCTION json_set(document text,path text,value boolean) RETURNS text LANGUAGE SQL IMMUTABLE AS $$ SELECT jsonb_set(document::jsonb,string_to_array(substring(path from 3),'.'),COALESCE(to_jsonb(value),'null'::jsonb),true)::text $$;

CREATE OR REPLACE FUNCTION json_set(document text,path text,value text,path2 text,value2 text) RETURNS text LANGUAGE SQL IMMUTABLE AS $$ SELECT json_set(json_set(document,path,value),path2,value2) $$;
