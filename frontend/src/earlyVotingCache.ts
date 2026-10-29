import type { Activity, Geography, Participation } from "./types";

export const ACTIVITY_FRESH_MS = 5 * 60_000;
export const ACTIVITY_MAX_MS = 30 * 60_000;
export const GEOGRAPHY_MAX_MS = 24 * 60 * 60_000;
export const SOURCE_STALE_MS = 12 * 60 * 60_000;

// One activity response and one boundary, in memory only. Nothing is written to
// browser storage, HTTP caches, or disk. Reloading the document clears the cache.
let activityEntry: { data: Activity; checkedAt: number } | null = null;
let geographyEntry: { data: Geography; checkedAt: number } | null = null;

export function cachedActivity(now = Date.now()) {
  if (
    activityEntry &&
    (now < activityEntry.checkedAt ||
      now - activityEntry.checkedAt >= ACTIVITY_MAX_MS)
  )
    activityEntry = null;
  return activityEntry;
}
export function cachedGeography(boundary: string, now = Date.now()) {
  if (
    geographyEntry &&
    (now < geographyEntry.checkedAt ||
      now - geographyEntry.checkedAt >= GEOGRAPHY_MAX_MS)
  )
    geographyEntry = null;
  return geographyEntry?.data.boundary_id === boundary
    ? geographyEntry.data
    : null;
}
export function saveActivity(data: Activity, now = Date.now()) {
  activityEntry = { data, checkedAt: now };
  return activityEntry;
}
export function saveGeography(data: Geography, now = Date.now()) {
  geographyEntry = { data, checkedAt: now };
}

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
