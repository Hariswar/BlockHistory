import { NextResponse } from "next/server";
import { search } from "@/lib/data";
import { geocode } from "@/lib/geocode";
import { groupSites, present, presentSheet } from "@/lib/present";

export const runtime = "nodejs";
const RADIUS_M = 100;

export async function GET(req: Request) {
  const q = new URL(req.url).searchParams.get("q")?.trim() ?? "";
  if (q.length < 3 || q.length > 200) {
    return NextResponse.json({ error: "Type a street address, like 7313 S Broadway." }, { status: 400 });
  }
  let point;
  try {
    point = await geocode(q);
  } catch {
    return NextResponse.json(
      { error: "The address lookup service didn't answer. Try again in a minute." },
      { status: 502 },
    );
  }
  if (!point) {
    return NextResponse.json(
      { error: `We couldn't find "${q}" in St. Louis. Check the spelling, or add the ZIP code.` },
      { status: 404 },
    );
  }
  let found;
  try {
    found = await search(point.lat, point.lon, RADIUS_M);
  } catch (e) {
    console.error(e);
    return NextResponse.json(
      { error: "The map database didn't answer. Try again in a minute." },
      { status: 503 },
    );
  }
  const { findings, coveredBy } = found;
  return NextResponse.json({
    query: q,
    point,
    radiusM: RADIUS_M,
    coveredBy: coveredBy.map(presentSheet),
    findings: groupSites(findings.map(present)),
  });
}
