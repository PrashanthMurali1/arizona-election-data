import { afterEach, describe, expect, it, vi } from "vitest";
import type { Election } from "./types";
import { electionPrefetchUrls, prefetchElections } from "./electionPrefetch";

const elections = [
  { id: "senate-old", office_id: "us-senate", boundary_id: "county" },
  { id: "senate-new", office_id: "us-senate", boundary_id: "county" },
  { id: "house", office_id: "us-house", boundary_id: "districts" },
  { id: "governor-old", office_id: "governor", boundary_id: "county" },
  { id: "governor-new", office_id: "governor", boundary_id: "county" },
  {
    id: "attorney-general-old",
    office_id: "attorney-general",
    boundary_id: "county",
  },
  {
    id: "attorney-general-new",
    office_id: "attorney-general",
    boundary_id: "county",
  },
] as Election[];
afterEach(() => vi.unstubAllGlobals());

describe("historical election HTTP prefetch", () => {
  it("covers each office's page dependencies and deduplicates shared boundaries", () => {
    expect(electionPrefetchUrls(elections, "us-senate")).toEqual([
      "/api/elections/senate-old",
      "/api/elections/senate-old/counties",
      "/api/elections/senate-old/activity",
      "/api/geography/county",
      "/api/elections/senate-new",
      "/api/elections/senate-new/counties",
      "/api/elections/senate-new/activity",
    ]);
    expect(electionPrefetchUrls(elections, "us-house")).toEqual([
      "/api/elections/house",
      "/api/geography/districts",
    ]);
  });

  it.each(["governor", "attorney-general"])(
    "covers all %s dependencies without fetching other offices",
    (office) => {
      expect(electionPrefetchUrls(elections, office)).toEqual([
        `/api/elections/${office}-old`,
        `/api/elections/${office}-old/counties`,
        `/api/elections/${office}-old/activity`,
        "/api/geography/county",
        `/api/elections/${office}-new`,
        `/api/elections/${office}-new/counties`,
        `/api/elections/${office}-new/activity`,
      ]);
      expect(electionPrefetchUrls(elections, "early-voting")).toEqual([]);
    },
  );
  it.each(["us-senate", "governor", "attorney-general"])(
    "limits %s concurrency to three and retries only failed URLs",
    async (office) => {
      let active = 0;
      let peak = 0;
      const attempts = new Map<string, number>();
      vi.stubGlobal(
        "fetch",
        vi.fn(async (requestUrl: string, options: RequestInit) => {
          const url = new URL(requestUrl, "http://local").pathname;
          expect(options.cache).toBe("default");
          active++;
          peak = Math.max(peak, active);
          const count = (attempts.get(url) ?? 0) + 1;
          attempts.set(url, count);
          await new Promise((resolve) => setTimeout(resolve, 0));
          active--;
          if (url.endsWith("/counties") && count === 1)
            return new Response(null, { status: 503 });
          return new Response("{}");
        }),
      );
      await prefetchElections(elections, office, new AbortController().signal);
      expect(peak).toBe(3);
      expect(attempts.size).toBe(7);
      for (const [url, count] of attempts)
        expect(count).toBe(url.endsWith("/counties") ? 2 : 1);
    },
  );

  it("stops queued work on cancellation and does not loop on persistent failures", async () => {
    const controller = new AbortController();
    const fetch = vi.fn(
      (_url: string, options: RequestInit) =>
        new Promise<Response>((_resolve, reject) => {
          options.signal!.addEventListener("abort", () =>
            reject(new DOMException("Aborted", "AbortError")),
          );
        }),
    );
    vi.stubGlobal("fetch", fetch);
    const task = prefetchElections(elections, "us-senate", controller.signal);
    expect(fetch).toHaveBeenCalledTimes(3);
    controller.abort();
    await task;
    expect(fetch).toHaveBeenCalledTimes(3);

    const offline = vi.fn().mockRejectedValue(new TypeError("Offline"));
    vi.stubGlobal("fetch", offline);
    await prefetchElections(
      elections,
      "us-senate",
      new AbortController().signal,
    );
    expect(offline).toHaveBeenCalledTimes(14);
  });
});
