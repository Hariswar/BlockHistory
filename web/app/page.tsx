import type { Metadata } from "next";
import Search from "@/components/Search";
import { lookup, lookupSummary } from "@/lib/lookup";
import { AREA, yearsText } from "@/lib/site";

type Props = { searchParams: Promise<{ q?: string }> };

// A shared search link previews as "What stood near 7313 S Broadway?" with its counts.
export async function generateMetadata({ searchParams }: Props): Promise<Metadata> {
  const q = (await searchParams).q?.trim();
  if (!q) return {};
  const { status, body } = await lookup(q);
  if (status !== 200) return { title: "BlockHistory" };
  const place = (body.point as { source: string }).source === "point" ? "this spot" : q;
  const title = `What stood near ${place}? · BlockHistory`;
  const description = lookupSummary(body);
  const image = `/api/og?q=${encodeURIComponent(q)}`;
  return {
    title,
    description,
    openGraph: { title, description, images: [{ url: image, width: 1200, height: 630 }] },
    twitter: { card: "summary_large_image", title, description, images: [image] },
  };
}

export default function Home() {
  return (
    <>
      <section className="hero">
        <h1>What stood on your block?</h1>
        <p>
          Type a street address in {AREA.place}. BlockHistory looks at the {yearsText()} Sanborn
          fire insurance maps and lists past uses within 100 meters that sometimes left
          soil or groundwater contamination, like gas stations, garages, dry cleaners and
          foundries. Or <a href="/streets">browse by street</a>.
        </p>
      </section>
      <Search />
    </>
  );
}
