// Address -> point with the free US Census geocoder (no key). Server-side only: the
// Census API doesn't allow browser requests. It interpolates along address ranges, so
// a point can be 30-80 m from the actual building; the page says so.
const URL_BASE = "https://geocoding.geo.census.gov/geocoder/locations/onelineaddress";
const cache = new Map<string, Geocoded | null>();

export type Geocoded = { lat: number; lon: number; matched: string };

export async function geocode(address: string): Promise<Geocoded | null> {
  const query = /,/.test(address) ? address : `${address}, St. Louis, MO`;
  const key = query.toLowerCase().trim();
  if (cache.has(key)) return cache.get(key)!;
  const url = `${URL_BASE}?${new URLSearchParams({
    address: query,
    benchmark: "Public_AR_Current",
    format: "json",
  })}`;
  const res = await fetch(url, { signal: AbortSignal.timeout(20_000) });
  if (!res.ok) throw new Error(`Census geocoder: HTTP ${res.status}`);
  const match = (await res.json()).result?.addressMatches?.[0];
  const out = match
    ? { lat: match.coordinates.y, lon: match.coordinates.x, matched: match.matchedAddress }
    : null;
  cache.set(key, out);
  return out;
}
