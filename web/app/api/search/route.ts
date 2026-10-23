import { NextResponse } from "next/server";
import { lookup } from "@/lib/lookup";

export const runtime = "nodejs";

export async function GET(req: Request) {
  const { status, body } = await lookup(new URL(req.url).searchParams.get("q") ?? "");
  return NextResponse.json(body, { status });
}
