"""Georeference sheets and give every finding a latitude/longitude.

    # 1. Control points: street intersections, read off the 50% sheet image, located today
    #    from OpenStreetMap. Writes config/georef/<area>/<edition>/<sheet>.points (QGIS format).
    python scripts/georef_sheet.py gcps carondelet 1938 56 "Robert Av/Minnesota Av@467,325" ...

    # 2. Fit and check: leave-one-out error per point, in meters.
    python scripts/georef_sheet.py fit carondelet 1938 56

    # 3. Findings -> lat/lon: data/results/<area>/<edition>/<sheet>.geojson
    python scripts/georef_sheet.py locate carondelet 1938 56 [--no-ocr]

    # 4. Check against the Census geocoder on hand-labeled addresses.
    python scripts/georef_sheet.py validate carondelet 1938 56

A sheet needs at least 3 control points; 6+ spread over the sheet is better.
A sheet with two separately drawn panels gets one set of points per panel:

    python scripts/georef_sheet.py gcps carondelet 1938 74 --outline 0,0,2230,3898 "..."
    python scripts/georef_sheet.py gcps carondelet 1938 74 --panel inset --outline 2230,0,3201,3898 "..."

--outline takes a box (x0,y0,x1,y1) or a polygon ("x,y x,y x,y ..."), in sheet pixels.
--similarity fits shift + scale + rotation only, for a panel whose points are all on one
street (see blockhistory/georef/transform.py).
"""

import argparse
import json
from pathlib import Path

from blockhistory.georef import osm
from blockhistory.georef.geocode import geocode
from blockhistory.georef.locate import sheet_point
from blockhistory.georef.transform import (
    GCP,
    Affine,
    distance_m,
    in_outline,
    leave_one_out,
    parse_outline,
    read_model,
    read_outline,
    read_points,
    write_points,
)
from blockhistory.map_reader import tanks
from blockhistory.map_reader.scoring import match_sheet
from blockhistory.map_reader.sheets import merge_sheet

ROOT = Path(__file__).resolve().parent.parent


def sheet_dir(area: str, edition: str, n: int) -> Path:
    return next((ROOT / "data" / "tiles" / area / edition).glob(f"*-{n:04d}"))


def points_path(area: str, edition: str, sheet_id: str, panel: str | None = None) -> Path:
    name = f"{sheet_id}.{panel}" if panel else sheet_id
    return ROOT / "config" / "georef" / area / edition / f"{name}.points"


def panel_files(area: str, edition: str, sheet_id: str) -> list[Path]:
    """The sheet's .points files: the main one plus any <sheet>.<panel>.points."""
    folder = ROOT / "config" / "georef" / area / edition
    return sorted(folder.glob(f"{sheet_id}.points")) + sorted(folder.glob(f"{sheet_id}.*.points"))


def panel_id(path: Path) -> str:
    """04858_12_1938-0074 for the main panel, 04858_12_1938-0074.inset for another."""
    return path.name.removesuffix(".points")


ROBUST_M = 12.0  # a corner this close to the consensus placement agrees with it


def _robust(cands: list[tuple[str, float, float, list]], scale_ft: float | None) -> list[GCP]:
    """Choose one today-location per corner by consensus, and drop corners that agree with
    nothing. `cands` is (name, px, py, [(lat, lon), ...]) with every OSM match for each
    corner (0, 1 or several). Every pair of matches from two corners fixes a similarity
    placement; the one most other corners land within ROBUST_M of wins (scale must be
    within 10% of scale_ft when given). Prints what it set aside."""
    flat = [(i, px, py, hit) for i, (_, px, py, hits) in enumerate(cands) for hit in hits]
    best: list[GCP] = []
    for j in range(len(flat)):
        for k in range(j + 1, len(flat)):
            if flat[j][0] == flat[k][0]:
                continue
            pair = [GCP(f[1], f[2], f[3][0], f[3][1], "") for f in (flat[j], flat[k])]
            if (pair[0].px, pair[0].py) == (pair[1].px, pair[1].py):
                continue
            t = Affine(pair, "similarity")
            if scale_ft and abs(t.meters_per_pixel() * 3.281 / scale_ft - 1) > 0.10:
                continue
            chosen = []
            for name, px, py, hits in cands:
                lat, lon = t.to_latlon(px, py)
                near = min(hits, key=lambda h: distance_m((lat, lon), h), default=None)
                if near and distance_m((lat, lon), near) <= ROBUST_M:
                    chosen.append(GCP(px, py, near[0], near[1], name))
            if len(chosen) > len(best):
                best = chosen
    kept = {g.name for g in best}
    for name, _, _, hits in cands:
        if name not in kept:
            why = "no match today" if not hits else "disagrees with the other corners"
            print(f"  set aside: {name} ({why})")
    return best


