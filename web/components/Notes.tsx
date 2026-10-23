"use client";

// Neighbors' notes: approved memories shown under a search, and the two forms that send new
// ones to the review queue (app/api/notes). Nothing typed here appears on the site until it
// has been read and approved.
import { useRef, useState } from "react";
import type { PublicFinding } from "@/lib/present";

export type PublicNote = {
  id: number;
  text: string;
  decade: string | null;
  source: string | null;
  distanceM: number;
};

const DECADES = ["before 1940", "1940s", "1950s", "1960s", "1970s", "1980s", "1990s", "2000s or later", "not sure"];
const SOURCES: Record<string, string> = {
  lived: "I lived nearby",
  worked: "I worked there or nearby",
  family: "Family stories",
  other: "Other",
};
const KNEW: Record<string, string> = {
  lived: "who lived nearby",
  worked: "who worked there or nearby",
  family: "from family stories",
  other: "",
};

function track(kind: string) {
  (window as { umami?: { track: (e: string, d: object) => void } }).umami?.track("note", { kind });
}

// Sending, with the shared spam traps: a hidden field and the time the form was open.
function useSend(kind: "memory" | "correction") {
  const opened = useRef(Date.now());
  const [state, setState] = useState<"idle" | "sending" | "sent">("idle");
  const [error, setError] = useState<string | null>(null);
  async function send(fields: Record<string, unknown>, form: HTMLFormElement) {
    setState("sending");
    setError(null);
    try {
      const res = await fetch("/api/notes", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          kind,
          ...fields,
          website: (form.elements.namedItem("website") as HTMLInputElement | null)?.value ?? "",
          elapsedMs: Date.now() - opened.current,
        }),
      });
      const data = await res.json();
      if (!res.ok) {
        setError(data.error ?? "Your note couldn't be sent.");
        setState("idle");
        return;
      }
      setState("sent");
      track(kind);
    } catch {
      setError("Couldn't reach the server. Check your connection and try again.");
      setState("idle");
    }
  }
  return { state, error, send };
}

// Hidden from people (and screen readers); bots that fill every field give themselves away.
function Trap() {
  return (
    <input
      name="website"
      tabIndex={-1}
      autoComplete="off"
      aria-hidden
      style={{ position: "absolute", left: -9999, width: 1, height: 1 }}
    />
  );
}

const PRIVACY =
  "Please leave out names, phone numbers and other personal details. We read every note before anything is shown, and may shorten it.";

export function NeighborNotes({ notes }: { notes: PublicNote[] }) {
  if (!notes.length) return null;
  return (
    <section className="records notes" aria-label="What neighbors remember">
      <h3>Neighbors remember</h3>
      <p className="small">
        Shared by visitors and read before posting, but not checked against records.
      </p>
      <ul className="record-list">
        {notes.map((n) => (
          <li key={n.id} className="record">
            “{n.text}”
            <span className="small">
              {" "}
              · a neighbor{n.source && KNEW[n.source] ? ` ${KNEW[n.source]}` : ""}
              {n.decade && n.decade !== "not sure" ? `, about the ${n.decade}` : ""} · about {n.distanceM} m
              away
            </span>
          </li>
        ))}
      </ul>
    </section>
  );
}

export function MemoryForm({ point }: { point: { lat: number; lon: number } }) {
  const { state, error, send } = useSend("memory");
  const [text, setText] = useState("");
  const [decade, setDecade] = useState("");
  const [source, setSource] = useState("");
  if (state === "sent") {
    return (
      <section className="records notes" role="status">
        <h3>Thank you</h3>
        <p className="small">
          Your note is in the review queue. Once it has been read, it may appear here for others
          searching nearby.
        </p>
      </section>
    );
  }
  return (
    <details className="records notes">
      <summary>
        <h3>Remember what used to be here?</h3>
      </summary>
      <p className="small">
        The maps stop in 1950. If you remember a gas station, garage, dry cleaner, factory or
        dump on this block, especially from the 1950s to the 1980s, tell us. {PRIVACY}
      </p>
      <form
        className="note-form"
        onSubmit={(e) => {
          e.preventDefault();
          send({ text, decade, source, lat: point.lat, lon: point.lon }, e.currentTarget);
        }}
      >
        <Trap />
        <label>
          What was here?
          <textarea
            value={text}
            onChange={(e) => setText(e.target.value)}
            rows={3}
            maxLength={1000}
            required
            minLength={10}
            placeholder="e.g. A Sinclair station on the corner, with pumps out front"
          />
        </label>
        <div className="note-row">
          <label>
            Roughly when?
            <select value={decade} onChange={(e) => setDecade(e.target.value)} required>
              <option value="">Pick one</option>
              {DECADES.map((d) => (
                <option key={d} value={d}>
                  {d}
                </option>
              ))}
            </select>
          </label>
          <label>
            How do you know? <span className="small">(optional)</span>
            <select value={source} onChange={(e) => setSource(e.target.value)}>
              <option value="">Rather not say</option>
              {Object.entries(SOURCES).map(([v, l]) => (
                <option key={v} value={v}>
                  {l}
                </option>
              ))}
            </select>
          </label>
        </div>
        {error && (
          <p className="small note-error" role="alert">
            {error}
          </p>
        )}
        <button disabled={state === "sending"}>{state === "sending" ? "Sending…" : "Send"}</button>
      </form>
    </details>
  );
}

const PROBLEMS: Record<string, string> = {
  wrong_use: "The map says something else here",
  wrong_place: "It's in the wrong place",
  other: "Something else",
};

export function CorrectionForm({ f }: { f: PublicFinding }) {
  const { state, error, send } = useSend("correction");
  const [problem, setProblem] = useState("");
  const [text, setText] = useState("");
  if (state === "sent") {
    return (
      <p className="small" role="status">
        Thanks. We&apos;ll compare it with the map scan.
      </p>
    );
  }
  return (
    <details className="note-inline">
      <summary className="small">Something wrong with this listing?</summary>
      <form
        className="note-form"
        onSubmit={(e) => {
          e.preventDefault();
          send(
            { problem, text, lat: f.lat, lon: f.lon, year: f.year, sheetNumber: f.sheetNumber, label: f.printedLabel },
            e.currentTarget,
          );
        }}
      >
        <Trap />
        <fieldset>
          <legend className="small">What&apos;s wrong?</legend>
          {Object.entries(PROBLEMS).map(([v, l]) => (
            <label key={v} className="note-choice">
              <input type="radio" name="problem" value={v} checked={problem === v} onChange={() => setProblem(v)} required />
              {l}
            </label>
          ))}
        </fieldset>
        <label>
          Tell us more
          <textarea
            value={text}
            onChange={(e) => setText(e.target.value)}
            rows={2}
            maxLength={1000}
            required
            minLength={10}
            placeholder="e.g. The scan says LAUNDRY, not PAINT"
          />
        </label>
        <p className="small">{PRIVACY}</p>
        {error && (
          <p className="small note-error" role="alert">
            {error}
          </p>
        )}
        <button disabled={state === "sending"}>{state === "sending" ? "Sending…" : "Send"}</button>
      </form>
    </details>
  );
}
