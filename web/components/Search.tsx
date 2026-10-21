"use client";

import { useEffect, useState } from "react";
import MapLegend from "./MapLegend";
import MapView, { type Coverage } from "./MapView";
import type { PublicFinding, PublicRecord } from "@/lib/present";

type Result = {
  query: string;
  point: { lat: number; lon: number; matched: string; source: "parcel" | "street" | "census" };
  radiusM: number;
  coveredBy: Coverage[];
  findings: PublicFinding[];
  records: PublicRecord[];
};

const EXAMPLES = ["7313 S Broadway", "6601 S Broadway", "7421 Pennsylvania Ave"];

// Count searches by outcome only; the address never leaves for analytics.
function track(outcome: string, sites = 0) {
  (window as { umami?: { track: (e: string, d: object) => void } }).umami?.track("search", {
    outcome,
    sites,
  });
}
const REPORT_URL = "https://github.com/Hariswar/BlockHistory/issues/new";

export default function Search() {
  const [query, setQuery] = useState("");
  const [result, setResult] = useState<Result | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [coverage, setCoverage] = useState<Coverage[]>([]);
  const [active, setActive] = useState<number | null>(null);
  const [year, setYear] = useState("1938");

  // A search can be linked: /?q=7313+S+Broadway
  useEffect(() => {
    const q = new URLSearchParams(window.location.search).get("q");
    if (q) run(q);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    fetch("/api/coverage")
      .then((r) => r.json())
      .then((d) => setCoverage(d.sheets))
      .catch(() => setCoverage([]));
  }, []);

  async function run(q: string) {
    setQuery(q);
    setLoading(true);
    setError(null);
    setActive(null);
    window.history.replaceState(null, "", `?q=${encodeURIComponent(q)}`);
    try {
      const res = await fetch(`/api/search?q=${encodeURIComponent(q)}`);
      const data = await res.json();
      if (!res.ok) {
        setResult(null);
        setError(data.error ?? "Something went wrong.");
        track(res.status === 404 ? "address not found" : "error");
      } else {
        setResult(data);
        const covered = data.coveredBy.length > 0;
        track(!covered ? "not covered" : data.findings.length ? "found" : "none", data.findings.length);
      }
    } catch {
      setError("Couldn't reach the server. Check your connection and try again.");
    } finally {
      setLoading(false);
    }
  }

  const years = [...new Set(coverage.map((c) => c.year))].sort();
  // What the selected map year shows: its sheets, its findings.
  const shown = result && {
    ...result,
    coveredBy: result.coveredBy.filter((s) => s.year === year),
    findings: result.findings.filter((f) => f.year === year),
  };

  return (
    <>
      <form
        className="search"
        role="search"
        onSubmit={(e) => {
          e.preventDefault();
          if (query.trim()) run(query.trim());
        }}
      >
        <label htmlFor="address" className="small" style={{ position: "absolute", left: -9999 }}>
          Street address
        </label>
        <input
          id="address"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Street address, e.g. 7313 S Broadway"
          autoComplete="street-address"
        />
        <button disabled={loading}>{loading ? "Looking…" : "Look up"}</button>
      </form>
      <p className="examples">
        Try:
        {EXAMPLES.map((ex) => (
          <button key={ex} type="button" onClick={() => run(ex)}>
            {ex}
          </button>
        ))}
      </p>
      {years.length > 1 && (
        <div className="years" role="group" aria-label="Map year">
          <span>Map year:</span>
          {years.map((y) => (
            <button
              key={y}
              type="button"
              aria-pressed={y === year}
              onClick={() => {
                setYear(y);
                setActive(null);
              }}
            >
              {y}
            </button>
          ))}
        </div>
      )}

      {error && (
        <div className="summary error" role="alert">
          <p>{error}</p>
        </div>
      )}

      <div className={`results${shown ? "" : " empty"}`}>
        <div className="map">
          <MapView
            coverage={coverage.filter((c) => c.year === year)}
            point={shown?.point ?? null}
            radiusM={shown?.radiusM ?? 100}
            findings={shown?.findings ?? []}
            active={active}
            onSelect={(id) => {
              setActive(id);
              document.getElementById(`f-${id}`)?.scrollIntoView({ behavior: "smooth", block: "nearest" });
            }}
          />
          <MapLegend searched={!!shown} />
        </div>
        {shown && (
          <div className="side">
            <Summary result={shown} year={year} />
            {shown.findings.length > 0 && (
              <ol className="cards">
                {shown.findings.map((f, i) => (
                  <FindingCard
                    key={f.id}
                    f={f}
                    n={i + 1}
                    active={active === f.id}
                    onFocus={() => setActive(f.id)}
                  />
                ))}
              </ol>
            )}
            <StateRecords result={shown} />
          </div>
        )}
        {!shown && (
          <p className="small">
            The outlined areas on the map are the parts of Carondelet processed so far. More are
            being added.
          </p>
        )}
      </div>
    </>
  );
}

