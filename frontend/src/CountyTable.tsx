import { useMemo, useState } from "react";
import type { Results } from "./types";
import {
  number,
  percent,
  partyShare,
  partyClass,
  sortCounties,
  type SortKey,
} from "./results";
const columns: { key: SortKey; label: string }[] = [
  { key: "name", label: "County" },
  { key: "DEM", label: "Dem %" },
  { key: "REP", label: "Rep %" },
  { key: "winner", label: "Winner" },
  { key: "total_votes", label: "Contest votes" },
  { key: "turnout", label: "Turnout" },
];
export default function CountyTable({
  counties,
  selected,
  onSelect,
  provisional = false,
}: {
  counties: Results[];
  selected: string | null;
  onSelect: (id: string) => void;
  provisional?: boolean;
}) {
  const [key, setKey] = useState<SortKey>("total_votes");
  const [direction, setDirection] = useState<"asc" | "desc">("desc");
  const rows = useMemo(
    () => sortCounties(counties, key, direction),
    [counties, key, direction],
  );
  function sort(k: SortKey) {
    if (k === key) setDirection((d) => (d === "desc" ? "asc" : "desc"));
    else {
      setKey(k);
      setDirection(k === "name" || k === "winner" ? "asc" : "desc");
    }
  }
  return (
    <div className="table-scroll">
      <table>
        <caption className="sr-only">
          County election results. Select a column heading to sort and a county
          name to view full results.
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
                  {c.key === "winner" && provisional
                    ? "Current leader"
                    : c.label}{" "}
                  <span aria-hidden="true">
                    {key === c.key ? (direction === "asc" ? "↑" : "↓") : "↕"}
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
                  aria-pressed={selected === r.geoid}
                  onClick={() => onSelect(r.geoid)}
                >
                  {r.name}
                  <span aria-hidden="true">↗</span>
                </button>
              </th>
              <td className="dem-text">{percent(partyShare(r, "DEM"))}</td>
              <td className="rep-text">{percent(partyShare(r, "REP"))}</td>
              <td>
                <span className={`winner-label ${partyClass(r.winner?.party)}`}>
                  {r.winner?.name.replace(/ \(Write-In\)/, "") ?? "N/A"}
                </span>
              </td>
              <td>{number(r.total_votes)}</td>
              <td>{percent(r.turnout.percent)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
