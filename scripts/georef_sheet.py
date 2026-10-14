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
    leave_one_out,
    read_points,
    write_points,
)
from blockhistory.map_reader import tanks
from blockhistory.map_reader.scoring import match_sheet
from blockhistory.map_reader.sheets import merge_sheet

ROOT = Path(__file__).resolve().parent.parent


def sheet_dir(area: str, edition: str, n: int) -> Path:
    return next((ROOT / "data" / "tiles" / area / edition).glob(f"*-{n:04d}"))


def points_path(area: str, edition: str, sheet_id: str) -> Path:
    return ROOT / "config" / "georef" / area / edition / f"{sheet_id}.points"


def cmd_gcps(args) -> None:
    sid = sheet_dir(args.area, args.edition, args.sheet).name
    gcps = []
    for spec in args.points:
        streets, xy = spec.split("@")
        a, b = streets.split("/")
        px, py = (float(v) for v in xy.split(","))
        hits = osm.intersection(a, b)
        if len(hits) != 1:
            raise SystemExit(f"{a} & {b}: {len(hits)} intersections in OpenStreetMap; pick another")
        (lat, lon) = hits[0]
        gcps.append(GCP(px, py, lat, lon, f"{a} & {b}"))
    path = points_path(args.area, args.edition, sid)
    write_points(path, gcps)
    print(f"{len(gcps)} points -> {path.relative_to(ROOT)}")
    report(gcps)


def report(gcps: list[GCP]) -> Affine:
    t = Affine(gcps)
    print(f"scale {t.meters_per_pixel() * 3.281:.3f} ft/px")
    loo = leave_one_out(gcps)
    for g, err in zip([g for g in gcps if g.enabled], loo):
        flag = "  <- check this point" if err > 8 else ""
        print(
            f"  {g.name or f'({g.px:.0f},{g.py:.0f})':34} fit {t.error_m(g):5.1f} m   left out {err:5.1f} m{flag}"
        )
    print(f"median left-out error {sorted(loo)[len(loo) // 2]:.1f} m, worst {max(loo):.1f} m")
    return t


def load_transform(area: str, edition: str, sheet_id: str) -> Affine:
    path = points_path(area, edition, sheet_id)
    if not path.exists():
        raise SystemExit(f"{sheet_id}: no control points yet ({path.relative_to(ROOT)})")
    return Affine(read_points(path))


def located_findings(area: str, edition: str, n: int, use_ocr: bool) -> tuple[str, list[dict]]:
    tile_dir = sheet_dir(area, edition, n)
    t = load_transform(area, edition, tile_dir.name)
    merged = merge_sheet(tile_dir)
    tanks.apply(merged["findings"], tile_dir)
    mpp = t.meters_per_pixel()
    for f in merged["findings"]:
        p = sheet_point(f, tile_dir, use_ocr=use_ocr)
        f["lat"], f["lon"] = (round(v, 7) for v in t.to_latlon(p["px"], p["py"]))
        f["sheet_px"] = [round(p["px"]), round(p["py"])]
        f["location_method"] = p["method"]
        f["uncertainty_m"] = round(p["uncertainty_px"] * mpp)
    return tile_dir.name, merged["findings"]


def cmd_fit(args) -> None:
    sid = sheet_dir(args.area, args.edition, args.sheet).name
    report(read_points(points_path(args.area, args.edition, sid)))


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
                } | {"sheet": sid},
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
