import { Link } from "react-router-dom";
import type { Candidate, Results, Turnout } from "./types";
import { number, percent, partyClass } from "./results";
import Icon from "./Icon";
export function Availability({
  status,
  label,
}: {
  status: string;
  label?: string;
}) {
  return (
    <span
      className={`badge ${status === "verified" ? "verified" : status === "civicapi" ? "info" : "warn"}`}
    >
      <Icon
        name={
          status === "verified"
            ? "check"
            : status === "civicapi"
              ? "info"
              : "clock"
        }
      />
      {label ??
        (status === "verified"
          ? "Verified results"
          : status === "civicapi"
            ? "civicAPI report"
            : status === "pre_results"
              ? "Voting in progress"
              : status === "unofficial"
                ? "Unofficial results"
                : status === "reported"
                  ? "Official results"
                  : status === "secondary"
                    ? "Secondary-source results"
                    : "Incomplete")}
    </span>
  );
}
export function CandidateRow({
  candidate,
  compact = false,
  awaiting = false,
}: {
  candidate: Candidate;
  compact?: boolean;
  awaiting?: boolean;
}) {
  return (
    <div className={`candidate-row ${compact ? "compact" : ""}`}>
      <div className="candidate-info">
        <span className={`party-chip ${partyClass(candidate.party)}`}>
          {candidate.party}
        </span>
        <div>
          <strong>{candidate.name}</strong>
          <small>
            {candidate.party_name}
            {candidate.status !== "verified" &&
            candidate.status !== "source_checked"
              ? " · Unavailable"
              : ""}
          </small>
        </div>
        <div className="vote-value">
          <strong>
            {awaiting
              ? "Pending"
              : percent(candidate.votes == null ? null : candidate.percent)}
          </strong>
          <small>{number(candidate.votes)} votes</small>
        </div>
      </div>
      {awaiting || candidate.votes == null || candidate.percent == null ? (
        <small className="unavailable-share">
          {awaiting ? "Awaiting results" : "Share unavailable"}
        </small>
      ) : (
        <div className="vote-track" aria-hidden="true">
          <div
            className={partyClass(candidate.party)}
            style={{ width: `${candidate.percent}%` }}
          />
        </div>
      )}
    </div>
  );
}
export function CandidateSummary({ results }: { results: Results }) {
  const awaiting = results.status === "unofficial" && results.total_votes === 0;
  return (
    <div className="candidate-summary">
      {results.partial && (
        <p className="footnote">
          Shares use the reported candidate votes. Some source entries are not
          allocated to this county.
        </p>
      )}
      {results.candidates.length ? (
        results.candidates.map((c) => (
          <CandidateRow key={c.id} candidate={c} awaiting={awaiting} />
        ))
      ) : (
        <p className="empty">
          Candidate results have not been verified for this election.
        </p>
      )}
    </div>
  );
}
export function GeographyResults({
  results,
  title,
  onClose,
  unitKind = "county",
  contestNote,
}: {
  results: Results;
  title: string;
  onClose: () => void;
  unitKind?: "county" | "district";
  contestNote: React.ReactNode;
}) {
  const turnout = results.turnout;
  const cast =
    turnout.basis === "contest_votes"
      ? turnout.votes_cast
      : turnout.ballots_cast;
  const hasTurnout =
    turnout.percent != null &&
    Number.isFinite(turnout.percent) &&
    turnout.percent >= 0 &&
    turnout.percent <= 100 &&
    cast != null &&
    Number.isFinite(cast) &&
    cast >= 0 &&
    turnout.registered_voters != null &&
    Number.isFinite(turnout.registered_voters) &&
    turnout.registered_voters > 0;
  return (
    <>
      <div className="panel-heading">
        <h2>{title}</h2>
        <button
          className="close-button"
          onClick={onClose}
          aria-label={`Close ${unitKind} details`}
        >
          <Icon name="close" />
        </button>
      </div>
      <div className={`detail-grid${hasTurnout ? "" : " without-turnout"}`}>
        <div>
          <h3>All candidate results</h3>
          <CandidateSummary results={results} />
          {!hasTurnout && (
            <p className="footnote contest-note">{contestNote}</p>
          )}
        </div>
        {hasTurnout && (
          <div className="turnout-panel">
            <h3>Beyond the contest</h3>
            <TurnoutMetrics turnout={turnout} />
            <p className="footnote">{contestNote}</p>
          </div>
        )}
      </div>
    </>
  );
}
export function TurnoutMetrics({ turnout }: { turnout: Turnout }) {
  return (
    <>
      <div className="turnout-metrics">
        <div>
          <small>
            {turnout.basis === "contest_votes"
              ? "Turnout (% registered)"
              : turnout.basis === "calculated_ballots"
                ? "Calculated turnout"
                : "Official turnout"}
          </small>
          <strong>{percent(turnout.percent)}</strong>
        </div>
        <div>
          <small>
            {turnout.basis === "contest_votes"
              ? "Votes cast in this race"
              : "Ballots cast"}
          </small>
          <strong>
            {number(
              turnout.basis === "contest_votes"
                ? turnout.votes_cast
                : turnout.ballots_cast,
            )}
          </strong>
        </div>
        <div>
          <small>Eligible registration</small>
          <strong>{number(turnout.registered_voters)}</strong>
        </div>
      </div>
      <p className="footnote">{turnout.definition}</p>
    </>
  );
}
export function Loading() {
  return (
    <div className="loading" role="status">
      <strong>Loading election records…</strong>
      <div className="skeleton" aria-hidden="true" />
      <div className="skeleton" aria-hidden="true" />
      <div className="skeleton" aria-hidden="true" />
    </div>
  );
}
export function ErrorState({ message }: { message: string }) {
  const status = message.match(/\((\d{3})\)/)?.[1];
  return (
    <div className="error notice" role="alert">
      <Icon name="info" />
      <div>
        <h2>Data couldn’t be loaded</h2>
        <p>
          {status === "404"
            ? "This election record could not be found (404)."
            : `Election records are temporarily unavailable.${status ? ` Request failed (${status}).` : ""}`}{" "}
          Try again, or return to the catalog.
        </p>
        <div className="error-actions">
          <button onClick={() => window.location.reload()}>Try again</button>
          <Link to="/">Back to the catalog</Link>
        </div>
      </div>
    </div>
  );
}

