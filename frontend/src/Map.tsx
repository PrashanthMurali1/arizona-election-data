import { useMemo } from "react";
import { geoArea, geoMercator, geoPath } from "d3-geo";
import type { Feature, Geometry } from "geojson";
import type { Geography, Results } from "./types";
import { partyClass } from "./results";
function rewind(feature: Feature): Feature {
  if (geoArea(feature) <= 2 * Math.PI) return feature;
  const geometry = feature.geometry;
  let reversed: Geometry = geometry;
  if (geometry.type === "Polygon")
    reversed = {
      ...geometry,
      coordinates: geometry.coordinates.map((r) => [...r].reverse()),
    };
  if (geometry.type === "MultiPolygon")
    reversed = {
      ...geometry,
      coordinates: geometry.coordinates.map((p) =>
        p.map((r) => [...r].reverse()),
      ),
    };
  return { ...feature, geometry: reversed };
}
export default function CountyMap({
  geography,
  counties,
  selected,
  onSelect,
  mode = "results",
  unitKind = "county",
}: {
  geography: Geography;
  counties: Results[];
  selected: string | null;
  onSelect: (id: string) => void;
  mode?: "results" | "activity" | "unofficial";
  unitKind?: "county" | "district";
}) {
  const features = useMemo(() => geography.features.map(rewind), [geography]);
  const projection = useMemo(
    () =>
      geoMercator().fitExtent(
        [
          [20, 16],
          [460, 470],
        ],
        { type: "FeatureCollection", features },
      ),
    [features],
  );
  const path = geoPath(projection);
  return (
    <div className="map-wrap">
      <svg
        className="county-map"
        viewBox="0 0 480 490"
        role="group"
        aria-label={
          unitKind === "district"
            ? "Arizona congressional districts. Select a district to view results."
            : "Arizona counties. Select a county to view results."
        }
      >
        {features.map((f) => {
          const id = String(f.properties?.geoid);
          const row =
            mode === "activity"
              ? undefined
              : counties.find((c) => c.geoid === id);
          const center = path.centroid(f);
          const inactive =
            unitKind === "district" && row?.status === "not_contested";
          return (
            <g key={id}>
              <path
                className={`county ${partyClass(row?.winner?.party)} ${selected === id ? "selected" : ""}`}
                d={path(f) ?? ""}
                tabIndex={inactive ? -1 : 0}
                role="button"
                aria-label={
                  inactive
                    ? `${f.properties?.name}. Not contested in this election.`
                    : unitKind === "district"
                      ? `${f.properties?.name}, ${row?.winner?.name ?? "winner unavailable"}. View district results.`
                      : mode === "activity"
                        ? `${f.properties?.name} County. View early-voting activity.`
                        : `${f.properties?.name} County, ${row?.winner?.name ?? "winner unavailable"}. View county results.`
                }
                aria-pressed={selected === id}
                aria-disabled={inactive || undefined}
                onClick={() => {
                  if (!inactive) onSelect(id);
                }}
                onKeyDown={(e) => {
                  if (e.key === "Enter" || e.key === " ") {
                    e.preventDefault();
                    if (!inactive) onSelect(id);
                  }
                }}
              >
                <title>
                  {f.properties?.name}:{" "}
                  {inactive
                    ? "Not contested"
                    : mode === "activity"
                      ? "Participation reports"
                      : (row?.winner?.name ??
                        (mode === "unofficial"
                          ? "No reported leader"
                          : "No verified winner"))}
                </title>
              </path>
              <text
                x={center[0]}
                y={center[1]}
                className="map-label"
                aria-hidden="true"
              >
                {f.properties?.label ?? f.properties?.name}
              </text>
            </g>
          );
        })}
      </svg>
      <div className="legend">
        {mode === "activity" ? (
          <span>
            <i className="dot other" />
            Participation only · candidate results not released
          </span>
        ) : (
          <>
            <span>
              <i className="dot dem" />
              Democratic
            </span>
            <span>
              <i className="dot rep" />
              Republican
            </span>
            <span>
              <i className="dot other" />
              Other / tie / unavailable
            </span>
          </>
        )}
      </div>
      <p className="map-note">
        {mode === "activity"
          ? "All counties · neutral participation map"
          : mode === "unofficial"
            ? "Current reported leader · unofficial"
            : unitKind === "district"
              ? "District winner · solid party colors"
              : "County winner · solid party colors"}
        <br />
        U.S. Census Bureau · {geography.vintage} boundaries
      </p>
    </div>
  );
}
