import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";
import { mapLink, streetHistory, streets } from "@/lib/streets";
import type { PublicFinding } from "@/lib/present";

export const dynamic = "force-dynamic";

type Props = { params: Promise<{ slug: string }> };

async function find(slug: string) {
  return (await streets()).find((s) => s.slug === slug) ?? null;
}

function countLine(counts: Record<string, number>) {
  return Object.entries(counts)
    .sort()
    .map(([y, n]) => `${n} on the ${y} map`)
    .join(", ");
}

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const s = await find((await params).slug);
  if (!s) return { title: "Street not found · BlockHistory" };
  const title = `${s.name}: past uses · BlockHistory`;
  const description = `Past uses along ${s.name}, Carondelet, St. Louis, that sometimes left soil contamination: ${countLine(s.counts)}.`;
  const image = `/api/og?street=${encodeURIComponent(s.name)}&line=${encodeURIComponent(
    `Past uses that sometimes left soil contamination: ${countLine(s.counts)}.`,
  )}`;
  return {
    title,
    description,
    openGraph: { title, description, images: [{ url: image, width: 1200, height: 630 }] },
    twitter: { card: "summary_large_image", title, description, images: [image] },
  };
}

const CHANGE = {
  still: (y: string) => `Also on the ${y} map`,
  similar: (y: string) => `A similar use nearby on the ${y} map`,
  not: (y: string) => `Not on the ${y} map`,
  new: (y: string) => `New since the ${y} map`,
};

function Row({ f }: { f: PublicFinding }) {
  return (
    <li className="street-row">
      <div>
        <strong>{f.title}</strong>
        <span className="small">
          {" "}
          · printed “{f.printedLabel}”{f.streetNumber ? ` · No. ${f.streetNumber}` : ""}
        </span>
      </div>
      <div className="tags">
        <span className={`tag ${f.relevance}`}>
          {f.relevance === "high" ? "Often linked to contamination" : "Sometimes linked"}
        </span>
        {f.hasGasolineTanks && <span className="tag high">Gasoline tanks on the map</span>}
        {f.change && <span className="tag">{CHANGE[f.change.kind](f.change.otherYear)}</span>}
        <Link href={mapLink(f)} className="small">
          See on the map
        </Link>
      </div>
    </li>
  );
}

export default async function StreetPage({ params }: Props) {
  const s = await find((await params).slug);
  if (!s) notFound();
  const { years, byYear } = await streetHistory(s.name);
  return (
    <article className="prose street">
      <p className="small">
        <Link href="/streets">All streets</Link>
      </p>
      <h1>{s.name}</h1>
      <p>
        Businesses along {s.name} in Carondelet that sometimes left soil or groundwater
        contamination, as printed on the {years.join(" and ")} Sanborn fire insurance maps, in
        order along the street. They are historical uses, not test results; open one on the map
        for the scan, the full note and nearby state records.
      </p>
      <div className="street-years">
        {years.map((y) => (
          <section key={y}>
            <h2>
              {y} map · {byYear[y].length} {byYear[y].length === 1 ? "site" : "sites"}
            </h2>
            <ol className="street-list">
              {byYear[y].map((f) => (
                <Row key={f.id} f={f} />
              ))}
            </ol>
          </section>
        ))}
      </div>
      <p className="small">
        Matched to {s.name} by position (OpenStreetMap), so a corner business can appear on the
        cross street instead. Read from the map scans by an AI model and partly checked by a
        person; see <Link href="/limits">Limits</Link>.
      </p>
    </article>
  );
}
