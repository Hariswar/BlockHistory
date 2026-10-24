"""Place sheets on the map from the street lists in config/georef/<area>/<edition>/streets.txt.

    python scripts/place_sheets.py carondelet 1908              # every sheet in the list
    python scripts/place_sheets.py carondelet 1908 63 64        # some sheets
    python scripts/place_sheets.py carondelet 1908 --report     # fit of each saved sheet, no changes

For each sheet: fit the named streets' center lines (georef_preview.py lines), cross them to
get corners, match the corners to today's intersections with --robust (one match per corner by
consensus; corners that don't agree are set aside), and fit. Unless the line gives OPTS, both
the affine and the similarity fit are tried and the one with the lower median + worst/2
left-out error is kept (affine only with 5+ points). Writes the .points files (free: OpenStreetMap is cached, no API calls).

streets.txt, one sheet (or panel) per line:
    <sheet> [OPTS=<georef_sheet.py gcps options>] [SKIP=a/b|c/d] [THIN=8] | H:<street>@<y> V:<street>@<x> ...
H streets run across the sheet, V streets down it; "@<pos>/<from>-<to>" measures only between
from and to along the street. SKIP drops corners that aren't real crossings. THIN=8 bridges a
pipe line drawn down the middle of a street. Use today's street names.
"""

import argparse
import os
import re
import shlex
import subprocess
import sys
from pathlib import Path
from statistics import median

from georef_sheet import points_path, sheet_dir

from blockhistory.georef.transform import leave_one_out, read_model, read_points

ROOT = Path(__file__).resolve().parent.parent
PY = sys.executable
AFFINE_MIN = 5  # fewer points than this: similarity only
SCALE_FT = {"1908": 0.33}  # expected feet per pixel on the 50% image, for --robust


def _field(head: str, key: str) -> re.Match | None:
    return re.search(rf"{key}=(.*?)(?= OPTS=| SKIP=| THIN=|$)", head)


def parse(area: str, edition: str) -> list[dict]:
    path = ROOT / "config" / "georef" / area / edition / "streets.txt"
    out = []
    for line in path.read_text().splitlines():
        if not line.strip() or line.startswith("#"):
            continue
        head, streets = line.split(" | ", 1)
        opts, skip, thin = (_field(head, k) for k in ("OPTS", "SKIP", "THIN"))
        out.append(
            {
                "sheet": int(head.split()[0]),
                "opts": shlex.split(opts.group(1)) if opts else [],
                "skip": [s.strip() for s in skip.group(1).split("|")] if skip else [],
                "thin": thin.group(1).strip() if thin else "0",
                "streets": re.findall(r"[HV]:.+?@[0-9/-]+", streets),
            }
        )
    return out


def corners(area: str, edition: str, e: dict) -> list[str]:
    out = subprocess.run(
        [
            PY,
            str(ROOT / "scripts" / "georef_preview.py"),
            "lines",
            area,
            edition,
            str(e["sheet"]),
            *e["streets"],
        ],
        env=dict(os.environ, GEOREF_THIN=e["thin"]),
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    found = re.findall(r'"([^"]+)"', next((l for l in out.splitlines() if l.startswith('"')), ""))
    return [c for c in found if c.split("@")[0] not in e["skip"]]


def fit_report(path: Path) -> tuple[int, float, float]:
    g = read_points(path)
    loo = sorted(leave_one_out(g, read_model(path)))
    return len(g), median(loo), loo[-1]


def place(area: str, edition: str, e: dict) -> str:
    pts = corners(area, edition, e)
    panel = e["opts"][e["opts"].index("--panel") + 1] if "--panel" in e["opts"] else None
    sid = sheet_dir(area, edition, e["sheet"]).name
    path = points_path(area, edition, sid, panel)
    base = [
        PY,
        str(ROOT / "scripts" / "georef_sheet.py"),
        "gcps",
        area,
        edition,
        str(e["sheet"]),
        "--robust",
    ]
    if edition in SCALE_FT:
        base += ["--scale-ft", str(SCALE_FT[edition])]

    def run(extra: list[str]) -> tuple[float, str]:
        path.unlink(missing_ok=True)
        r = subprocess.run(
            base + e["opts"] + extra + pts, check=False, capture_output=True, text=True
        )
        if r.returncode or not path.exists():
            return float("inf"), (r.stdout + r.stderr).strip().splitlines()[-1]
        n, med, worst = fit_report(path)
        aside = len([l for l in r.stdout.splitlines() if "set aside" in l])
        # Affine needs spare points: with 4 nearly in line it can swing wildly.
        if "--similarity" not in extra + e["opts"] and n < AFFINE_MIN:
            return float("inf"), f"{n} points: too few for affine"
        return med + worst / 2, f"{n} points, median {med:.1f} m, worst {worst:.1f} m" + (
            f" ({aside} set aside)" if aside else ""
        )

    if "--similarity" in e["opts"]:
        return run([])[1]
    affine, similarity = run([]), run(["--similarity"])
    if affine[0] <= similarity[0]:
        return run([])[1] + " (affine)"
    return similarity[1] + " (similarity)"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("area")
    parser.add_argument("edition")
    parser.add_argument("sheets", nargs="*", type=int)
    parser.add_argument("--report", action="store_true", help="show saved fits, change nothing")
    args = parser.parse_args()
    if args.report:
        for path in sorted(
            (ROOT / "config" / "georef" / args.area / args.edition).glob("*.points")
        ):
            n, med, worst = fit_report(path)
            print(
                f"{path.stem.split('-')[-1]:12} {n:2} points  median {med:4.1f} m  worst {worst:4.1f} m"
            )
        return
    for e in parse(args.area, args.edition):
        if args.sheets and e["sheet"] not in args.sheets:
            continue
        label = f"{e['sheet']}" + (
            f" {e['opts'][e['opts'].index('--panel') + 1]}" if "--panel" in e["opts"] else ""
        )
        print(f"{label:10} {place(args.area, args.edition, e)}")


if __name__ == "__main__":
    main()
