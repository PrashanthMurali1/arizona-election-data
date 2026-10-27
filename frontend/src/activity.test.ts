import { describe, expect, it } from "vitest";
import { sortActivity, activityValue, reportTime } from "./activity";
import type { Participation, ActivityMetric } from "./types";
function row(name: string, value: number | null): Participation {
  return {
    geoid: name,
    name,
    metrics: [{ key: "ballots_received", value } as ActivityMetric],
  };
}
describe("current-election activity", () => {
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
