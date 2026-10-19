"use client";

import { useEffect, useState } from "react";
import MapLegend from "./MapLegend";
import MapView, { type Coverage } from "./MapView";
import type { PublicFinding } from "@/lib/present";

type Result = {
  query: string;
  point: { lat: number; lon: number; matched: string };
  radiusM: number;
  coveredBy: Coverage[];
  findings: PublicFinding[];
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

      {error && (
        <div className="summary error" role="alert">
          <p>{error}</p>
        </div>
      )}

      <div className={`results${result ? "" : " empty"}`}>
        <div className="map">
          <MapView
            coverage={coverage}
            point={result?.point ?? null}
            radiusM={result?.radiusM ?? 100}
            findings={result?.findings ?? []}
            active={active}
            onSelect={(id) => {
              setActive(id);
              document.getElementById(`f-${id}`)?.scrollIntoView({ behavior: "smooth", block: "nearest" });
            }}
          />
          <MapLegend searched={!!result} />
        </div>
        {result && (
          <div className="side">
            <Summary result={result} />
            {result.findings.length > 0 && (
              <ol className="cards">
                {result.findings.map((f, i) => (
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
          </div>
        )}
        {!result && (
          <p className="small">
            The outlined areas on the map are the parts of Carondelet processed so far. More are
            being added.
          </p>
        )}
      </div>
    </>
  );
}

function Summary({ result }: { result: Result }) {
  const { findings, coveredBy, radiusM, point } = result;
  const years = [...new Set(coveredBy.map((s) => s.year))].join(" and ");
  // A sheet with two panels covers as two rows; name it once.
  const sheets = [...new Set(coveredBy.map((s) => `sheet ${s.sheetNumber}`))].join(", ");
  return (
    <section className="summary" aria-live="polite">
      {coveredBy.length === 0 ? (
        <>
          <h2>We haven&apos;t processed the maps for this address yet</h2>
          <p>
            So far BlockHistory covers part of Carondelet on the 1938 map (the outlined areas on
            the map). This says nothing either way about this property.
          </p>
        </>
      ) : findings.length === 0 ? (
        <>
          <h2>No flagged past uses within {radiusM} m on the {years} map</h2>
          <p>
            Nothing within {radiusM} m was a gas station, garage, dry cleaner, factory or similar
            use on the {years} map ({sheets}). That covers one year only: businesses that came and
            went at other times won&apos;t show here, and this is not a sign that the soil is clean.
          </p>
        </>
      ) : (
        <>
          <h2>
            {findings.length} past {findings.length === 1 ? "use" : "uses"} within {radiusM} m on the{" "}
            {years} map
          </h2>
          <p>
            These are kinds of businesses that sometimes left soil or groundwater contamination.
            They are historical uses, not test results. Source: {years} Sanborn map, {sheets}.
          </p>
        </>
      )}
      <p className="small">
        Address found as {point.matched}. Its position comes from the US Census and can be 30–80 m
        off, so check the map.
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
          {f.reviewStatus === "checked_ok" ? (
            <span className="tag checked">Checked against the map by a person</span>
          ) : f.reviewStatus === "partly_checked" ? (
            <span className="tag">Partly checked by a person</span>
          ) : (
            <span className="tag">Not yet checked by a person</span>
          )}
        </div>
        <p style={{ margin: "6px 0" }}>{f.explanation}</p>
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
