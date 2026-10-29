import { describe, expect, it } from "vitest";
import type { Activity } from "./types";
import { currentStaleness, SOURCE_STALE_MS } from "./earlyVotingStatus";

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
describe("time-dependent source status", () => {
  it("ages release and county flags even with an unchanged revision, preserving values and original timestamps", () => {
    const original = activity(0);
    expect(currentStaleness(original, SOURCE_STALE_MS).stale).toBe(false);
    const aged = currentStaleness(original, SOURCE_STALE_MS + 1);
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
    expect(currentStaleness(original, 101).stale).toBe(true);
    expect(currentStaleness(original, 101).counties[0].metrics[0].stale).toBe(
      true,
    );
  });
});
