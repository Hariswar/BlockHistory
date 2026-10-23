// Preview image for shared links (1200x630): the address or street and its counts.
import { ImageResponse } from "next/og";
import { lookup, lookupSummary } from "@/lib/lookup";

export const runtime = "nodejs";

export async function GET(req: Request) {
  const params = new URL(req.url).searchParams;
  const q = params.get("q")?.trim() ?? "";
  const street = params.get("street")?.trim() ?? "";
  let heading = "What stood on your block?";
  let line = "Past uses from the 1938 and 1950 fire insurance maps of Carondelet, St. Louis.";
  if (street) {
    heading = `${street.slice(0, 60)}, past uses`;
    line = params.get("line")?.slice(0, 160) ?? line;
  } else if (q) {
    const { status, body } = await lookup(q);
    if (status === 200) {
      const point = body.point as { source: string };
      heading = `What stood near ${point.source === "point" ? "this spot" : q.slice(0, 50)}?`;
      line = lookupSummary(body);
    }
  }
  return new ImageResponse(
    (
      <div
        style={{
          width: "100%",
          height: "100%",
          display: "flex",
          flexDirection: "column",
          justifyContent: "space-between",
          padding: "64px 72px",
          background: "#f7f3ea",
          color: "#1f1d1a",
          fontFamily: "serif",
        }}
      >
        <div style={{ display: "flex", fontSize: 40, fontWeight: 700 }}>
          Block<span style={{ color: "#b23a2e" }}>History</span>
        </div>
        <div style={{ display: "flex", flexDirection: "column", gap: 24 }}>
          <div style={{ fontSize: 68, fontWeight: 700, lineHeight: 1.1 }}>{heading}</div>
          <div style={{ fontSize: 36, color: "#5f5a52", lineHeight: 1.3 }}>{line}</div>
        </div>
        <div style={{ display: "flex", fontSize: 26, color: "#5f5a52" }}>
          Historical uses from Sanborn maps (Library of Congress), not test results.
        </div>
      </div>
    ),
    { width: 1200, height: 630, headers: { "Cache-Control": "public, max-age=86400" } },
  );
}
