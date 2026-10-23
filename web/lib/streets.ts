// Street pages: names, links, and the order of sites along a street.
import { streetFindings } from "@/lib/data";
import { groupSites, markChanges, present, type PublicFinding } from "@/lib/present";

export function streetSlug(name: string) {
  return name.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "");
}

export type StreetSummary = { name: string; slug: string; counts: Record<string, number> };

/** Every street with its number of sites per map year, counted as the street pages do. */
export async function streets(): Promise<StreetSummary[]> {
  const rows = await streetFindings(null);
  const names = [...new Set(rows.map((r) => r.street!))].sort((a, b) => a.localeCompare(b));
  return names.map((name) => {
    const counts: Record<string, number> = {};
    for (const site of sites(rows.filter((r) => r.street === name))) {
      counts[site.year] = (counts[site.year] ?? 0) + 1;
    }
    return { name, slug: streetSlug(name), counts };
  });
}

type Row = Awaited<ReturnType<typeof streetFindings>>[number];

function sites(rows: Row[]) {
  return groupSites(markChanges(rows.map(present), [...new Set(rows.map((r) => r.edition))]));
}

/**
 * The street's shown sites per map year, in order along the street. The order follows the
 * street's long axis and is turned so printed house numbers mostly go up.
 */
export async function streetHistory(name: string) {
  const rows = await streetFindings(name);
  const found = sites(rows);
  if (!found.length) return { years: [] as string[], byYear: {} as Record<string, PublicFinding[]> };
  const kx = Math.cos((found[0].lat * Math.PI) / 180);
  const spread = (k: (f: PublicFinding) => number) =>
    Math.max(...found.map(k)) - Math.min(...found.map(k));
  const northSouth = spread((f) => f.lat) >= spread((f) => f.lon * kx);
  let along = (f: PublicFinding) => (northSouth ? -f.lat : f.lon);
  const numbered = rows
    .map((r) => ({ r, n: parseInt(r.street_number ?? "", 10) }))
    .filter((x) => Number.isFinite(x.n));
  if (numbered.length >= 3) {
    const pos = (x: (typeof numbered)[number]) => (northSouth ? -x.r.lat : x.r.lon);
    const mp = numbered.reduce((s, x) => s + pos(x), 0) / numbered.length;
    const mn = numbered.reduce((s, x) => s + x.n, 0) / numbered.length;
    const cov = numbered.reduce((s, x) => s + (pos(x) - mp) * (x.n - mn), 0);
    if (cov < 0) {
      const first = along;
      along = (f) => -first(f);
    }
  }
  const years = [...new Set(found.map((s) => s.year))].sort();
  const byYear = Object.fromEntries(
    years.map((y) => [y, found.filter((s) => s.year === y).sort((a, b) => along(a) - along(b))]),
  );
  return { years, byYear };
}

/** A search around the site, for "See on the map". */
export function mapLink(f: { lat: number; lon: number }) {
  return `/?q=${f.lat.toFixed(5)},${f.lon.toFixed(5)}`;
}
