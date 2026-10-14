// What the browser gets for each finding: no internal fields, plus links to the source.
import type { FindingRow, Sheet } from "./data";

const IIIF = "https://tile.loc.gov/image-services/iiif";
const CROP_FULL_PX = 700; // square crop of the full-resolution scan around the building

export type PublicFinding = ReturnType<typeof present>;

export function present(f: FindingRow & { distance_m: number; sheet: Sheet }) {
  const s = f.sheet;
  const cx = Math.round(f.sheet_px * s.full_res_scale);
  const cy = Math.round(f.sheet_py * s.full_res_scale);
  const half = CROP_FULL_PX / 2;
  const region = `${Math.max(0, cx - half)},${Math.max(0, cy - half)},${CROP_FULL_PX},${CROP_FULL_PX}`;
  return {
    id: f.id,
    title: capitalize(f.use.split(";")[0].replace(/\s*\(.*?\)/g, "").trim() || f.label),
    printedLabel: f.label,
    category: f.category,
    relevance: f.relevance as "high" | "medium",
    explanation: f.explanation,
    hasGasolineTanks: f.gasoline_tank_count > 0,
    reviewStatus: f.review_status as "unreviewed" | "checked_ok",
    readerConfidence: f.reader_confidence,
    distanceM: f.distance_m,
    lat: f.lat,
    lon: f.lon,
    locationUncertaintyM: Math.max(5, Math.round(f.location_uncertainty_m + s.georef_error_m)),
    year: f.edition,
    sheetNumber: s.sheet_number,
    volume: s.volume,
    sourcePage: s.loc_page_url,
    sourceCrop: `${IIIF}/${s.iiif_service}/${region}/pct:50/0/default.jpg`,
  };
}

export function presentSheet(s: Sheet) {
  return {
    sheetId: s.sheet_id,
    year: s.edition,
    sheetNumber: s.sheet_number,
    volume: s.volume,
    sourcePage: s.loc_page_url,
    footprint: JSON.parse(s.footprint) as GeoJSON.Polygon,
  };
}

function capitalize(t: string) {
  return t.charAt(0).toUpperCase() + t.slice(1);
}
