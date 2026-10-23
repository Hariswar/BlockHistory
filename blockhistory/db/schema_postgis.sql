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
  street TEXT,
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
-- Today's street name for street pages (added Oct 2026; for tables made before that).
ALTER TABLE findings ADD COLUMN IF NOT EXISTS street TEXT;
CREATE INDEX IF NOT EXISTS findings_street ON findings (street);

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

-- Shown past uses on one street, or on every street when street_name is NULL (street pages).
DROP FUNCTION IF EXISTS streets_list();
DROP FUNCTION IF EXISTS street_findings(TEXT);
CREATE FUNCTION street_findings(street_name TEXT DEFAULT NULL)
RETURNS TABLE (
  id BIGINT, sheet_id TEXT, edition TEXT, label TEXT, use TEXT, street_number TEXT,
  street TEXT, relevance TEXT, category TEXT, explanation TEXT, gasoline_tank_count INTEGER,
  reader_confidence TEXT, review_status TEXT, location_method TEXT,
  location_uncertainty_m DOUBLE PRECISION, sheet_px INTEGER, sheet_py INTEGER,
  lat DOUBLE PRECISION, lon DOUBLE PRECISION, distance_m DOUBLE PRECISION
)
LANGUAGE sql STABLE SET search_path = public, extensions AS $$
  SELECT f.id, f.sheet_id, f.edition, f.label, f.use, f.street_number, f.street, f.relevance,
         f.category, f.explanation, f.gasoline_tank_count, f.reader_confidence,
         f.review_status, f.location_method, f.location_uncertainty_m, f.sheet_px, f.sheet_py,
         ST_Y(f.geom::geometry), ST_X(f.geom::geometry), 0::DOUBLE PRECISION
  FROM findings f
  WHERE f.street IS NOT NULL AND (street_name IS NULL OR f.street = street_name)
    AND f.review_status <> 'checked_wrong' AND f.relevance IN ('high', 'medium');
$$;

GRANT EXECUTE ON FUNCTION sheets_list() TO anon, authenticated;
GRANT EXECUTE ON FUNCTION street_findings(TEXT) TO anon, authenticated;
GRANT EXECUTE ON FUNCTION records_near(DOUBLE PRECISION, DOUBLE PRECISION, DOUBLE PRECISION) TO anon, authenticated;
GRANT EXECUTE ON FUNCTION sheets_covering(DOUBLE PRECISION, DOUBLE PRECISION) TO anon, authenticated;
GRANT EXECUTE ON FUNCTION findings_near(DOUBLE PRECISION, DOUBLE PRECISION, DOUBLE PRECISION) TO anon, authenticated;

