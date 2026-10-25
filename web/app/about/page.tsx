import Link from "next/link";
import InfoTabs from "@/components/InfoTabs";
import { SCORES, percent, rate } from "@/lib/accuracy";

export const metadata = { title: "About · BlockHistory" };

export default function About() {
  const found = rate("1938", "sites found") ?? [0, 1];
  const asRead38 = rate("1938", "listings right as read") ?? [0, 1];
  const asRead50 = rate("1950", "listings right as read") ?? [0, 1];
  const tanks = rate("1938", "tank sites found") ?? [0, 1];
  return (
    <article className="prose">
      <InfoTabs active="about" />
      <h1>About BlockHistory</h1>
      <p>
        Fire insurance companies mapped American cities building by building. The Sanborn maps show
        what each building was used for, what it was made of, and where gasoline tanks were buried.
        BlockHistory reads those maps for Carondelet, St. Louis, and lists past uses near an address
        that sometimes left soil or groundwater contamination.{" "}
        <Link href="/limits">What it can&apos;t tell you</Link>.{" "}
        <a href="https://github.com/Hariswar/BlockHistory/blob/main/docs/writeup.md">
          How it was built
        </a>
        .
      </p>

      <div className="info-grid">
        <section>
          <h2>What&apos;s covered</h2>
          <ul>
            <li>
              Three map years: 1908 (Sanborn St. Louis Vol. 8), 1938 (Vol. 12) and its 1950
              update. Switch between them above the map; each listing says whether the map before
              and after it shows it too.
            </li>
            <li>
              All of Carondelet and Patch: 46 map sheets from Bates St. to the River des Peres,
              Grand Blvd. to the river (the outlined area on the map) for 1938 and 1950; the 1950
              scan has no sheet 11. The 1908 map is drawn at twice the scale; 48 of its sheets cover
              most of the same area, except a few blocks where streets were re-laid after the River
              des Peres was moved.
            </li>
          </ul>
        </section>
        <section>
          <h2>How it works</h2>
          <ol>
            <li>Map scans come from the Library of Congress.</li>
            <li>
              An AI model (Claude Haiku) reads each sheet&apos;s business labels and gasoline-tank
              symbols.
            </li>
            <li>Sheets are matched to today&apos;s streets, typically within 1–7 m.</li>
            <li>
              Every listing was then compared with the full-resolution scan, and wrong ones were
              fixed or removed. Listings the project&apos;s author also checked say so.
            </li>
            <li>
              The note on each listing explains that kind of business in plain words. The middle
              sentence is written by the AI model from the printed label and checked by fixed
              rules (no claims about a property, no health claims); the rest is fixed wording.
            </li>
            <li>
              Each search also lists the Missouri Department of Natural Resources&apos; tank and
              cleanup records nearby, and puts a record on a listing when both are at the same spot.
            </li>
          </ol>
        </section>
      </div>

      <h2>How accurate it is</h2>
      <div className="stats">
        <div>
          <strong>{percent(found)}</strong>
          <span>of hand-checked sites found (1938)</span>
        </div>
        <div>
          <strong>
            {percent(asRead38)} / {percent(asRead50)}
          </strong>
          <span>of listings right as read (1938 / 1950)</span>
        </div>
        <div>
          <strong>
            {tanks[0]} of {tanks[1]}
          </strong>
          <span>gasoline-tank sites found (1938)</span>
        </div>
      </div>
      <p className="small">
        &ldquo;Found&rdquo; and tank sites: {SCORES["1938"].key_sheets} sheets annotated by hand (
        {found[1]} sites). &ldquo;Right as read&rdquo;: every listing on all 46 sheets, before the
        scan check fixed the rest. The AI misses some past uses, and a check can miss an error, so
        every listing links to the map image for you to check.{" "}
        <Link href="/accuracy">All the numbers, by map year</Link>.
      </p>
    </article>
  );
}
