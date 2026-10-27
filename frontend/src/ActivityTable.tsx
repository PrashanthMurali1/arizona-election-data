import { useMemo, useState } from "react";
import type { Participation } from "./types";
import { activityValue, sortActivity } from "./activity";
import { number } from "./results";
const columns = [
  ["name", "County"],
  ["registered_voters", "Active registered"],
  ["ballots_requested", "Requested"],
  ["ballots_issued", "Sent / issued"],
  ["ballots_received", "Returns"],
  ["ballots_accepted", "Accepted"],
  ["in_person_early", "In-person early"],
];
export default function ActivityTable({
  counties,
  selected,
  onSelect,
}: {
  counties: Participation[];
  selected: string | null;
  onSelect: (id: string) => void;
}) {
  const [key, setKey] = useState("registered_voters");
  const [direction, setDirection] = useState<"asc" | "desc">("desc");
  const rows = useMemo(
    () => sortActivity(counties, key, direction),
    [counties, key, direction],
  );
  function sort(k: string) {
    if (k === key) setDirection((d) => (d === "desc" ? "asc" : "desc"));
    else {
      setKey(k);
      setDirection(k === "name" ? "asc" : "desc");
    }
  }
  return (
    <div className="table-scroll">
      <table className="activity-table">
        <caption className="sr-only">
          General-election participation by county, not gubernatorial candidate
          votes. Sort columns and select county names for source definitions and
          reporting dates.
        </caption>
        <thead>
          <tr>
            {columns.map(([k, label]) => (
              <th
                key={k}
                scope="col"
                aria-sort={
                  key === k
                    ? direction === "asc"
                      ? "ascending"
                      : "descending"
                    : "none"
                }
              >
                <button onClick={() => sort(k)}>
                  {label}{" "}
                  <span aria-hidden="true">
                    {key === k ? (direction === "asc" ? "↑" : "↓") : "↕"}
                  </span>
                </button>
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((r) => (
            <tr key={r.geoid} className={r.geoid === selected ? "active" : ""}>
              <th scope="row">
                <button
                  onClick={() => onSelect(r.geoid)}
                  aria-pressed={r.geoid === selected}
                >
                  {r.name}
                  <span aria-hidden="true">↗</span>
                </button>
              </th>
              {columns.slice(1).map(([k]) => (
                <td key={k}>
                  {number(activityValue(r, k))}
                  {r.metrics.find((m) => m.key === k)?.completeness ===
                  "partial" ? (
                    <span title="Partial source coverage; select county for details">
                      {" "}
                      *
                    </span>
                  ) : null}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