-- Community notes (Phase 3): memories of what used to be on a block, and corrections to
-- listings, sent from the website. Visitors can only ADD notes, through submit_note(), which
-- checks every field and caps the rate. Nobody can read the queue through the public API:
-- review it in the Supabase Table Editor. A note shows on the site only once its status is
-- 'approved' AND public_text is filled in (the reviewer's edited wording), via notes_near().
-- The load_postgis_*.sql files never touch this table.
CREATE TABLE IF NOT EXISTS community_notes (
  id BIGSERIAL PRIMARY KEY,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  kind TEXT NOT NULL CHECK (kind IN ('memory', 'correction')),
  body TEXT NOT NULL,                 -- what the visitor wrote (never shown as is)
  decade TEXT,                        -- memories: roughly when
  source TEXT,                        -- memories: how they know (lived, worked, family, other)
  problem TEXT,                       -- corrections: wrong_use, wrong_place, other
  edition TEXT, sheet_number INTEGER, label TEXT,  -- corrections: the listing as shown
  geom GEOGRAPHY(POINT, 4326) NOT NULL,            -- rounded to about 10 m
  status TEXT NOT NULL DEFAULT 'new' CHECK (status IN ('new', 'approved', 'rejected', 'applied')),
  public_text TEXT,                   -- the wording the site shows, written by the reviewer
  reviewer_note TEXT
);
CREATE INDEX IF NOT EXISTS community_notes_geom ON community_notes USING GIST (geom);
CREATE INDEX IF NOT EXISTS community_notes_new ON community_notes (status, created_at);
ALTER TABLE community_notes ENABLE ROW LEVEL SECURITY;  -- and no policies: no direct access
REVOKE ALL ON community_notes FROM anon, authenticated;
REVOKE ALL ON SEQUENCE community_notes_id_seq FROM anon, authenticated;

DROP FUNCTION IF EXISTS submit_note(TEXT, TEXT, DOUBLE PRECISION, DOUBLE PRECISION, TEXT, TEXT, TEXT, TEXT, INTEGER, TEXT);
CREATE FUNCTION submit_note(
  p_kind TEXT, p_body TEXT, p_lat DOUBLE PRECISION, p_lon DOUBLE PRECISION,
  p_decade TEXT DEFAULT NULL, p_source TEXT DEFAULT NULL, p_problem TEXT DEFAULT NULL,
  p_edition TEXT DEFAULT NULL, p_sheet_number INTEGER DEFAULT NULL, p_label TEXT DEFAULT NULL
)
RETURNS TEXT
LANGUAGE plpgsql SECURITY DEFINER SET search_path = public, extensions AS $$
DECLARE
  b TEXT := btrim(coalesce(p_body, ''));
BEGIN
  -- Messages starting "note:" are shown to the visitor by the website.
  IF p_kind NOT IN ('memory', 'correction') THEN RAISE EXCEPTION 'note: unknown kind'; END IF;
  IF length(b) < 10 THEN RAISE EXCEPTION 'note: Please write a little more (at least 10 characters).'; END IF;
  IF length(b) > 1000 THEN RAISE EXCEPTION 'note: Please keep it under 1000 characters.'; END IF;
  IF b ~* '(https?://|www\.)' THEN RAISE EXCEPTION 'note: Please leave out links.'; END IF;
  IF p_lat IS NULL OR p_lon IS NULL OR p_lat NOT BETWEEN 38.525 AND 38.575
     OR p_lon NOT BETWEEN -90.29 AND -90.225 THEN
    RAISE EXCEPTION 'note: Notes can only be added for places in Carondelet and Patch.';
  END IF;
  IF p_kind = 'memory' AND (
       p_decade IS NULL OR p_decade NOT IN ('before 1940', '1940s', '1950s', '1960s', '1970s',
                                          '1980s', '1990s', '2000s or later', 'not sure')
       OR (p_source IS NOT NULL AND p_source NOT IN ('lived', 'worked', 'family', 'other'))) THEN
    RAISE EXCEPTION 'note: unknown decade or source';
  END IF;
  IF p_kind = 'correction' AND (
       p_problem IS NULL OR p_problem NOT IN ('wrong_use', 'wrong_place', 'other')
       OR coalesce(p_edition, '') NOT IN ('1938', '1950') OR p_label IS NULL OR length(p_label) > 200) THEN
    RAISE EXCEPTION 'note: unknown problem or listing';
  END IF;
  -- Flood guard for the whole site: a neighborhood site gets nowhere near this honestly.
  IF (SELECT count(*) FROM community_notes WHERE created_at > now() - interval '1 hour') >= 30 THEN
    RAISE EXCEPTION 'note: Lots of notes are coming in right now. Please try again in an hour.';
  END IF;
  INSERT INTO community_notes (kind, body, decade, source, problem, edition, sheet_number, label, geom)
  VALUES (p_kind, b,
          CASE WHEN p_kind = 'memory' THEN p_decade END,
          CASE WHEN p_kind = 'memory' THEN p_source END,
          CASE WHEN p_kind = 'correction' THEN p_problem END,
          CASE WHEN p_kind = 'correction' THEN p_edition END,
          CASE WHEN p_kind = 'correction' THEN p_sheet_number END,
          CASE WHEN p_kind = 'correction' THEN p_label END,
          ST_Point(round(p_lon::numeric, 4)::float8, round(p_lat::numeric, 4)::float8, 4326)::geography);
  RETURN 'ok';
END;
$$;

-- Approved memories near a point: only the reviewer's wording, nothing the visitor typed.
DROP FUNCTION IF EXISTS notes_near(DOUBLE PRECISION, DOUBLE PRECISION, DOUBLE PRECISION);
CREATE FUNCTION notes_near(at_lat DOUBLE PRECISION, at_lon DOUBLE PRECISION,
                           radius_m DOUBLE PRECISION DEFAULT 100)
RETURNS TABLE (id BIGINT, public_text TEXT, decade TEXT, source TEXT, distance_m DOUBLE PRECISION)
LANGUAGE sql STABLE SECURITY DEFINER SET search_path = public, extensions AS $$
  SELECT n.id, n.public_text, n.decade, n.source,
         ST_Distance(n.geom, ST_Point(at_lon, at_lat, 4326)::geography)
  FROM community_notes n
  WHERE n.kind = 'memory' AND n.status = 'approved' AND n.public_text IS NOT NULL
    AND ST_DWithin(n.geom, ST_Point(at_lon, at_lat, 4326)::geography, LEAST(radius_m, 500))
  ORDER BY 5;
$$;

REVOKE EXECUTE ON FUNCTION submit_note(TEXT, TEXT, DOUBLE PRECISION, DOUBLE PRECISION, TEXT, TEXT, TEXT, TEXT, INTEGER, TEXT) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION submit_note(TEXT, TEXT, DOUBLE PRECISION, DOUBLE PRECISION, TEXT, TEXT, TEXT, TEXT, INTEGER, TEXT) TO anon, authenticated;
GRANT EXECUTE ON FUNCTION notes_near(DOUBLE PRECISION, DOUBLE PRECISION, DOUBLE PRECISION) TO anon, authenticated;
