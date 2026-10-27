import type { Candidate, Results, Turnout } from "./types";
import { number, percent, partyClass } from "./results";
export function Availability({ status }: { status: string }) {
  return (
    <span
      className={`badge ${status === "verified" ? "verified" : "incomplete"}`}
    >
      <span aria-hidden="true">{status === "verified" ? "✓" : "◷"}</span>{" "}
      {status === "verified"
        ? "Verified results"
        : status === "pre_results"
          ? "Voting in progress"
          : status === "unofficial"
            ? "Unofficial results"
            : "Incomplete"}
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
      <div className="vote-track">
        <div
          className={partyClass(candidate.party)}
          style={{ width: `${candidate.percent ?? 0}%` }}
        />
      </div>
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
      <span className="pulse" />
      Loading election records…
    </div>
  );
}
export function ErrorState({ message }: { message: string }) {
  return (
    <div className="error" role="alert">
      <h2>Data couldn’t be loaded</h2>
      <p>{message}</p>
      <button onClick={() => window.location.reload()}>Try again</button>
    </div>
  );
}
