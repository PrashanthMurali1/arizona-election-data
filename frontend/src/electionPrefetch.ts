import type { Election } from "./types";
import { cacheUrl } from "./cacheUrl";

// These are the same URLs used by ElectionPage and HouseElectionPage. House
// overviews already contain every district's candidates, results and sources.
export function electionPrefetchUrls(elections: Election[], office: string) {
  const urls = new Set<string>();
  if (
    !["us-senate", "us-house", "governor", "attorney-general"].includes(office)
  )
    return [];
  for (const election of elections.filter((e) => e.office_id === office)) {
    const base = `/api/elections/${election.id}`;
    urls.add(base);
    if (office !== "us-house") {
      urls.add(`${base}/counties`);
      urls.add(`${base}/activity`);
    }
    urls.add(`/api/geography/${election.boundary_id}`);
  }
  return [...urls];
}

export async function prefetchElections(
  elections: Election[],
  office: string,
  signal: AbortSignal,
) {
  const queue = electionPrefetchUrls(elections, office);
  let next = 0;
  async function worker() {
    while (!signal.aborted && next < queue.length) {
      const url = queue[next++];
      // Retry a partial failure once; successful bodies remain in HTTP cache.
      for (let attempt = 0; attempt < 2 && !signal.aborted; attempt++) {
        try {
          const response = await fetch(cacheUrl(url), {
            signal,
            cache: "default",
          });
          if (!response.ok)
            throw new Error(`Prefetch failed (${response.status})`);
          await response.arrayBuffer(); // Finish the body so it can be cached.
          break;
        } catch {
          // Failed prefetches never block a card. Navigation, re-entry or an
          // online event can retry through the normal HTTP cache again.
        }
      }
    }
  }
  await Promise.all(Array.from({ length: 3 }, worker));
}
