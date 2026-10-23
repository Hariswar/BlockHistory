// Address -> point, server-side only. First the City of St. Louis composite geocoder (free,
// no key): it puts an address on its parcel when it can (median 15 m from the building on
// the 1938 map, measured on 34 addresses) and otherwise interpolates along the street. If
// the city has no confident match, the US Census geocoder (median 52 m). Each result says
// which method placed it, and the page words its precision to match.
const CITY =
  "https://maps6.stlouis-mo.gov/arcgis/rest/services/GEOCODERS/COMPOSITE_GEOCODE/GeocodeServer/findAddressCandidates";
const CENSUS = "https://geocoding.geo.census.gov/geocoder/locations/onelineaddress";
const MIN_SCORE = 90; // the city service scores 0-100; lower is a guess at a different number
const cache = new Map<string, Geocoded | null>();

export type Geocoded = {
  lat: number;
  lon: number;
  matched: string;
  source: "parcel" | "street" | "census" | "point";
};

// "38.5547,-90.2492": a spot picked on the website (street pages link to their sites this
// way). Only inside St. Louis.
const POINT = /^\s*(-?\d{1,2}\.\d+)\s*,\s*(-?\d{1,3}\.\d+)\s*$/;
const ST_LOUIS = { south: 38.5, north: 38.8, west: -90.35, east: -90.15 };

function mapPoint(q: string): Geocoded | null {
  const m = q.match(POINT);
  if (!m) return null;
  const [lat, lon] = [Number(m[1]), Number(m[2])];
  const b = ST_LOUIS;
  if (lat < b.south || lat > b.north || lon < b.west || lon > b.east) return null;
  return { lat, lon, matched: "the spot on the map you followed", source: "point" };
}

export async function geocode(address: string): Promise<Geocoded | null> {
  const point = mapPoint(address);
  if (point) return point;
  const key = address.toLowerCase().replace(/\s+/g, " ").trim();
  if (cache.has(key)) return cache.get(key)!;
  let out: Geocoded | null = null;
  try {
    out = await city(address);
  } catch (e) {
    console.error("City geocoder:", e); // fall back to the Census below
  }
  out ??= await census(address);
  cache.set(key, out);
  return out;
}

async function city(address: string): Promise<Geocoded | null> {
  // The service wants just the street address: drop ", St. Louis, MO 63111" and the like.
  const street = address.split(",")[0].trim();
  const url = `${CITY}?${new URLSearchParams({
    Street: street,
    outSR: "4326",
    outFields: "Loc_name",
    maxLocations: "5",
    f: "json",
  })}`;
  const res = await fetch(url, { signal: AbortSignal.timeout(10_000) });
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  const best = ((await res.json()).candidates ?? []).find(
    (c: { score: number }) => c.score >= MIN_SCORE,
  );
  if (!best) return null;
  return {
    lat: best.location.y,
    lon: best.location.x,
    matched: `${best.address}, St. Louis, MO`,
    source: best.attributes?.Loc_name === "PARCEL_GEOCODE" ? "parcel" : "street",
  };
}

async function census(address: string): Promise<Geocoded | null> {
  const query = /,/.test(address) ? address : `${address}, St. Louis, MO`;
  const url = `${CENSUS}?${new URLSearchParams({
    address: query,
    benchmark: "Public_AR_Current",
    format: "json",
  })}`;
  const res = await fetch(url, { signal: AbortSignal.timeout(20_000) });
  if (!res.ok) throw new Error(`Census geocoder: HTTP ${res.status}`);
  const match = (await res.json()).result?.addressMatches?.[0];
  return match
    ? {
        lat: match.coordinates.y,
        lon: match.coordinates.x,
        matched: match.matchedAddress,
        source: "census",
      }
    : null;
}
