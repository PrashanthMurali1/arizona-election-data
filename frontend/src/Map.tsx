import { useId, useMemo } from "react";
import { geoArea, geoMercator, geoPath } from "d3-geo";
import type { Feature, Geometry } from "geojson";
import type { Geography, Results } from "./types";
import { partyClass } from "./results";
import { returnedRegistrationParty } from "./activity";
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
  registrationBreakdowns = {},
}: {
  geography: Geography;
  counties: Results[];
  selected: string | null;
  onSelect: (id: string) => void;
  mode?: "results" | "activity" | "unofficial" | "registration";
  unitKind?: "county" | "district";
  registrationBreakdowns?: Record<string, Record<string, number | null>>;
}) {
  const hatchId = `not-contested-${useId().replace(/:/g, "")}`;
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
    <div
      className={`map-wrap${mode === "registration" ? " registration-map" : ""}`}
    >
      <svg
        className="county-map"
        viewBox="0 0 480 490"
        role="group"
        aria-label={
          mode === "registration"
            ? "Arizona counties colored by party registration among returned early ballots. Select a county for participation details."
            : unitKind === "district"
              ? "Arizona congressional districts. Select a district to view results."
              : "Arizona counties. Select a county to view results."
        }
      >
        <defs>
          <pattern
            id={hatchId}
            width="6"
            height="6"
            patternUnits="userSpaceOnUse"
          >
            <rect width="6" height="6" fill="var(--map-quiet)" />
            <line
              x1="0"
              y1="6"
              x2="6"
              y2="0"
              stroke="var(--map-hatch)"
              strokeWidth="1"
            />
          </pattern>
        </defs>
        {features.map((f) => {
          const id = String(f.properties?.geoid);
          const row =
            mode === "activity" || mode === "registration"
              ? undefined
              : counties.find((c) => c.geoid === id);
          const registrationParty = returnedRegistrationParty(
            registrationBreakdowns[id],
          );
          const registrationDescription =
            registrationParty === "DEM"
              ? "Democratic registration is largest among returned ballots"
              : registrationParty === "REP"
                ? "Republican registration is largest among returned ballots"
                : "Other, tied or missing party-registration breakdown among returned ballots";
          const center = path.centroid(f);
          const inactive =
            unitKind === "district" && row?.status === "not_contested";
          return (
            <g key={id}>
              <path
                className={`county ${partyClass(mode === "registration" ? (registrationParty ?? undefined) : row?.winner?.party)} ${selected === id ? "selected" : ""}`}
                d={path(f) ?? ""}
                style={inactive ? { fill: `url(#${hatchId})` } : undefined}
                tabIndex={inactive ? -1 : 0}
                role="button"
                aria-label={
                  inactive
                    ? `${f.properties?.name}. Not contested in this election.`
                    : unitKind === "district"
                      ? `${f.properties?.name}, ${row?.winner?.name ?? "winner unavailable"}. View district results.`
                      : mode === "registration"
                        ? `${f.properties?.name} County. View early-voting activity. ${registrationDescription}.`
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
                    : mode === "registration"
                      ? `${registrationDescription}. Registration does not show candidate choices.`
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
              {mode === "registration"
                ? "Democratic registration"
                : "Democratic"}
            </span>
            <span>
              <i className="dot rep" />
              {mode === "registration"
                ? "Republican registration"
                : "Republican"}
            </span>
            {unitKind === "district" &&
              counties.some((c) => c.status === "not_contested") && (
                <span>
                  <svg
                    className="legend-hatch"
                    viewBox="0 0 12 12"
                    aria-hidden="true"
                  >
                    <rect width="12" height="12" fill={`url(#${hatchId})`} />
                  </svg>
                  Not contested
                </span>
              )}
            <span>
              <i className="dot other" />
              Other / tie / unavailable
            </span>
          </>
        )}
      </div>
      {mode === "registration" && (
        <>
          <p className="map-explanation">
            <strong>Registration is not candidate support.</strong> Colors do
            not show how anyone voted.
          </p>
          <details className="map-definition">
            <summary>How colors are assigned</summary>
            <p>
              Colors show the largest party-registration group among returned
              early ballots in each county. Other, tied and unavailable
              breakdowns use the neutral color. They do not show which
              candidates voters selected.
            </p>
          </details>
        </>
      )}
      <p className="map-note">
        {mode !== "registration" && (
          <>
            {mode === "activity"
              ? "All counties · neutral participation map"
              : mode === "unofficial"
                ? "Current reported leader · unofficial"
                : unitKind === "district"
                  ? "District winner · solid party colors"
                  : "County winner · solid party colors"}
            <br />
          </>
        )}
        U.S. Census Bureau · {geography.vintage} boundaries
        {mode === "registration" && (
          <>
            <br />
            Select a county on the map or in the table.
          </>
        )}
      </p>
    </div>
  );
}
