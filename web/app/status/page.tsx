import type { Metadata } from "next";
import { sheets } from "@/lib/data";
import { lookup } from "@/lib/lookup";
import { AREA } from "@/lib/site";

export const metadata: Metadata = {
  title: "Status · BlockHistory",
  description: "Whether BlockHistory's address search, map database and map images are working.",
};
export const dynamic = "force-dynamic";
// Results are reused for 5 minutes, so many visits don't each call the city address service.
const REUSE_MS = 5 * 60_000;

const PROBE = "6532 S Broadway";
const WEEKLY =
  "https://api.github.com/repos/Hariswar/BlockHistory/actions/workflows/weekly.yml/runs?per_page=1";

type Check = { name: string; ok: boolean; detail: string };

async function timed<T>(fn: () => Promise<T>): Promise<[T, number]> {
  const start = Date.now();
  const out = await fn();
  return [out, Date.now() - start];
}

async function searchChecks(): Promise<[Check[], string | undefined]> {
  const [{ status, body }, ms] = await timed(() => lookup(PROBE));
  const lookupOk = status !== 502 && status !== 404;
  const dbOk = status === 200;
  const findings = (body.findings ?? []) as { sourceCrop: string }[];
  return [
    [
      {
        name: "Address lookup",
        ok: lookupOk,
        detail: lookupOk ? "The city address service answers." : (body.error ?? `error ${status}`),
      },
      {
        name: "Search",
        ok: dbOk && findings.length > 0,
        detail: dbOk
          ? `A test search found ${findings.length} past uses in ${(ms / 1000).toFixed(1)} s.`
          : (body.error ?? `error ${status}`),
      },
    ],
    findings[0]?.sourceCrop,
  ];
}

async function mapCheck(): Promise<Check> {
  try {
    const all = await sheets();
    const missing = AREA.years.filter((y) => !all.some((s) => s.edition === y));
    return {
      name: "Map data",
      ok: missing.length === 0,
      detail: missing.length
        ? `No map sections loaded for ${missing.join(", ")}.`
        : `${all.length} map sections loaded for ${AREA.years.join(", ")}.`,
    };
  } catch {
    return { name: "Map data", ok: false, detail: "The map database didn't answer." };
  }
}

async function imageCheck(crop: string | undefined): Promise<Check> {
  const name = "Map images (Library of Congress)";
  if (!crop) return { name, ok: false, detail: "Not checked: the test search failed." };
  try {
    const res = await fetch(crop, { signal: AbortSignal.timeout(20_000) });
    const ok = res.ok && (res.headers.get("content-type") ?? "").startsWith("image/");
    return {
      name,
      ok,
      detail: ok ? "Map images load." : `The image server answered ${res.status}.`,
    };
  } catch {
    return { name, ok: false, detail: "The image server didn't answer." };
  }
}

async function weeklyCheck(): Promise<Check> {
  const name = "Weekly check";
  try {
    const res = await fetch(WEEKLY, {
      headers: { Accept: "application/vnd.github+json" },
      signal: AbortSignal.timeout(10_000),
    });
    const run = (await res.json()).workflow_runs?.[0];
    if (!run) return { name, ok: true, detail: "Not run yet." };
    const when = new Date(run.run_started_at).toLocaleDateString("en-US", {
      month: "long",
      day: "numeric",
      timeZone: "America/Chicago",
    });
    if (run.status !== "completed") return { name, ok: true, detail: `Running now (${when}).` };
    return {
      name,
      ok: run.conclusion === "success",
      detail:
        run.conclusion === "success"
          ? `Passed on ${when}: tests, and saved searches give the same answers.`
          : `Failed on ${when}; being looked into.`,
    };
  } catch {
    return { name, ok: false, detail: "Couldn't read the last weekly check." };
  }
}

async function runChecks(): Promise<Check[]> {
  const [[search, crop], map, weekly] = await Promise.all([
    searchChecks(),
    mapCheck(),
    weeklyCheck(),
  ]);
  return [...search, map, await imageCheck(crop), weekly];
}

let last: { at: number; checks: Promise<Check[]> } | undefined;

export default async function Status() {
  if (!last || Date.now() - last.at > REUSE_MS) last = { at: Date.now(), checks: runChecks() };
  const checks = await last.checks;
  const down = checks.filter((c) => !c.ok);
  const checkedAt = new Date(last.at).toLocaleString("en-US", {
    dateStyle: "medium",
    timeStyle: "short",
    timeZone: "America/Chicago",
  });
  return (
    <article className="prose">
      <h1>Status</h1>
      <p className={down.length ? "status-summary down" : "status-summary"}>
        {down.length
          ? `Something isn't working: ${down.map((c) => c.name.toLowerCase()).join(", ")}.`
          : "Everything is working."}
      </p>
      <ul className="status-list">
        {checks.map((c) => (
          <li key={c.name} className={c.ok ? "ok" : "down"}>
            <strong>
              <span aria-hidden="true">{c.ok ? "✓" : "✕"}</span> {c.name}
              <span className="visually-hidden">{c.ok ? ": working" : ": not working"}</span>
            </strong>
            <span>{c.detail}</span>
          </li>
        ))}
      </ul>
      <p className="small">
        Checked {checkedAt} (Central time), at most every 5 minutes. The weekly check runs the tests
        and compares saved searches with the live site; a failure opens an issue on{" "}
        <a href="https://github.com/Hariswar/BlockHistory/issues">GitHub</a>.
      </p>
    </article>
  );
}
