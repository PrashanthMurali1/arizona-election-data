import { beforeEach, describe, expect, it, vi } from "vitest";
import type { Activity, Geography } from "./types";

let cache: typeof import("./earlyVotingCache");
beforeEach(async () => {
  vi.resetModules();
  cache = await import("./earlyVotingCache");
});
const geo = (boundary: string): Geography => ({
  type: "FeatureCollection",
  boundary_id: boundary,
  vintage: 2022,
  features: [],
});
function activity(at: number): Activity {
  const metric = {
    key: "ballots_received",
    value: 0,
    stale: false,
    retrieved_at: new Date(at).toISOString(),
  };
  return {
    revision: "retained",
    stale: false,
    failures: [],
    statewide: { geoid: "04", metrics: [metric] },
    counties: [{ geoid: "04019", metrics: [metric] }],
    releases: [
      { stale: false, error: null, retrieved_at: new Date(at).toISOString() },
    ],
  } as unknown as Activity;
}
describe("bounded session cache", () => {
  it("reuses activity and geography independently and expires them without extending source dates", () => {
    const data = activity(0);
    cache.saveActivity(data, 0);
    cache.saveGeography(geo("county"), 0);
    expect(cache.cachedActivity(cache.ACTIVITY_FRESH_MS)!.data).toBe(data);
    expect(cache.cachedActivity(cache.ACTIVITY_MAX_MS)).toBeNull();
    expect(
      cache.cachedGeography("county", cache.ACTIVITY_MAX_MS),
    ).not.toBeNull();
    expect(cache.cachedGeography("county", cache.GEOGRAPHY_MAX_MS)).toBeNull();
    expect(data.statewide.metrics[0].retrieved_at).toBe(
      new Date(0).toISOString(),
    );
  });
  it("stores only one boundary and rejects mismatched boundaries or a clock moving backwards", () => {
    cache.saveGeography(geo("old"), 100);
    cache.saveGeography(geo("new"), 100);
    expect(cache.cachedGeography("old", 101)).toBeNull();
    expect(cache.cachedGeography("new", 101)!.boundary_id).toBe("new");
    cache.saveActivity(activity(100), 100);
    expect(cache.cachedActivity(99)).toBeNull();
    expect(cache.cachedGeography("new", 99)).toBeNull();
  });
});
describe("time-dependent source status", () => {
  it("ages release and county flags even with an unchanged revision, preserving values and original timestamps", () => {
    const original = activity(0);
    expect(cache.currentStaleness(original, cache.SOURCE_STALE_MS).stale).toBe(
      false,
    );
    const aged = cache.currentStaleness(original, cache.SOURCE_STALE_MS + 1);
    expect(aged.stale).toBe(true);
    expect(aged.releases[0].stale).toBe(true);
    expect(aged.counties[0].metrics[0].stale).toBe(true);
    expect(aged.statewide.metrics[0].value).toBe(0);
    expect(aged.revision).toBe(original.revision);
    expect(original.stale).toBe(false);
    expect(original.counties[0].metrics[0].stale).toBe(false);
  });
  it("preserves server failures and treats malformed retrieval timestamps conservatively", () => {
    const original = activity(100);
    original.releases[0].error = "Retained failure";
    original.counties[0].metrics[0].retrieved_at = "invalid";
    expect(cache.currentStaleness(original, 101).stale).toBe(true);
    expect(
      cache.currentStaleness(original, 101).counties[0].metrics[0].stale,
    ).toBe(true);
  });
});
