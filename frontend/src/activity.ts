import type { Participation } from "./types";
const metricColumns: [string, string][] = [
  ["name", "County"],
  ["registered_voters", "Active registered"],
  ["ballots_requested", "Requested"],
  ["ballots_issued", "Sent / issued"],
  ["ballots_received", "Returned"],
  ["ballots_accepted", "Accepted"],
  ["in_person_early", "In-person early"],
];

export function visibleActivityColumns(counties: Participation[]): [string, string][] {
  return metricColumns
    .filter(([key]) => key === "name" || counties.some((county) => activityValue(county, key) !== null))
    .map(([key, fallback]) => [
      key,
      counties.flatMap((county) => county.metrics)
        .find((metric) => metric.key === key && metric.source_id)?.label ?? fallback,
    ]);
}

export function defaultActivitySort(columns: [string, string][]): string {
  return columns.some(([key]) => key === "ballots_received")
    ? "ballots_received"
    : columns.find(([key]) => key !== "name")?.[0] ?? "name";
}

export function returnedRegistrationParty(
  breakdown: Record<string, number | null> | undefined,
): "DEM" | "REP" | null {
  if (!breakdown || ["Democratic", "Republican", "Other"].some((key) => typeof breakdown[key] !== "number"))
    return null;
  const entries = Object.entries(breakdown);
  if (entries.some(([, count]) => count == null || !Number.isFinite(count) || count < 0))
    return null;
  const highest = Math.max(...entries.map(([, count]) => count!));
  const largest = entries.filter(([, count]) => count === highest);
  if (largest.length !== 1) return null;
  return largest[0][0] === "Democratic" ? "DEM" : largest[0][0] === "Republican" ? "REP" : null;
}

export const activityValue = (row: Participation, key: string) =>
  row.metrics.find((m) => m.key === key)?.value ?? null;
export function reportTime(value: string | null, precision = "datetime") {
  if (!value) return "Not supplied by source";
  if (precision === "date")
    return `${new Date(`${value}T12:00:00-07:00`).toLocaleDateString("en-US", { timeZone: "America/Phoenix", month: "short", day: "numeric", year: "numeric" })} (date only)`;
  return new Date(value).toLocaleString("en-US", {
    timeZone: "America/Phoenix",
    month: "short",
    day: "numeric",
    year: "numeric",
    hour: "numeric",
    minute: "2-digit",
    timeZoneName: "short",
  });
}
export function sortActivity(
  rows: Participation[],
  key: string,
  direction: "asc" | "desc",
) {
  return [...rows].sort((a, b) => {
    const x = key === "name" ? a.name : activityValue(a, key),
      y = key === "name" ? b.name : activityValue(b, key);
    if (x == null) return y == null ? a.name.localeCompare(b.name) : 1;
    if (y == null) return -1;
    return (
      (typeof x === "string" && typeof y === "string"
        ? x.localeCompare(y)
        : Number(x) - Number(y)) * (direction === "asc" ? 1 : -1) ||
      a.name.localeCompare(b.name)
    );
  });
}
