import type { Metadata } from "next";
import Link from "next/link";
import InfoTabs from "@/components/InfoTabs";
import { CHECKED_ON, SCORES, percent, rate } from "@/lib/accuracy";
import { AREA } from "@/lib/site";

export const metadata: Metadata = {
  title: "Accuracy · BlockHistory",
  description: `How often BlockHistory's map reading is right, by map year, for ${AREA.name}.`,
};

const ROWS: { name: string; label: string; note: string }[] = [
  {
    name: "sites found",
    label: "Past uses found",
    note: "of the sites marked by hand on the answer-key sheets",
  },
  {
    name: "high-concern sites found",
    label: "Higher-concern uses found",
    note: "filling stations, garages, dry cleaners, foundries and the like",
  },
  {
    name: "flags that are real sites",
    label: "Flags that are real",
    note: "of the AI's flagged uses on the answer-key sheets",
  },
  {
    name: "listings right as read",
    label: "Listings right as read",
    note: "every shown listing, compared with the scan before mistakes were fixed",
  },
  {
    name: "tank sites found",
    label: "Gasoline-tank sites found",
    note: "sites with tank symbols on the answer-key sheets",
  },
  {
    name: "exact tank counts",
    label: "Exact tank counts",
    note: "of those tank sites",
  },
];

function longDate(iso: string): string {
  return new Date(`${iso}T12:00:00`).toLocaleDateString("en-US", {
    year: "numeric",
    month: "long",
    day: "numeric",
  });
}

export default function Accuracy() {
  const years = AREA.years.filter((y) => SCORES[y]);
  return (
    <article className="prose">
      <InfoTabs active="accuracy" />
      <h1>How accurate it is</h1>
      <p>
        An AI model reads the map labels, so it misses some past uses and misreads others. These
        numbers measure how often, for {AREA.name}, by map year. They are rerun after every change
        to the map reading; last checked {longDate(CHECKED_ON)}.
      </p>

      <div className="table-scroll">
        <table className="scores">
          <caption>Map reading</caption>
          <thead>
            <tr>
              <th scope="col">Measure</th>
              {years.map((y) => (
                <th scope="col" key={y}>
                  {y}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {ROWS.map((r) => (
              <tr key={r.name}>
                <th scope="row">
                  {r.label}
                  <span>{r.note}</span>
                </th>
                {years.map((y) => {
                  const v = rate(y, r.name);
                  return (
                    <td key={y}>
                      {v ? (
                        <>
                          <strong>{percent(v)}</strong>
                          <span>
                            {v[0]} of {v[1]}
                          </span>
                        </>
                      ) : (
                        <span>
                          {r.name === "listings right as read"
                            ? "not measured"
                            : "none on these sheets"}
                        </span>
                      )}
                    </td>
                  );
                })}
              </tr>
            ))}
            <tr>
              <th scope="row">
                Tanks put on sites with none
                <span>on the answer-key sheets</span>
              </th>
              {years.map((y) => (
                <td key={y}>
                  <strong>{SCORES[y].tanks_on_sites_with_none}</strong>
                </td>
              ))}
            </tr>
            <tr>
              <th scope="row">
                Answer keys
                <span>sheets where every site was marked by hand</span>
              </th>
              {years.map((y) => (
                <td key={y}>
                  <strong>{SCORES[y].key_sheets}</strong>
                  <span>
                    {SCORES[y].keys_verified ? "checked by the author" : "drafts, not yet checked"}
                  </span>
                </td>
              ))}
            </tr>
          </tbody>
        </table>
      </div>

      <div className="table-scroll">
        <table className="scores">
          <caption>Placing the maps on today&apos;s streets</caption>
          <thead>
            <tr>
              <th scope="col">Measure</th>
              {years.map((y) => (
                <th scope="col" key={y}>
                  {y}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            <tr>
              <th scope="row">
                Typical error
                <span>street corners left out of the fit, then predicted</span>
              </th>
              {years.map((y) => (
                <td key={y}>
                  <strong>{SCORES[y].typical_median_m.toFixed(1)} m</strong>
                </td>
              ))}
            </tr>
            <tr>
              <th scope="row">
                Least precise sheet
                <span>its typical error</span>
              </th>
              {years.map((y) => (
                <td key={y}>
                  <strong>{SCORES[y].worst_median_m.toFixed(1)} m</strong>
                </td>
              ))}
            </tr>
            <tr>
              <th scope="row">Map sections placed</th>
              {years.map((y) => (
                <td key={y}>
                  <strong>{SCORES[y].panels}</strong>
                </td>
              ))}
            </tr>
          </tbody>
        </table>
      </div>

      <h2>What these numbers don&apos;t show</h2>
      <ul>
        <li>
          The listings on the site are better than &ldquo;right as read&rdquo;: wrong ones found in
          the scan check were fixed or removed. A check can still miss an error, so every listing
          links to the map image.
        </li>
        <li>
          &ldquo;Found&rdquo; can only be measured on the hand-marked sheets. Past uses the AI
          missed elsewhere don&apos;t show at all, so an empty search isn&apos;t proof of nothing.
        </li>
        {years
          .filter((y) => !SCORES[y].keys_verified)
          .map((y) => (
            <li key={y}>
              {y} is measured on {SCORES[y].key_sheets} draft answer keys (
              {rate(y, "sites found")?.[1] ?? 0} sites), too few for firm numbers
              {SCORES[y].checked_listings === 0 &&
                ", and only its doubtful listings were compared with the scan"}
              .
            </li>
          ))}
        <li>
          Placement errors are where a map&apos;s street corners land against today&apos;s. A
          building&apos;s own outline can be a few meters further off, more where streets moved.
        </li>
      </ul>
      <p className="small">
        How each number is measured: <code>scripts/check_accuracy.py</code> in the{" "}
        <a href="https://github.com/Hariswar/BlockHistory">project&apos;s code</a>. See also{" "}
        <Link href="/limits">what BlockHistory can&apos;t tell you</Link>.
      </p>
    </article>
  );
}
