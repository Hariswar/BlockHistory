// Read side of the findings database.
// With SUPABASE_URL and SUPABASE_ANON_KEY set (web/.env.local, or the host's settings), it
// calls the Postgres functions in blockhistory/db/schema_postgis.sql. Otherwise it reads the
// local SQLite file built by scripts/build_db.py. Both give the same answers; keep the
// SQLite branch in step with blockhistory/db/store.py:search().
import type { DatabaseSync } from "node:sqlite";
import path from "node:path";

const DB_PATH =
  process.env.BLOCKHISTORY_DB ?? path.join(process.cwd(), "..", "data", "blockhistory.sqlite");
const M_PER_DEG = 111_320;
const SHOWN = ["high", "medium"];

export type Sheet = {
  sheet_id: string;
  edition: string;
  sheet_number: number;
  volume: string;
  loc_page_url: string;
  iiif_service: string;
  full_res_scale: number;
  georef_error_m: number;
  footprint: string;
};

export type FindingRow = {
  id: number;
  sheet_id: string;
  edition: string;
  label: string;
  use: string;
  street_number: string | null;
  relevance: string;
  category: string;
  explanation: string;
  gasoline_tank_count: number;
  reader_confidence: string | null;
  review_status: string;
  lat: number;
  lon: number;
  location_method: string;
  location_uncertainty_m: number;
  sheet_px: number;
  sheet_py: number;
};

const SUPABASE_URL = process.env.SUPABASE_URL?.replace(/\/$/, "");
const SUPABASE_KEY = process.env.SUPABASE_ANON_KEY;
export const backend = SUPABASE_URL && SUPABASE_KEY ? "supabase" : "sqlite";

async function rpc<T>(fn: string, args: Record<string, number> = {}): Promise<T> {
  const headers: Record<string, string> = { apikey: SUPABASE_KEY!, "Content-Type": "application/json" };
  // Legacy anon keys are JWTs and also go in Authorization; new sb_publishable_ keys don't.
  if (SUPABASE_KEY!.startsWith("eyJ")) headers.Authorization = `Bearer ${SUPABASE_KEY}`;
  const res = await fetch(`${SUPABASE_URL}/rest/v1/rpc/${fn}`, {
    method: "POST",
    headers,
    body: JSON.stringify(args),
    cache: "no-store",
    signal: AbortSignal.timeout(15_000),
  });
  if (!res.ok) throw new Error(`Supabase ${fn}: HTTP ${res.status} ${await res.text()}`);
  return res.json() as Promise<T>;
}

let db: DatabaseSync | null = null;
async function open(): Promise<DatabaseSync> {
  if (!db) {
    const { DatabaseSync } = await import("node:sqlite");
    db = new DatabaseSync(DB_PATH, { readOnly: true });
  }
  return db;
}

export function distanceM(lat1: number, lon1: number, lat2: number, lon2: number): number {
  const kx = M_PER_DEG * Math.cos((((lat1 + lat2) / 2) * Math.PI) / 180);
  return Math.hypot((lat1 - lat2) * M_PER_DEG, (lon1 - lon2) * kx);
}

function inside(lat: number, lon: number, footprint: string): boolean {
  const ring: [number, number][] = JSON.parse(footprint).coordinates[0];
  let hit = false;
  for (let i = 0; i < ring.length - 1; i++) {
    const [x1, y1] = ring[i];
    const [x2, y2] = ring[i + 1];
    if (y1 > lat !== y2 > lat && lon < x1 + ((lat - y1) * (x2 - x1)) / (y2 - y1)) hit = !hit;
  }
  return hit;
}

export async function sheets(): Promise<Sheet[]> {
  if (backend === "supabase") return rpc<Sheet[]>("sheets_list");
  return (await open()).prepare("SELECT * FROM sheets ORDER BY sheet_number").all() as unknown as Sheet[];
}

export async function search(lat: number, lon: number, radiusM = 100) {
  if (backend === "supabase") {
    const [rows, covering, all] = await Promise.all([
      rpc<(FindingRow & { distance_m: number })[]>("findings_near", { at_lat: lat, at_lon: lon, radius_m: radiusM }),
      rpc<string[]>("sheets_covering", { at_lat: lat, at_lon: lon }),
      sheets(),
    ]);
    const bySheet = new Map(all.map((s) => [s.sheet_id, s]));
    return {
      findings: rows.map((r) => ({ ...r, distance_m: Math.round(r.distance_m), sheet: bySheet.get(r.sheet_id)! })),
      coveredBy: all.filter((s) => covering.includes(s.sheet_id)),
    };
  }
  const dlat = radiusM / M_PER_DEG;
  const dlon = radiusM / (M_PER_DEG * Math.cos((lat * Math.PI) / 180));
  const rows = (await open())
    .prepare(
      `SELECT * FROM findings
       WHERE lat BETWEEN ? AND ? AND lon BETWEEN ? AND ?
         AND review_status != 'checked_wrong'`,
    )
    .all(lat - dlat, lat + dlat, lon - dlon, lon + dlon) as unknown as FindingRow[];
  const bySheet = new Map((await sheets()).map((s) => [s.sheet_id, s]));
  const findings = rows
    .filter((r) => SHOWN.includes(r.relevance))
    .map((r) => ({ ...r, distance_m: Math.round(distanceM(lat, lon, r.lat, r.lon)) }))
    .filter((r) => r.distance_m <= radiusM)
    .sort((a, b) => a.distance_m - b.distance_m)
    .map((r) => ({ ...r, sheet: bySheet.get(r.sheet_id)! }));
  const coveredBy = [...bySheet.values()].filter((s) => inside(lat, lon, s.footprint));
  return { findings, coveredBy };
}
