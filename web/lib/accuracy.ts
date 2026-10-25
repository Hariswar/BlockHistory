// Accuracy scores accepted by scripts/check_accuracy.py --update (written to lib/accuracy.json).
import data from "./accuracy.json";
import { AREA } from "./site";

export type YearScores = {
  key_sheets: number;
  keys_verified: boolean;
  rates: Record<string, [number, number]>;
  tanks_on_sites_with_none: number;
  checked_listings: number;
  panels: number;
  typical_median_m: number;
  worst_median_m: number;
  usd_per_sheet: number;
};

export const CHECKED_ON: string = data.date;
export const SCORES =
  (data.areas as unknown as Record<string, Record<string, YearScores>>)[AREA.area] ?? {};

export function rate(year: string, name: string): [number, number] | undefined {
  return SCORES[year]?.rates[name];
}

export function percent([a, b]: [number, number]): string {
  return `${Math.round((100 * a) / b)}%`;
}
