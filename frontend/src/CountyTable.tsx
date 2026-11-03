import Icon from "./Icon";
import { useMemo, useState } from "react";
import type { Results } from "./types";
import {
  number,
  percent,
  partyShare,
  partyClass,
  sortCounties,
  tableParties,
  type SortKey,
} from "./results";
export default function CountyTable({
  counties,
  selected,
  onSelect,
  provisional = false,
  unitKind = "county",
}: {
  counties: Results[];
  selected: string | null;
  onSelect: (id: string) => void;
  provisional?: boolean;
  unitKind?: "county" | "district";
}) {
  // Live midterm tables have no contest-votes column: start in name (district-number) order.
  const live = counties.some((c) => c.percent_reporting !== undefined);
  const [key, setKey] = useState<SortKey>(live ? "name" : "total_votes");
  const [direction, setDirection] = useState<"asc" | "desc">(
    live ? "asc" : "desc",
  );
  // Live midterm results: always Dem % and Rep %, no contest-votes column, and reporting %
  // in place of turnout
  // (civicAPI supplies no turnout); the reporting column appears only if any row has it.
  const showReporting = counties.some((c) => c.percent_reporting != null);
  const parties = live ? ["DEM", "REP"] : tableParties(counties);
  const columns: { key: SortKey; label: string }[] = [
    { key: "name", label: "County" },
    ...parties.map((p) => ({
      key: `party:${p}` as SortKey,
      label: `${p[0]}${p.slice(1).toLowerCase()} %`,
    })),
    { key: "winner", label: "Winner" },
    ...(live
      ? []
      : [{ key: "total_votes" as SortKey, label: "Contest votes" }]),
    ...(live
      ? showReporting
        ? [{ key: "reporting" as SortKey, label: "Reporting %" }]
        : []
      : [{ key: "turnout" as SortKey, label: "Turnout" }]),
  ];
  const rows = useMemo(
    () => sortCounties(counties, key, direction, live),
    [counties, key, direction, live],
  );
  function sort(k: SortKey) {
    if (k === key) setDirection((d) => (d === "desc" ? "asc" : "desc"));
    else {
      setKey(k);
      setDirection(k === "name" || k === "winner" ? "asc" : "desc");
    }
  }
  return (
    <>
      <p className="scroll-hint">
        Scroll horizontally for all metrics. Geographic names stay visible.
      </p>
      <div
        className="table-scroll scroll-region"
        role="region"
        aria-label="Scrollable election results"
        tabIndex={0}
      >
        <table className={`results-table${live ? " live" : ""}`}>
          <caption className="sr-only">
            {unitKind === "district"
              ? "District election results. Select a column heading to sort and a district name to view full results."
              : "County election results. Select a column heading to sort and a county name to view full results."}
          </caption>
          <thead>
            <tr>
              {columns.map((c) => (
                <th
                  key={c.key}
                  scope="col"
                  aria-sort={
                    key === c.key
                      ? direction === "asc"
                        ? "ascending"
                        : "descending"
                      : "none"
                  }
                >
                  <button onClick={() => sort(c.key)}>
                    {c.key === "name" && unitKind === "district"
                      ? "District"
                      : c.key === "winner" && provisional
                        ? "Current leader"
                        : c.label}{" "}
                    <span aria-hidden="true">
                      <Icon
                        name={
                          key === c.key
                            ? direction === "asc"
                              ? "up"
                              : "down"
                            : "sort"
                        }
                      />
                    </span>
                  </button>
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rows.map((r) => (
              <tr
                key={r.geoid}
                className={r.geoid === selected ? "active" : ""}
              >
                <th scope="row">
                  <button
                    aria-pressed={selected === r.geoid}
                    onClick={() => onSelect(r.geoid)}
                  >
                    {r.name}
                    <Icon name="arrow" />
                  </button>
                </th>
                {parties.map((p) => (
                  <td key={p} className={`${partyClass(p)}-text`}>
                    {percent(
                      partyShare(r, p) ??
                        // Live race with no votes yet: 0.00%, matching the candidate card.
                        (live &&
                        !r.total_votes &&
                        r.candidates.some((c) => c.party === p)
                          ? 0
                          : null),
                    )}
                  </td>
                ))}
                <td>
                  <span
                    className={`winner-label ${partyClass(r.winner?.party)}`}
                  >
                    {r.winner?.name.replace(/ \(Write-In\)/, "") ?? "N/A"}
                  </span>
                </td>
                {!live && <td>{number(r.total_votes)}</td>}
                {live ? (
                  showReporting && <td>{percent(r.percent_reporting)}</td>
                ) : (
                  <td title={r.turnout.definition}>
                    {percent(r.turnout.percent)}
                  </td>
                )}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </>
  );
}