def known_points(area: str) -> dict[frozenset, tuple[float, float]]:
    """config/georef/<area>/known_points.txt: corners gone from today's map, measured on an
    older placed map. Keyed by the two normalized street names."""
    path = ROOT / "config" / "georef" / area / "known_points.txt"
    out = {}
    if path.exists():
        for line in path.read_text().splitlines():
            line = line.split("#")[0].strip()
            if "=" not in line:
                continue
            names, ll = line.split("=")
            a, b = (osm.norm_street(n) for n in names.split("&"))
            out[frozenset((a, b))] = tuple(float(v) for v in ll.split(","))
    return out


def _lookup(a: str, b: str, known: dict) -> list[tuple[float, float]]:
    # A curated known point wins: today's street of that name may be a different street.
    if pt := known.get(frozenset((osm.norm_street(a), osm.norm_street(b)))):
        return [pt]
    return osm.intersection(a, b)


def cmd_gcps(args) -> None:
    sid = sheet_dir(args.area, args.edition, args.sheet).name
    known = known_points(args.area)
    gcps = []
    if args.robust:
        cands = []
        for spec in args.points:
            streets, xy = spec.split("@")
            a, b = streets.split("/")
            px, py = (float(v) for v in xy.split(","))
            cands.append((f"{a} & {b}", px, py, _lookup(a, b, known)))
        gcps = _robust(cands, args.scale_ft)
    for spec in [] if args.robust else args.points:
        streets, xy = spec.split("@")
        a, b = streets.split("/")
        px, py = (float(v) for v in xy.split(","))
        hits = _lookup(a, b, known)
        if len(hits) != 1:
            msg = f"{a} & {b}: {len(hits)} intersections in OpenStreetMap"
            # Streets renamed, closed or rerouted since the map was drawn (common for 1908).
            if args.skip_missing:
                print(f"  skipped: {msg}")
                continue
            raise SystemExit(f"{msg}; pick another (or pass --skip-missing)")
        (lat, lon) = hits[0]
        gcps.append(GCP(px, py, lat, lon, f"{a} & {b}"))
    path = points_path(args.area, args.edition, sid, args.panel)
    outline = parse_outline(args.outline) if args.outline else None
    model = "similarity" if args.similarity else "affine"
    if path.exists():  # re-measuring points keeps the panel's outline and model
        outline = outline or read_outline(path)
        model = "similarity" if args.similarity else read_model(path)
    write_points(path, gcps, outline, model)
    print(f"{len(gcps)} points -> {path.relative_to(ROOT)}")
    report(gcps, model)


def report(gcps: list[GCP], model: str = "affine") -> Affine:
    t = Affine(gcps, model)
    print(f"scale {t.meters_per_pixel() * 3.281:.3f} ft/px ({model})")
    loo = leave_one_out(gcps, model)
    for g, err in zip([g for g in gcps if g.enabled], loo):
        flag = "  <- check this point" if err > 8 else ""
        print(
            f"  {g.name or f'({g.px:.0f},{g.py:.0f})':34} fit {t.error_m(g):5.1f} m   left out {err:5.1f} m{flag}"
        )
    print(f"median left-out error {sorted(loo)[len(loo) // 2]:.1f} m, worst {max(loo):.1f} m")
    return t


def load_panels(area: str, edition: str, sheet_id: str) -> list[tuple[str, list | None, Affine]]:
    """(panel id, pixel outline or None, transform) for each panel; outlined panels first."""
    files = panel_files(area, edition, sheet_id)
    if not files:
        path = points_path(area, edition, sheet_id)
        raise SystemExit(f"{sheet_id}: no control points yet ({path.relative_to(ROOT)})")
    panels = [(panel_id(p), read_outline(p), Affine(read_points(p), read_model(p))) for p in files]
    return sorted(panels, key=lambda p: p[1] is None)


def located_findings(area: str, edition: str, n: int, use_ocr: bool) -> tuple[str, list[dict]]:
    """Merged findings with lat/lon; each carries its "panel". Findings outside every panel
    (in a margin, or in a panel not georeferenced yet) are left out."""
    tile_dir = sheet_dir(area, edition, n)
    panels = load_panels(area, edition, tile_dir.name)
    merged = merge_sheet(tile_dir)
    tanks.apply(merged["findings"], tile_dir)
    located = []
    for f in merged["findings"]:
        p = sheet_point(f, tile_dir, use_ocr=use_ocr)
        panel = next((pl for pl in panels if in_outline(pl[1], p["px"], p["py"])), None)
        if panel is None:
            continue
        pid, _, t = panel
        f["panel"] = pid
        f["lat"], f["lon"] = (round(v, 7) for v in t.to_latlon(p["px"], p["py"]))
        f["sheet_px"] = [round(p["px"]), round(p["py"])]
        f["location_method"] = p["method"]
        f["uncertainty_m"] = round(p["uncertainty_px"] * t.meters_per_pixel())
        located.append(f)
    return tile_dir.name, located