export function NotFound() {
  return (
    <div className="empty">
      <h1>Page not found</h1>
      <Link to="/">Back to the catalog</Link>
    </div>
  );
}

export function CandidateOverview({
  results,
  unitKind = "state",
  provider = false,
}: {
  results: Results;
  unitKind?: "state" | "district";
  provider?: boolean;
}) {
  const leaders = results.candidates.slice(0, 2);
  const remaining = results.candidates.slice(2);
  return (
    <section
      className="result-summary statewide"
      aria-label="Candidate results"
    >
      <div className="summary-heading">
        <h2>
          {unitKind === "district"
            ? `${results.name} · Candidate results`
            : "Statewide candidate results"}
        </h2>
        <a className="small" href="#geography-explorer">
          Explore {unitKind === "district" ? "districts" : "counties"}
        </a>
      </div>
      <div className="lead-grid">
        <div className="lead-candidates">
          {leaders.length ? (
            leaders.map((c) => (
              <div className="lead-candidate" key={c.id}>
                <div className="candidate-label">
                  <span className={`party ${partyClass(c.party)}`}>
                    {c.party}
                  </span>
                  <div>
                    <strong>{c.name}</strong>
                    <small>
                      {c.party_name}
                      {!["verified", "source_checked"].includes(c.status)
                        ? " · Unavailable"
                        : ""}
                    </small>
                  </div>
                </div>
                <div className="lead-value">
                  <strong className={`${partyClass(c.party)}-text`}>
                    {percent(c.percent)}
                  </strong>
                  <small>{number(c.votes)} votes</small>
                </div>
                {c.percent == null ? (
                  <p className="small muted">Share unavailable</p>
                ) : (
                  <div className="track" aria-hidden="true">
                    <span
                      className={partyClass(c.party)}
                      style={{ width: `${c.percent}%` }}
                    />
                  </div>
                )}
              </div>
            ))
          ) : (
            <p className="empty">
              Candidate results have not been verified for this election.
            </p>
          )}
        </div>
        <aside className="summary-stats">
          <dl>
            <div>
              <dt>
                {unitKind === "district"
                  ? "District contest votes"
                  : "Statewide contest votes"}
              </dt>
              <dd>{number(results.total_votes)}</dd>
            </div>
            {results.percent_reporting !== undefined ? (
              <div>
                <dt>% Reporting</dt>
                <dd>{percent(results.percent_reporting)}</dd>
              </div>
            ) : (
              <div>
                <dt>
                  {results.turnout.basis === "contest_votes"
                    ? "Turnout (% registered)"
                    : unitKind === "district"
                      ? "Official district turnout"
                      : "Official statewide turnout"}
                </dt>
                <dd>{percent(results.turnout.percent)}</dd>
              </div>
            )}
          </dl>
          <Link to="/methodology">
            {results.percent_reporting !== undefined
              ? "About these results"
              : "Votes and turnout explained"}
          </Link>
        </aside>
      </div>
      {remaining.length > 0 ? (
        <details className="roster" key={results.geoid}>
          <summary>
            Show all {results.candidates.length}{" "}
            {provider
              ? "reported candidates"
              : "candidates, including write-ins"}
          </summary>
          <div className="candidate-summary candidate-list">
            {remaining.map((c) => (
              <CandidateRow key={c.id} candidate={c} compact />
            ))}
          </div>
        </details>
      ) : (
        leaders.length > 0 && (
          <p className="summary-foot">
            All {results.candidates.length} listed candidates are shown.
          </p>
        )
      )}
      <p className="summary-foot">
        {provider
          ? "Shares use the listed civicAPI candidates."
          : results.status === "reported"
            ? "Vote shares use all published statewide candidate totals, including write-ins."
            : results.status === "secondary"
              ? "Vote shares use all candidate totals in the secondary source, including write-ins."
              : "Vote shares include all verified candidates and write-ins."}
      </p>
    </section>
  );
}
