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
                : "Incomplete")}
    </span>
  );
}
export function CandidateRow({
  candidate,
  compact = false,
}: {
  candidate: Candidate;
  compact?: boolean;
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
          <strong>{percent(candidate.percent)}</strong>
          <small>{number(candidate.votes)} votes</small>
        </div>
      </div>
      {candidate.percent == null ? (
        <small className="unavailable-share">Share unavailable</small>
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
  return (
    <div className="candidate-summary">
      {results.candidates.length ? (
        results.candidates.map((c) => <CandidateRow key={c.id} candidate={c} />)
      ) : (
        <p className="empty">
          Candidate results have not been verified for this election.
        </p>
      )}
    </div>
  );
}
export function TurnoutMetrics({ turnout }: { turnout: Turnout }) {
  return (
    <>
      <div className="turnout-metrics">
        <div>
          <small>Official turnout</small>
          <strong>{percent(turnout.percent)}</strong>
        </div>
        <div>
          <small>Ballots cast</small>
          <strong>{number(turnout.ballots_cast)}</strong>
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
            <div>
              <dt>
                {unitKind === "district"
                  ? "Official district turnout"
                  : "Official statewide turnout"}
              </dt>
              <dd>{percent(results.turnout.percent)}</dd>
            </div>
          </dl>
          <Link to="/methodology">Votes and turnout explained</Link>
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
          : "Vote shares include all verified candidates and write-ins."}
      </p>
    </section>
  );
}
