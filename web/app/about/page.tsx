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
            <li>One map year: 1938 (Sanborn St. Louis Vol. 12). 1950 is next.</li>
            <li>
              17 map sheets: much of Carondelet between Iron St. and the River des Peres, with gaps
              (the outlined areas on the map). More are being added.
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
            <li>Sheets are matched to today&apos;s streets, typically within 1–4 m.</li>
            <li>People check findings against the map; each listing says whether it was checked.</li>
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
          <strong>91%</strong>
          <span>of flags are real sites</span>
        </div>
        <div>
          <strong>14 of 15</strong>
          <span>gasoline-tank sites found</span>
        </div>
      </div>
      <p className="small">
        Measured on 10 sheets checked by hand (119 sites). Some listings are wrong and some past
        uses are missing, so every listing links to the map image for you to check.
      </p>
    </article>
  );
}
