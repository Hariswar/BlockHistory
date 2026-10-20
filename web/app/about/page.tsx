import Link from "next/link";
import InfoTabs from "@/components/InfoTabs";

export const metadata = { title: "About · BlockHistory" };

export default function About() {
  return (
    <article className="prose">
      <InfoTabs active="about" />
      <h1>About BlockHistory</h1>
      <p>
        Fire insurance companies mapped American cities building by building. The Sanborn maps show
        what each building was used for, what it was made of, and where gasoline tanks were buried.
        BlockHistory reads those maps for Carondelet, St. Louis, and lists past uses near an address
        that sometimes left soil or groundwater contamination.{" "}
        <Link href="/limits">What it can&apos;t tell you</Link>.
      </p>

      <div className="info-grid">
        <section>
          <h2>What&apos;s covered</h2>
          <ul>
            <li>
              Two map years: 1938 (Sanborn St. Louis Vol. 12) and its 1950 update. Switch between
              them above the map; each listing says whether the other year shows it too.
            </li>
            <li>
              All of Carondelet and Patch: 46 map sheets from Bates St. to the River des Peres,
              Grand Blvd. to the river (the outlined area on the map). The 1950 scan has no sheet
              11.
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
          </ol>
        </section>
      </div>

      <h2>How accurate it is</h2>
      <div className="stats">
        <div>
          <strong>87%</strong>
          <span>of hand-checked sites found</span>
        </div>
        <div>
          <strong>92% / 89%</strong>
          <span>of AI flags right as read (1938 / 1950)</span>
        </div>
        <div>
          <strong>14 of 15</strong>
          <span>gasoline-tank sites found</span>
        </div>
      </div>
      <p className="small">
        &ldquo;Found&rdquo; and tank sites: 10 sheets annotated by hand (119 sites, 1938).
        &ldquo;Right as read&rdquo;: every listing on all 46 sheets, before the scan check fixed
        the rest. The AI misses some past uses, and a check can miss an error, so every listing
        links to the map image for you to check.
      </p>
    </article>
  );
}