def cmd_fit(args) -> None:
    sid = sheet_dir(args.area, args.edition, args.sheet).name
    for path in panel_files(args.area, args.edition, sid):
        print(f"{panel_id(path)}  outline {read_outline(path) or 'whole sheet'}")
        report(read_points(path), read_model(path))


def cmd_locate(args) -> None:
    for n in args.sheets:
        sid, findings = located_findings(args.area, args.edition, n, not args.no_ocr)
        features = [
            {
                "type": "Feature",
                "geometry": {"type": "Point", "coordinates": [f["lon"], f["lat"]]},
                "properties": {
                    k: f.get(k)
                    for k in (
                        "label", "use", "street_number", "relevance", "gasoline_tank_count",
                        "confidence", "location_method", "uncertainty_m", "tiles", "source",
                    )
                } | {"sheet": f["panel"]},
            }
            for f in findings
        ]  # fmt: skip
        out = ROOT / "data" / "results" / args.area / args.edition / f"{sid}.geojson"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps({"type": "FeatureCollection", "features": features}, indent=1))
        methods = {}
        for f in findings:
            methods[f["location_method"]] = methods.get(f["location_method"], 0) + 1
        print(f"{sid}: {len(findings)} findings -> {out.relative_to(ROOT)}  {methods}")


def cmd_validate(args) -> None:
    """Distance from each located finding to the Census position of its hand-labeled address."""
    rows = []
    for n in args.sheets:
        sid, findings = located_findings(args.area, args.edition, n, not args.no_ocr)
        hand = json.loads((ROOT / "evals" / "labels" / f"{sid}.json").read_text())["buildings"]
        match = match_sheet(findings, hand)
        seen = set()
        for f, i in zip(findings, match):
            if i is None or i in seen:
                continue
            h = hand[i]
            if not (h.get("street_number") and h.get("street_name")):
                continue
            seen.add(i)
            num = h["street_number"].split("-")[0].strip("() ").split()[0]
            pos = geocode(f"{num} {h['street_name']}, St. Louis, MO")
            if pos is None:
                print(
                    f"  {sid[-4:]} {h['label'][:30]:30} {num} {h['street_name']}: no Census match"
                )
                continue
            d = distance_m((f["lat"], f["lon"]), pos)
            rows.append(d)
            print(
                f"  {sid[-4:]} {h['label'][:30]:30} {num:>5} {h['street_name']:16} "
                f"{d:6.0f} m  ({f['location_method']}, +-{f['uncertainty_m']} m)"
            )
    if rows:
        rows.sort()
        print(
            f"{len(rows)} sites: median {rows[len(rows) // 2]:.0f} m, 80% within {rows[int(0.8 * (len(rows) - 1))]:.0f} m, worst {rows[-1]:.0f} m"
        )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="cmd", required=True)
    g = sub.add_parser("gcps")
    g.add_argument("area"), g.add_argument("edition"), g.add_argument("sheet", type=int)
    g.add_argument("points", nargs="+", help='"Street A/Street B@x,y" on the 50%% sheet image')
    g.add_argument("--panel", help="name of a second panel on the sheet, e.g. inset")
    g.add_argument("--outline", help='the panel in sheet pixels: "x0,y0,x1,y1" or "x,y x,y ..."')
    g.add_argument("--similarity", action="store_true", help="no shear: for points on one street")
    g.add_argument(
        "--robust",
        action="store_true",
        help="pick among repeated matches and set aside corners that disagree (streets changed)",
    )
    g.add_argument("--scale-ft", type=float, help="with --robust: expected ft per pixel")
    g.add_argument(
        "--skip-missing",
        action="store_true",
        help="drop corners whose streets no longer meet (or meet twice) today",
    )
    f = sub.add_parser("fit")
    f.add_argument("area"), f.add_argument("edition"), f.add_argument("sheet", type=int)
    for name in ("locate", "validate"):
        p = sub.add_parser(name)
        (
            p.add_argument("area"),
            p.add_argument("edition"),
            p.add_argument("sheets", nargs="+", type=int),
        )
        p.add_argument("--no-ocr", action="store_true", help="skip Tesseract word boxes")
    args = parser.parse_args()
    {"gcps": cmd_gcps, "fit": cmd_fit, "locate": cmd_locate, "validate": cmd_validate}[args.cmd](
        args
    )


if __name__ == "__main__":
    main()