function Summary({ result, year }: { result: Result; year: string }) {
  const { findings, coveredBy, radiusM, point } = result;
  // A sheet with two panels covers as two rows; name it once.
  const sheets = [...new Set(coveredBy.map((s) => `sheet ${s.sheetNumber}`))].join(", ");
  return (
    <section className="summary" aria-live="polite">
      {coveredBy.length === 0 ? (
        <>
          <h2>We haven&apos;t processed the maps for this address yet</h2>
          <p>
            So far BlockHistory covers Carondelet and Patch on the {year} map (the outlined area on
            the map). This says nothing either way about this property.
          </p>
        </>
      ) : findings.length === 0 ? (
        <>
          <h2>No flagged past uses within {radiusM} m on the {year} map</h2>
          <p>
            Nothing within {radiusM} m was a gas station, garage, dry cleaner, factory or similar
            use on the {year} map ({sheets}). That covers one year only: businesses that came and
            went at other times won&apos;t show here, and this is not a sign that the soil is clean.
          </p>
        </>
      ) : (
        <>
          <h2>
            {findings.length} past {findings.length === 1 ? "use" : "uses"} within {radiusM} m on the{" "}
            {year} map
          </h2>
          <p>
            These are kinds of businesses that sometimes left soil or groundwater contamination.
            They are historical uses, not test results. Source: {year} Sanborn map, {sheets}.
          </p>
        </>
      )}
      <p className="small">
        Address found as {point.matched}. {PLACED[point.source]}
      </p>
    </section>
  );
}

function FindingCard({
  f,
  n,
  active,
  onFocus,
}: {
  f: PublicFinding;
  n: number;
  active: boolean;
  onFocus: () => void;
}) {
  const issue = `${REPORT_URL}?${new URLSearchParams({
    title: `Finding ${f.id}: ${f.printedLabel} (${f.year} sheet ${f.sheetNumber})`,
    body: "What's wrong with this finding?\n\n",
  })}`;
  return (
    <li id={`f-${f.id}`} className={`card${active ? " active" : ""}`} onMouseEnter={onFocus}>
      <span className={`num ${f.relevance}`} aria-hidden>
        {n}
      </span>
      <div>
        <h3>{f.title}</h3>
        <div className="meta">
          Printed on the map: “{f.printedLabel}” · about {f.distanceM} m away (location ±
          {f.locationUncertaintyM} m)
        </div>
      </div>
      <div className="body">
        <div className="tags">
          <span className={`tag ${f.relevance}`}>
            {f.relevance === "high" ? "Often linked to contamination" : "Sometimes linked to contamination"}
          </span>
          {f.hasGasolineTanks && <span className="tag high">Gasoline tanks on the map</span>}
          {f.change && <span className="tag">{changeText(f.change)}</span>}
          {f.reviewStatus === "checked_ok" ? (
            <span className="tag checked">Checked against the map by a person</span>
          ) : f.reviewStatus === "partly_checked" ? (
            <span className="tag">Partly checked by a person</span>
          ) : (
            <span className="tag">Not yet checked by a person</span>
          )}
        </div>
        <p style={{ margin: "6px 0" }}>{f.explanation}</p>
        {f.records.map((r) => (
          <RecordNote key={r.id} r={r} lead="State record at about this spot" />
        ))}
        {f.alsoPrinted.length > 0 && (
          <p className="small" style={{ margin: "4px 0" }}>
            Same kind of use, also printed within 40 m:{" "}
            {f.alsoPrinted.map((l) => `“${l}”`).join(", ")}.
          </p>
        )}
        {f.cutOff && (
          <p className="small" style={{ margin: "4px 0" }}>
            The label is partly cut off or hard to read on the scan. Check the map image.
          </p>
        )}
        {f.reviewStatus !== "checked_ok" && (
          <p className="small" style={{ margin: "4px 0" }}>
            Read from the map scan by an AI model{f.readerConfidence ? ` (${f.readerConfidence} confidence)` : ""};
            it may be wrong. Compare with the map image.
          </p>
        )}
        <div className="source">
          <a href={f.sourceCrop} target="_blank" rel="noreferrer">
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img src={f.sourceCrop} alt={`Close-up of the ${f.year} map around “${f.printedLabel}”`} loading="lazy" />
          </a>
          <div className="links">
            <a href={f.sourcePage} target="_blank" rel="noreferrer">
              {f.year} map, {f.volume}, sheet {f.sheetNumber} (Library of Congress)
            </a>
            <a href={issue} target="_blank" rel="noreferrer">
              Something wrong? Report it
            </a>
          </div>
        </div>
      </div>
    </li>
  );
}

