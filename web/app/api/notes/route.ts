// Visitors' notes: memories of a block and corrections to listings. They go to a review
// queue (community_notes in Supabase); nothing shows on the site until it's approved.
import { NextResponse } from "next/server";
import { submitNote, type NewNote } from "@/lib/data";

export const runtime = "nodejs";

const DECADES = ["before 1940", "1940s", "1950s", "1960s", "1970s", "1980s", "1990s", "2000s or later", "not sure"];
const SOURCES = ["lived", "worked", "family", "other"];
const PROBLEMS = ["wrong_use", "wrong_place", "other"];
const MIN_FORM_MS = 3000; // a person takes longer than this to write a note

const bad = (error: string) => NextResponse.json({ error }, { status: 400 });

export async function POST(req: Request) {
  let b: Record<string, unknown>;
  try {
    b = await req.json();
  } catch {
    return bad("Something went wrong sending your note.");
  }
  // Spam traps: a hidden field people never fill, and a minimum time on the form. Bots get
  // a normal-looking answer so they don't adapt.
  if (b.website || Number(b.elapsedMs) < MIN_FORM_MS) return NextResponse.json({ ok: true });
  const text = typeof b.text === "string" ? b.text.trim() : "";
  const lat = Number(b.lat);
  const lon = Number(b.lon);
  if (!Number.isFinite(lat) || !Number.isFinite(lon)) return bad("Search for an address first.");
  let note: NewNote;
  if (b.kind === "memory") {
    if (!DECADES.includes(String(b.decade))) return bad("Pick roughly when.");
    if (b.source && !SOURCES.includes(String(b.source))) return bad("Pick how you know.");
    note = {
      p_kind: "memory",
      p_body: text,
      p_lat: lat,
      p_lon: lon,
      p_decade: String(b.decade),
      ...(b.source ? { p_source: String(b.source) } : {}),
    };
  } else if (b.kind === "correction") {
    if (!PROBLEMS.includes(String(b.problem))) return bad("Pick what's wrong.");
    note = {
      p_kind: "correction",
      p_body: text,
      p_lat: lat,
      p_lon: lon,
      p_problem: String(b.problem),
      p_edition: String(b.year),
      p_sheet_number: Number(b.sheetNumber),
      p_label: String(b.label).slice(0, 200),
    };
  } else {
    return bad("Something went wrong sending your note.");
  }
  const problem = await submitNote(note);
  return problem ? bad(problem) : NextResponse.json({ ok: true });
}
