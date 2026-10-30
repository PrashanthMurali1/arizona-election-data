import { useState } from "react";
import type { Election } from "../types";
import { ErrorState, Loading } from "../components";
import { useEarlyVoting } from "../useEarlyVoting";
import EarlyVotingDashboard from "./EarlyVotingDashboard";
import useGeographySelection from "../useGeographySelection";

export default function LiveElection({ election }: { election: Election }) {
  const { data, error, refreshError, checking } = useEarlyVoting(
    election.boundary_id,
  );
  const [selected, setSelected] = useState<string | null>(null);
  const { detailRef, focusSelection } = useGeographySelection(selected);
  if (error && !data) return <ErrorState message={error} />;
  if (!data) return <Loading />;
  return (
    <div className="embedded-early-voting">
      {checking && (
        <p className="muted" role="status">
          Checking for updates. Showing previously loaded data.
        </p>
      )}
      <EarlyVotingDashboard
        election={election}
        activity={data.activity}
        geo={data.geo}
        selected={selected}
        onSelect={(id) => {
          setSelected(id);
          if (id) focusSelection();
        }}
        detailRef={detailRef}
        refreshError={refreshError}
      />
    </div>
  );
}
