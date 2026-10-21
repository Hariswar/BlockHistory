-- BlockHistory on Supabase (Postgres + PostGIS). Same tables as blockhistory/db/store.py,
-- with geography columns instead of lat/lon.
-- 1. Run this whole file once in the Supabase SQL editor (safe to re-run).
-- 2. Then run data/export/load_postgis_1.sql, _2.sql, ... in order (scripts/build_db.py --export).
-- The website reads with the public (anon / publishable) key: row-level security lets
-- anyone read and no one write. Loading is done here in the SQL editor, as the owner.

CREATE EXTENSION IF NOT EXISTS postgis WITH SCHEMA extensions;
SET search_path = public, extensions;

CREATE TABLE IF NOT EXISTS sheets (
  sheet_id TEXT PRIMARY KEY,
  area TEXT, edition TEXT, sheet_number INTEGER, volume TEXT,
  loc_page_url TEXT,
  iiif_service TEXT,
  scale_m_per_px DOUBLE PRECISION,
  full_res_scale DOUBLE PRECISION,
  georef_error_m DOUBLE PRECISION,
  footprint GEOGRAPHY(POLYGON, 4326)
);

CREATE TABLE IF NOT EXISTS findings (
  id BIGSERIAL PRIMARY KEY,
  sheet_id TEXT REFERENCES sheets(sheet_id) ON DELETE CASCADE,
  edition TEXT,
  label TEXT,
  use TEXT,
  street_number TEXT,
  relevance TEXT,
  category TEXT,
  explanation TEXT,
  gasoline_tank_count INTEGER,
  reader_confidence TEXT,
  review_status TEXT,
  location_method TEXT,
  location_uncertainty_m DOUBLE PRECISION,
  sheet_px INTEGER, sheet_py INTEGER,
  geom GEOGRAPHY(POINT, 4326)
);
CREATE INDEX IF NOT EXISTS findings_geom ON findings USING GIST (geom);

-- Official environmental records (state tank and cleanup sites), shown beside the map's
-- past uses. Loaded by scripts/load_records.py.
CREATE TABLE IF NOT EXISTS records (
  id BIGSERIAL PRIMARY KEY,
  source TEXT, kind TEXT, name TEXT, address TEXT,
  status TEXT, status_plain TEXT, release BOOLEAN,
  contaminants TEXT, detail TEXT, url TEXT, located_by TEXT,
  geom GEOGRAPHY(POINT, 4326)
);
CREATE INDEX IF NOT EXISTS records_geom ON records USING GIST (geom);
CREATE INDEX IF NOT EXISTS sheets_footprint ON sheets USING GIST (footprint);

-- Read-only for the public key. Newer Supabase projects don't grant table access to anon
-- automatically, so grant SELECT (only) here; row-level security below still applies.
GRANT USAGE ON SCHEMA public TO anon, authenticated;
GRANT SELECT ON sheets, findings, records TO anon, authenticated;
REVOKE INSERT, UPDATE, DELETE, TRUNCATE ON sheets, findings, records FROM anon, authenticated;
ALTER TABLE sheets ENABLE ROW LEVEL SECURITY;
ALTER TABLE findings ENABLE ROW LEVEL SECURITY;
ALTER TABLE records ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "public read" ON sheets;
DROP POLICY IF EXISTS "public read" ON findings;
DROP POLICY IF EXISTS "public read" ON records;
CREATE POLICY "public read" ON sheets FOR SELECT TO anon, authenticated USING (true);
CREATE POLICY "public read" ON findings FOR SELECT TO anon, authenticated USING (true);
CREATE POLICY "public read" ON records FOR SELECT TO anon, authenticated USING (true);

-- Sheets with their outline as GeoJSON text (the shape web/lib/data.ts expects).
CREATE OR REPLACE FUNCTION sheets_list()
RETURNS TABLE (
  sheet_id TEXT, edition TEXT, sheet_number INTEGER, volume TEXT, loc_page_url TEXT,
  iiif_service TEXT, full_res_scale DOUBLE PRECISION, georef_error_m DOUBLE PRECISION,
  footprint TEXT
)
LANGUAGE sql STABLE SET search_path = public, extensions AS $$
  SELECT s.sheet_id, s.edition, s.sheet_number, s.volume, s.loc_page_url, s.iiif_service,
         s.full_res_scale, s.georef_error_m, ST_AsGeoJSON(s.footprint)
  FROM sheets s ORDER BY s.sheet_number;
