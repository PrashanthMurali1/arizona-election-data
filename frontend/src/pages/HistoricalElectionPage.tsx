import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useResource } from "../api";
import {
  Availability,
  CandidateSummary,
  ErrorState,
  Loading,
} from "../components";
import type { Election, Results, Source } from "../types";

interface HistoricalArchive {
  election: Election;
  contests: {
    district: string;
    contest_id: string;
    results: Results;
    page: number | null;
    notes: string;
  }[];
  sources: Source[];
  multi_seat: boolean;
  map_available: boolean;
}

export default function HistoricalElectionPage({ id }: { id: string }) {
  const { data, error } = useResource<HistoricalArchive>(
    `/api/historical-elections/${id}`,
  );
  const catalog = useResource<Election[]>("/api/elections");
  const [district, setDistrict] = useState("");
  const navigate = useNavigate();
  if (error) return <ErrorState message={error} />;
  if (!data) return <Loading />;
  const active =
    data.contests.find((c) => c.district === district) ?? data.contests[0];
  const years = (catalog.data ?? [data.election])
    .filter((e) => e.office_id === data.election.office_id)
    .sort((a, b) => b.date.localeCompare(a.date));
  const source = data.sources[0];
  return (
    <>
      <div className="breadcrumbs">
        <Link to="/">Election catalog</Link>
        <span>/</span>
        <Link to={`/?office=${data.election.office_id}`}>
          {data.election.office}
        </Link>
        <span>/</span>
        <span>{data.election.year}</span>
      </div>
      <section className="election-heading page-heading">
        <div>
          <h1>
            {data.election.office} <span>{data.election.year}</span>
          </h1>
          <p>General election · {data.contests.length} district contests</p>
          <Availability status={data.election.status} />
        </div>
        <div className="year-picker">
          <label htmlFor="historical-year">Election year</label>
          <select
            id="historical-year"
            value={id}
            onChange={(e) => navigate(`/elections/${e.target.value}`)}
          >
            {years.map((e) => (
              <option value={e.id} key={e.id}>
                {e.year} {e.kind === "special" ? "Special" : "General"}
              </option>
            ))}
          </select>
        </div>
      </section>
      <section
        className="panel county-detail selection-panel historical-panel"
        aria-label="Historical district results"
      >
        <div className="panel-heading">
          <h2>District results</h2>
          <div className="year-picker">
            <label htmlFor="historical-district">District</label>
            <select
              id="historical-district"
              value={active?.district ?? ""}
              onChange={(e) => setDistrict(e.target.value)}
            >
              {data.contests.map((c) => (
                <option key={c.district} value={c.district}>
                  District {c.district}
                </option>
              ))}
            </select>
          </div>
        </div>
        <div className="historical-results-body">
          <p className="footnote">
            Historical district maps are unavailable. Each district has its own
            candidate results.
          </p>
          {data.multi_seat && (
            <p className="footnote">
              Historical legislative districts could elect multiple members.
              Shares below are percentages of candidate votes, not voters.
              Elected members are not inferred from first place.
            </p>
          )}
          {active ? (
            <div aria-live="polite" aria-atomic="true">
              <h3>District {active.district}</h3>
              <Availability status={active.results.status} />
              <CandidateSummary results={active.results} />
              <p className="footnote">{active.notes}</p>
              {source && active.page && (
                <a
                  href={`${source.url}#page=${active.page}`}
                  target="_blank"
                  rel="noreferrer"
                >
                  View official canvass · page {active.page}
                </a>
              )}
            </div>
          ) : (
            <p>No district results are available.</p>
          )}
        </div>
      </section>
      <section
        className="sources source-section"
        aria-label="Sources and coverage"
      >
        <h2>Sources &amp; coverage</h2>
        {data.sources.map((s) => (
          <p key={s.id}>
            <a href={s.url} target="_blank" rel="noreferrer">
              {s.title}
            </a>
            <br />
            <span className="footnote">{s.notes}</span>
          </p>
        ))}
        <p className="footnote">
          Unavailable figures remain N/A. Complete printed contest totals can be
          shown even where county figures have not been transcribed.
        </p>
      </section>
    </>
  );
}
