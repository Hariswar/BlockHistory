import type { Metadata } from "next";
import Link from "next/link";
import { streets } from "@/lib/streets";

export const dynamic = "force-dynamic";

export const metadata: Metadata = {
  title: "Streets · BlockHistory",
  description:
    "Past uses along each Carondelet street on the 1938 and 1950 fire insurance maps: gas stations, garages, foundries and other businesses that sometimes left soil contamination.",
};

export default async function Streets() {
  const list = await streets();
  const years = [...new Set(list.flatMap((s) => Object.keys(s.counts)))].sort();
  return (
    <article className="prose">
      <h1>Browse by street</h1>
      <p>
        Past uses on the {years.join(" and ")} fire insurance maps, by the street they face today.
        Each street page lists them in order along the street. They are historical uses, not test
        results.
      </p>
      <table>
        <thead>
          <tr>
            <th>Street</th>
            {years.map((y) => (
              <th key={y}>{y} map</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {list.map((s) => (
            <tr key={s.slug}>
              <td>
                <Link href={`/streets/${s.slug}`}>{s.name}</Link>
              </td>
              {years.map((y) => (
                <td key={y}>{s.counts[y] ?? 0}</td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
      <p className="small">
        Sites are matched to the nearest street by position (OpenStreetMap). A corner business can
        show on the cross street, and buildings deep inside large plants aren&apos;t on any street
        page; search an address to see everything within 100 m.
      </p>
    </article>
  );
}
