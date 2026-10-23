// One address search, shared by the search API, link previews and preview images.
import { search } from "@/lib/data";
import { geocode } from "@/lib/geocode";
import { attachRecords, groupSites, markChanges, present, presentRecord, presentSheet } from "@/lib/present";

export const RADIUS_M = 100;
const MATCH_MARGIN_M = 50; // look this much further when comparing map years

export type Lookup = { status: number; body: Record<string, unknown> & { error?: string } };

export async function lookup(q: string): Promise<Lookup> {
  q = q.trim();
  if (q.length < 3 || q.length > 200) {
    return { status: 400, body: { error: "Type a street address, like 7313 S Broadway." } };
  }
  let point;
  try {
    point = await geocode(q);
  } catch {
    return { status: 502, body: { error: "The address lookup service didn't answer. Try again in a minute." } };
  }
  if (!point) {
    return {
      status: 404,
      body: { error: `We couldn't find "${q}" in St. Louis. Check the spelling, or add the ZIP code.` },
    };
  }
  let found;
  try {
    found = await search(point.lat, point.lon, RADIUS_M + MATCH_MARGIN_M);
  } catch (e) {
    console.error(e);
    return { status: 503, body: { error: "The map database didn't answer. Try again in a minute." } };
  }
  const { findings, coveredBy } = found;
  const records = found.records.filter((r) => r.distance_m <= RADIUS_M).map(presentRecord);
  return {
    status: 200,
    body: {
      query: q,
      point,
      radiusM: RADIUS_M,
      coveredBy: coveredBy.map(presentSheet),
      findings: attachRecords(
        groupSites(
          markChanges(
            findings.map(present),
            coveredBy.map((s) => s.edition),
          ).filter((f) => f.distanceM <= RADIUS_M),
        ),
        records,
      ),
      records,
    },
  };
}

/** "7 past uses on the 1938 map and 6 on the 1950 map" (or why there are none). */
export function lookupSummary(body: Lookup["body"]): string {
  const findings = (body.findings ?? []) as { year: string }[];
  const years = [...new Set(((body.coveredBy ?? []) as { year: string }[]).map((s) => s.year))].sort();
  if (!years.length) return "Not on the maps BlockHistory has processed yet.";
  const parts = years.map((y) => {
    const n = findings.filter((f) => f.year === y).length;
    return `${n === 0 ? "no" : n} past ${n === 1 ? "use" : "uses"} on the ${y} map`;
  });
  return `Within ${RADIUS_M} m: ${parts.join(" and ")} that sometimes left soil contamination.`;
}