// How the address was put on the map, and how far off that can be (see lib/geocode.ts).
const PLACED = {
  parcel: "It was placed on its city parcel, usually within about 15–40 m of the building.",
  street:
    "It was placed along the street by the city's address ranges, so it can be 30–60 m off; check the map.",
  census:
    "It was placed by the US Census address lookup, which can be 30–80 m off; check the map.",
};

// Compared with the other map year at this spot; "not on the map" rather than "gone", since a
// missed read looks the same.
function changeText(c: NonNullable<PublicFinding["change"]>) {
  if (c.kind === "still") return `Also on the ${c.otherYear} map`;
  if (c.kind === "similar") return `Similar use nearby on the ${c.otherYear} map`;
  if (c.kind === "new") return `New since the ${c.otherYear} map`;
  return `Not on the ${c.otherYear} map`;
}

// Official state tank and cleanup records within the search circle. Records already shown on
// a card (same spot) aren't repeated; with none at all, say why that isn't reassurance.
function StateRecords({ result }: { result: Result }) {
  if (result.coveredBy.length === 0) return null;
  const onCards = new Set(result.findings.flatMap((f) => f.records.map((r) => r.id)));
  const others = result.records.filter((r) => !onCards.has(r.id));
  return (
    <section className="records" aria-label="State environmental records">
      <h3>State tank and cleanup records within {result.radiusM} m</h3>
      {result.records.length === 0 ? (
        <p className="small">
          The Missouri Department of Natural Resources has no tank or cleanup record within{" "}
          {result.radiusM} m. Tanks only had to be registered from 1986, so tanks from the 1930s–50s
          that were removed or abandoned earlier usually have no record. No record is not a sign
          that the ground is clean.
        </p>
      ) : (
        <>
          <p className="small">
            {result.records.length} {result.records.length === 1 ? "record" : "records"} from the
            Missouri Department of Natural Resources
            {onCards.size > 0 && others.length > 0 ? `; ${onCards.size} shown on the listings above` : ""}
            {onCards.size > 0 && others.length === 0 ? ", shown on the listings above" : ""}.
          </p>
          {others.length > 0 && (
            <ul className="record-list">
              {others.map((r) => (
                <li key={r.id}>
                  <RecordNote r={r} lead={`About ${r.distanceM} m away`} />
                </li>
              ))}
            </ul>
          )}
        </>
      )}
    </section>
  );
}

function RecordNote({ r, lead }: { r: PublicRecord; lead: string }) {
  const what = r.kind === "tank" ? "storage tank site" : "cleanup site";
  return (
    <div className={`record${r.release ? " release" : ""}`}>
      <strong>{lead}:</strong> {r.name}
      {r.address ? `, ${r.address}` : ""} ({what}). {r.statusPlain}.
      {r.contaminants ? ` Listed contaminants: ${r.contaminants.toLowerCase()}.` : ""}{" "}
      <a href={r.url} target="_blank" rel="noreferrer">
        State record ({r.source})
      </a>
    </div>
  );
}
