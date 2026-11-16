// Called once a day by Vercel Cron (web/vercel.json). Supabase's free tier pauses a project
// after 7 days without database activity, which takes the site down; one small query a day
// keeps it awake. If CRON_SECRET is set in Vercel, only Vercel's cron can call this.
import { NextResponse } from "next/server";
import { backend, sheets } from "@/lib/data";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

export async function GET(req: Request) {
  const secret = process.env.CRON_SECRET;
  if (secret && req.headers.get("authorization") !== `Bearer ${secret}`) {
    return NextResponse.json({ error: "unauthorized" }, { status: 401 });
  }
  try {
    const n = (await sheets()).length;
    return NextResponse.json({ ok: true, backend, sheets: n });
  } catch (e) {
    return NextResponse.json({ ok: false, backend, error: String(e) }, { status: 502 });
  }
}
