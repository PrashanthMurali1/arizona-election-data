import type { Activity, Participation } from "./types";

export const SOURCE_STALE_MS = 12 * 60 * 60_000;

// SSE deliberately excludes time-dependent staleness from its revision. Update
// display flags from original retrieval times, never from browser-cache age.
export function currentStaleness(data: Activity, now = Date.now()): Activity {
  const aged = (retrieved: string | null) =>
    retrieved !== null &&
    (!Number.isFinite(Date.parse(retrieved)) ||
      now - Date.parse(retrieved) > SOURCE_STALE_MS);
  const row = (value: Participation): Participation => ({
    ...value,
    metrics: value.metrics.map((metric) => ({
      ...metric,
      stale: metric.stale || aged(metric.retrieved_at),
    })),
  });
  const releases = data.releases.map((release) => ({
    ...release,
    stale:
      release.stale || Boolean(release.error) || aged(release.retrieved_at),
  }));
  return {
    ...data,
    releases,
    stale:
      data.stale ||
      data.failures.length > 0 ||
      releases.some((release) => release.stale),
    statewide: row(data.statewide),
    counties: data.counties.map(row),
  };
}
