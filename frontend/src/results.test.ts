import { describe, it, expect } from "vitest";
import { sortCounties, partyShare, percent, number } from "./results";
import type { Results } from "./types";
function row(name: string, total: number | null): Results {
  return {
    geoid: name,
    name,
    total_votes: total,
    status: "verified",
    candidates: [],
    winner: null,
    turnout: {
      ballots_cast: null,
      registered_voters: null,
      percent: null,
      definition: "Unavailable",
      source_id: null,
    },
  };
}
describe("County table behavior", () => {
  it("sorts contest totals descending, keeps unavailable values last and leaves input intact", () => {
    const rows = [row("Small", 2), row("Unavailable", null), row("Large", 100)];
    expect(
      sortCounties(rows, "total_votes", "desc").map((r) => r.name),
    ).toEqual(["Large", "Small", "Unavailable"]);
    expect(rows[0].name).toBe("Small");
    expect(sortCounties(rows, "total_votes", "asc").map((r) => r.name)).toEqual(
      ["Small", "Large", "Unavailable"],
    );
  });
  it("sorts county names and preserves the selected GEOID across ordering", () => {
    const selected = "Apache";
    const rows = [row("Pima", 10), row("Apache", 20)];
    expect(sortCounties(rows, "name", "asc")[0].geoid).toBe(selected);
    expect(sortCounties(rows, "name", "desc")[1].geoid).toBe(selected);
  });
  it("keeps missing values distinct from zero", () => {
    expect(number(null)).toBe("N/A");
    expect(number(0)).toBe("0");
    expect(percent(null)).toBe("N/A");
    expect(percent(0)).toBe("0.00%");
    expect(percent(0.001)).toBe("<0.01%");
    expect(partyShare(row("Missing", null), "DEM")).toBeNull();
  });
});
