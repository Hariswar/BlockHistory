// The area this site covers and its map years, from lib/area.json (written by
// scripts/export_overlays.py from config/neighborhoods/<area>.json).
import area from "./area.json";

export const AREA = area;

/** "1908, 1938 and 1950" */
export function yearsText(years: string[] = area.years): string {
  return years.length < 2 ? years.join("") : `${years.slice(0, -1).join(", ")} and ${years.at(-1)}`;
}
