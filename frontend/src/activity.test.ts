import { describe, expect, it } from "vitest";
import { sortActivity, activityValue, reportTime, visibleActivityColumns, defaultActivitySort, returnedRegistrationParty } from "./activity";
import type { Participation, ActivityMetric } from "./types";
function row(name: string, value: number | null): Participation {
  return {
    geoid: name,
    name,
    metrics: [{ key: "ballots_received", value } as ActivityMetric],
  };
}
describe("current-election activity", () => {
  it("hides all-missing columns, keeps zero-valued columns, and selects a visible default sort", () => {
    const missing = [row("Unknown", null)];
    expect(visibleActivityColumns(missing).map(([key]) => key)).toEqual(["name"]);
    expect(defaultActivitySort(visibleActivityColumns(missing))).toBe("name");
    const partial = [...missing, row("Zero", 0)];
    expect(visibleActivityColumns(partial).map(([key]) => key)).toEqual(["name", "ballots_received"]);
    expect(defaultActivitySort(visibleActivityColumns(partial))).toBe("ballots_received");
    const requested = [{ geoid: "A", name: "A", metrics: [{key: "ballots_requested", value: 7} as ActivityMetric] }];
    expect(defaultActivitySort(visibleActivityColumns(requested))).toBe("ballots_requested");
  });
  it("colors only a unique Democratic or Republican maximum in a complete returned registration breakdown", () => {
    expect(returnedRegistrationParty({Democratic: 7, Republican: 3, Other: 2})).toBe("DEM");
    expect(returnedRegistrationParty({Democratic: 0, Republican: 1, Other: 0})).toBe("REP");
    expect(returnedRegistrationParty({Democratic: 7, Republican: 3, Other: 8})).toBeNull();
    expect(returnedRegistrationParty({Democratic: 7, Republican: 7, Other: 2})).toBeNull();
    expect(returnedRegistrationParty({Democratic: 0, Republican: 0, Other: 0})).toBeNull();
    expect(returnedRegistrationParty({Democratic: 7, Republican: 3, Other: null})).toBeNull();
    expect(returnedRegistrationParty({Democratic: 7, Republican: 3})).toBeNull();
    expect(returnedRegistrationParty(undefined)).toBeNull();
  });
  it("keeps missing values last in either sort direction and preserves genuine zero", () => {
    const rows = [row("Unknown", null), row("Zero", 0), row("Reported", 25)];
    expect(
      sortActivity(rows, "ballots_received", "desc").map((r) => r.name),
    ).toEqual(["Reported", "Zero", "Unknown"]);
    expect(
      sortActivity(rows, "ballots_received", "asc").map((r) => r.name),
    ).toEqual(["Zero", "Reported", "Unknown"]);
    expect(activityValue(rows[1], "ballots_received")).toBe(0);
    expect(activityValue(rows[0], "ballots_requested")).toBeNull();
    expect(rows[0].name).toBe("Unknown");
  });
  it("renders source datetimes in Phoenix and does not invent a clock time for dates", () => {
    expect(reportTime("2026-10-27T15:03:13+00:00")).toContain("8:03 AM");
    expect(reportTime("2026-10-26", "date")).toContain("date only");
    expect(reportTime("2026-10-26", "date")).not.toContain("AM");
    expect(reportTime(null)).toBe("Not supplied by source");
  });
});