$$;

-- Processed sheets that cover a point ("not covered yet" vs "nothing found").
DROP FUNCTION IF EXISTS sheets_covering(DOUBLE PRECISION, DOUBLE PRECISION);
CREATE FUNCTION sheets_covering(at_lat DOUBLE PRECISION, at_lon DOUBLE PRECISION)
RETURNS SETOF TEXT
LANGUAGE sql STABLE SET search_path = public, extensions AS $$
  SELECT s.sheet_id FROM sheets s
  WHERE ST_Covers(s.footprint, ST_Point(at_lon, at_lat, 4326)::geography);
$$;

-- The 100 m query: shown findings near a point, nearest first (radius capped at 500 m).
DROP FUNCTION IF EXISTS findings_near(DOUBLE PRECISION, DOUBLE PRECISION, DOUBLE PRECISION);
CREATE FUNCTION findings_near(at_lat DOUBLE PRECISION, at_lon DOUBLE PRECISION,
                              radius_m DOUBLE PRECISION DEFAULT 100)
RETURNS TABLE (
  id BIGINT, sheet_id TEXT, edition TEXT, label TEXT, use TEXT, street_number TEXT,
  relevance TEXT, category TEXT, explanation TEXT, gasoline_tank_count INTEGER,
  reader_confidence TEXT, review_status TEXT, location_method TEXT,
  location_uncertainty_m DOUBLE PRECISION, sheet_px INTEGER, sheet_py INTEGER,
  lat DOUBLE PRECISION, lon DOUBLE PRECISION, distance_m DOUBLE PRECISION
)
LANGUAGE sql STABLE SET search_path = public, extensions AS $$
  SELECT f.id, f.sheet_id, f.edition, f.label, f.use, f.street_number, f.relevance,
         f.category, f.explanation, f.gasoline_tank_count, f.reader_confidence,
         f.review_status, f.location_method, f.location_uncertainty_m, f.sheet_px, f.sheet_py,
         ST_Y(f.geom::geometry), ST_X(f.geom::geometry),
         ST_Distance(f.geom, ST_Point(at_lon, at_lat, 4326)::geography)
  FROM findings f
  WHERE ST_DWithin(f.geom, ST_Point(at_lon, at_lat, 4326)::geography,
                   LEAST(radius_m, 500))
    AND f.review_status <> 'checked_wrong'
    AND f.relevance IN ('high', 'medium')
  ORDER BY 19;
$$;

-- Official records near a point, nearest first (radius capped at 500 m).
DROP FUNCTION IF EXISTS records_near(DOUBLE PRECISION, DOUBLE PRECISION, DOUBLE PRECISION);
CREATE FUNCTION records_near(at_lat DOUBLE PRECISION, at_lon DOUBLE PRECISION,
                             radius_m DOUBLE PRECISION DEFAULT 100)
RETURNS TABLE (
  id BIGINT, source TEXT, kind TEXT, name TEXT, address TEXT, status TEXT, status_plain TEXT,
  release BOOLEAN, contaminants TEXT, detail TEXT, url TEXT, located_by TEXT,
  lat DOUBLE PRECISION, lon DOUBLE PRECISION, distance_m DOUBLE PRECISION
)
LANGUAGE sql STABLE SET search_path = public, extensions AS $$
  SELECT r.id, r.source, r.kind, r.name, r.address, r.status, r.status_plain, r.release,
         r.contaminants, r.detail, r.url, r.located_by,
         ST_Y(r.geom::geometry), ST_X(r.geom::geometry),
         ST_Distance(r.geom, ST_Point(at_lon, at_lat, 4326)::geography)
  FROM records r
  WHERE ST_DWithin(r.geom, ST_Point(at_lon, at_lat, 4326)::geography, LEAST(radius_m, 500))
  ORDER BY 15;
$$;

GRANT EXECUTE ON FUNCTION sheets_list() TO anon, authenticated;
GRANT EXECUTE ON FUNCTION records_near(DOUBLE PRECISION, DOUBLE PRECISION, DOUBLE PRECISION) TO anon, authenticated;
GRANT EXECUTE ON FUNCTION sheets_covering(DOUBLE PRECISION, DOUBLE PRECISION) TO anon, authenticated;
GRANT EXECUTE ON FUNCTION findings_near(DOUBLE PRECISION, DOUBLE PRECISION, DOUBLE PRECISION) TO anon, authenticated;
