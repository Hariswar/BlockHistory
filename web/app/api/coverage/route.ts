import { NextResponse } from "next/server";
import { sheets } from "@/lib/data";
import { presentSheet } from "@/lib/present";

export const runtime = "nodejs";
export const dynamic = "force-dynamic"; // read the database on each request, not at build time

// The processed sheets' outlines, so the map can show where search works today.
export async function GET() {
  try {
    return NextResponse.json({ sheets: (await sheets()).map(presentSheet) });
  } catch (e) {
    console.error(e);
    return NextResponse.json({ sheets: [] }, { status: 503 });
  }
}
