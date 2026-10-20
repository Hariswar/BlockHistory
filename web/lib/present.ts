// What the browser gets for each finding: no internal fields, plus links to the source.
import { distanceM, type FindingRow, type Sheet } from "./data";

const IIIF = "https://tile.loc.gov/image-services/iiif";
const CROP_FULL_PX = 700; // square crop of the full-resolution scan around the building
const SAME_SITE_M = 40; // same kind of use this close together = one site (a plant's buildings)
const SAME_PLACE_M = 50; // same kind of use this close on two map years = still there
// The reader says so when a label runs off the tile or can't be read in full.
const CUT_OFF = /cut off|partially visible|partly visible|uncertain|unclear|illegible|not legible/i;
// A company name ("LIBERTY FOUNDRY CO.", "CARONDELET CHEMICAL WKS.") is the clearest title.
const NAMED = /\b(CO|INC|WKS|WORKS|COMPANY|CORP)\b\.?/i;

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
    reviewStatus: f.review_status as "unreviewed" | "checked_ok" | "partly_checked",
    cutOff: CUT_OFF.test(f.use),
    alsoPrinted: [] as string[],
    // Compared with the other map year at the same place: "still" there (same printed name),
    // a "similar" use nearby (same kind, different label), "not" on the other map, or "new"
    // since the earlier one. Null when only one year covers the spot.
    change: null as null | { kind: "still" | "similar" | "not" | "new"; otherYear: string },
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

// Words that name a use, for matching a label across map years ("FILL'G STA." = "FILLING
// STA"). Construction and filler words don't count.
const FILLER = new Set(
  "CONC FL FLR STA STGE STG MISC MISCL CO INC THE AND OF ST BR IR FR RM HO NO 1ST 2ND".split(" "),
);
const SPELLING: Record<string, string> = { FILLG: "FILLING", FILLNG: "FILLING", REPG: "REP", REPAIR: "REP" };

function useWords(label: string): Set<string> {
  const words = label.toUpperCase().replace(/['’.]/g, "").split(/[^A-Z0-9]+/);
  return new Set(
    words
      .map((w) => SPELLING[w] ?? w)
      .filter((w) => w.length >= 3 && !FILLER.has(w) && !/^\d+$/.test(w)),
  );
}

// Kinds of use that readers swap for one site: a garage with a gasoline tank can be read as
// "fuel" one year and "auto" the next.
const FAMILY: Record<string, string> = { fuel: "vehicles", auto: "vehicles" };
const family = (category: string) => FAMILY[category] ?? category;

/**
 * Mark each finding against the other map year(s) covering the searched spot. Within
 * SAME_PLACE_M on the other map, a finding with a shared label word is "still" there (any
 * kind) and one of a related kind is a "similar" use; with neither, the earlier year's is
 * "not" on the later map and the later year's is "new". Pass findings from a wider radius
 * than shown, so a match just outside the circle still counts.
 */
export function markChanges(found: PublicFinding[], coveredYears: string[]): PublicFinding[] {
  const years = [...new Set(coveredYears)].sort();
  if (years.length < 2) return found;
  return found.map((f) => {
    const others = years.filter((y) => y !== f.year);
    const other = f.year < others[0] ? others[0] : others[others.length - 1];
    const near = found.filter(
      (g) => g.year === other && distanceM(f.lat, f.lon, g.lat, g.lon) <= SAME_PLACE_M,
    );
    const words = useWords(f.printedLabel);
    const named = near.some((g) => [...useWords(g.printedLabel)].some((w) => words.has(w)));
    const similar = near.some((g) => family(g.category) === family(f.category));
    const kind = named ? "still" : similar ? "similar" : f.year < other ? "not" : "new";
    return { ...f, change: { kind, otherYear: other } };
  });
}

/**
 * One card per site: findings of the same kind within SAME_SITE_M of the nearest one are
 * repeat reads or parts of one plant. The card is titled by its clearest read (not cut off,
 * a company name, high concern, checked, with tanks) and lists the other printed labels. It
 * counts as checked only if every part was. Input is nearest first; so is the output.
 */
export function groupSites(found: PublicFinding[]): PublicFinding[] {
  const groups: PublicFinding[][] = [];
  for (const f of found) {
    const g = groups.find(
      (g) =>
        g[0].year === f.year &&
        g[0].category === f.category &&
        distanceM(g[0].lat, g[0].lon, f.lat, f.lon) <= SAME_SITE_M,
    );
    if (g) g.push(f);
    else groups.push([f]);
  }
  const rank = (f: PublicFinding) => [
    f.cutOff ? 1 : 0,
    NAMED.test(f.printedLabel) ? 0 : 1,
    f.relevance === "high" ? 0 : 1,
    f.reviewStatus === "checked_ok" ? 0 : 1,
    f.hasGasolineTanks ? 0 : 1,
    f.distanceM,
  ];
  const byRank = (a: PublicFinding, b: PublicFinding) => {
    const [ra, rb] = [rank(a), rank(b)];
    const i = ra.findIndex((v, k) => v !== rb[k]);
    return i < 0 ? 0 : ra[i] - rb[i];
  };
  return groups.map((g) => {
    const lead = [...g].sort(byRank)[0];
    const checked = g.filter((f) => f.reviewStatus === "checked_ok").length;
    const seen = new Set([norm(lead.printedLabel)]);
    const alsoPrinted = g
      .filter((f) => f !== lead && !f.cutOff)
      .map((f) => f.printedLabel)
      .filter((l) => !seen.has(norm(l)) && seen.add(norm(l)));
    return {
      ...lead,
      distanceM: Math.min(...g.map((f) => f.distanceM)),
      hasGasolineTanks: g.some((f) => f.hasGasolineTanks),
      reviewStatus: checked === g.length ? "checked_ok" : checked > 0 ? "partly_checked" : "unreviewed",
      alsoPrinted,
    };
  });
}

function norm(label: string) {
  return label.toUpperCase().replace(/[^A-Z]/g, "").replace("FILLING", "FILLG");
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
