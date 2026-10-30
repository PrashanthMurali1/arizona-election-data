import Icon from "./Icon";
import { useMemo, useState } from "react";
import type { Participation } from "./types";
import { activityValue, sortActivity, activityColumns } from "./activity";
import { number } from "./results";
export default function ActivityTable({
  counties,
  selected,
  onSelect,
}: {
  counties: Participation[];
  selected: string | null;
  onSelect: (id: string) => void;
}) {
  const [key, setKey] = useState("ballots_received");
  const [direction, setDirection] = useState<"asc" | "desc">("desc");
  const columns = activityColumns;
  const activeKey = key;
  const activeDirection = direction;
  const rows = useMemo(
    () => sortActivity(counties, activeKey, activeDirection),
    [counties, activeKey, activeDirection],
  );
  function sort(k: string) {
    setKey(k);
    setDirection(
      k === activeKey
        ? activeDirection === "desc"
          ? "asc"
          : "desc"
        : k === "name"
          ? "asc"
          : "desc",
    );
  }
  return (
    <>
      <p className="scroll-hint">
        Scroll horizontally for all metrics. Geographic names stay visible.
      </p>
      <div
        className="table-scroll scroll-region"
        role="region"
        aria-label="Scrollable participation reports"
        tabIndex={0}
      >
        <table className="activity-table early-table">
          <caption className="sr-only">
            General-election participation by county, not candidate votes. Sort
            columns and select county names for source definitions and reporting
            dates.
          </caption>
          <thead>
            <tr>
              {columns.map(([k, label]) => (
                <th
                  key={k}
                  scope="col"
                  data-metric={k}
                  aria-sort={
                    activeKey === k
                      ? activeDirection === "asc"
                        ? "ascending"
                        : "descending"
                      : "none"
                  }
                >
                  <button onClick={() => sort(k)}>
                    {label}{" "}
                    <span aria-hidden="true">
                      <Icon
                        name={
                          activeKey === k
                            ? activeDirection === "asc"
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
                    onClick={() => onSelect(r.geoid)}
                    aria-pressed={r.geoid === selected}
                  >
                    {r.name}
                    <Icon name="arrow" />
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
    </>
  );
}
