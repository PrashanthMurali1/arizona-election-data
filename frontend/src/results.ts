import type { Results } from "./types";
export const number = (value: number | null | undefined) =>
  value == null ? "N/A" : value.toLocaleString("en-US");
export const percent = (value: number | null | undefined) =>
  value == null
    ? "N/A"
    : value > 0 && value < 0.01
      ? "<0.01%"
      : `${value.toFixed(2)}%`;
export function partyShare(r: Results, party: string): number | null {
  const candidates = r.candidates.filter((c) => c.party === party);
  return r.total_votes == null ||
    !r.total_votes ||
    !candidates.length ||
    candidates.some((c) => c.votes == null)
    ? null
    : (candidates.reduce((n, c) => n + c.votes!, 0) / r.total_votes) * 100;
}
export type SortKey =
  "name" | "DEM" | "REP" | "winner" | "total_votes" | "turnout";
export function sortCounties(
  rows: Results[],
  key: SortKey,
  direction: "asc" | "desc",
): Results[] {
  function value(r: Results): number | string | null {
    if (key === "DEM" || key === "REP") return partyShare(r, key);
    if (key === "turnout") return r.turnout.percent;
    if (key === "winner") return r.winner?.name ?? null;
    return r[key];
  }
  return [...rows].sort((a, b) => {
    const x = value(a),
      y = value(b);
    if (x == null) return y == null ? 0 : 1;
    if (y == null) return -1;
    const comparison =
      typeof x === "string" && typeof y === "string"
        ? x.localeCompare(y)
        : Number(x) - Number(y);
    return (
      comparison * (direction === "asc" ? 1 : -1) ||
      a.name.localeCompare(b.name)
    );
  });
}
export const partyClass = (party: string | undefined) =>
  party === "DEM" ? "dem" : party === "REP" ? "rep" : "other";
