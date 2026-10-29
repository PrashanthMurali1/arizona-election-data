import { useEffect, useState } from "react";
import { get } from "./api";
import type { Activity, Geography } from "./types";
import { currentStaleness } from "./earlyVotingStatus";

const ACTIVITY_FRESH_MS = 5 * 60_000;

const API = "/api/elections/az-2026-early-voting";
type Data = { activity: Activity; geo: Geography };

export function useEarlyVoting(boundary: string) {
  const [data, setData] = useState<Data | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [refreshError, setRefreshError] = useState<string | null>(null);
  const [checking, setChecking] = useState(true);
  const [now, setNow] = useState(Date.now);

  useEffect(() => {
    const controller = new AbortController();
    let current: { data: Activity; checkedAt: number } | null = null;
    let geo: Geography | null = null;
    let pending = false;
    let target: string | null = null;
    let stream: EventSource | null = null;
    let timer: ReturnType<typeof setTimeout>;
    const fresh = () =>
      current &&
      Date.now() >= current.checkedAt &&
      Date.now() - current.checkedAt < ACTIVITY_FRESH_MS &&
      geo;
    const schedule = (delay = ACTIVITY_FRESH_MS) => {
      clearTimeout(timer);
      timer = setTimeout(() => {
        if (document.visibilityState === "visible") void refresh();
        else schedule();
      }, delay);
    };
    async function refresh(cache: RequestCache = "no-cache") {
      if (controller.signal.aborted || pending) return;
      const requested = target;
      pending = true;
      setChecking(true);
      try {
        // Activity is the single atomic changing response: statewide metrics,
        // counties, registration breakdowns, provenance, failures and revision.
        // The registration map does not use candidate/result data.
        const retainedGeo = geo;
        const requests = [
          get<Activity>(`${API}/activity`, controller.signal, cache),
          retainedGeo
            ? Promise.resolve(retainedGeo)
            : get<Geography>(`/api/geography/${boundary}`, controller.signal),
        ] as const;
        await Promise.allSettled(requests);
        const [activity, geography] = await Promise.all(requests);
        if (controller.signal.aborted) return;
        if (
          !activity?.revision ||
          !Array.isArray(activity.counties) ||
          geography.boundary_id !== boundary
        )
          throw new Error("Incomplete early-voting response");
        current = { data: activity, checkedAt: Date.now() };
        geo = geography;
        setData({ activity, geo });
        setError(null);
        setRefreshError(null);
        setChecking(false);
        setNow(Date.now());
      } catch (failure) {
        if (!controller.signal.aborted) {
          const message =
            failure instanceof Error
              ? failure.message
              : "Unable to load early-voting data.";
          if (current && geo)
            setRefreshError(
              "Could not check for updates. Showing the last successfully loaded data.",
            );
          else setError(message);
          setChecking(false);
        }
      } finally {
        pending = false;
        if (!controller.signal.aborted) {
          schedule();
          if (
            target !== requested &&
            target &&
            target !== current?.data.revision
          )
            void refresh();
        }
      }
    }
    function connect() {
      stream?.close();
      if (document.visibilityState !== "visible") return;
      setChecking(true);
      const source = new EventSource(`${API}/updates`);
      stream = source;
      source.addEventListener("revision", (event) => {
        if (controller.signal.aborted || stream !== source) return;
        try {
          const value = JSON.parse((event as MessageEvent).data).revision;
          if (typeof value !== "string" || !value) return;
          target = value;
          if (fresh() && value === current?.data.revision) {
            setChecking(false);
            setRefreshError(null);
            setNow(Date.now());
          } else void refresh();
        } catch {
          /* Invalid notifications cannot replace displayed data. */
        }
      });
      source.addEventListener("error", () => {
        if (!controller.signal.aborted && stream === source) {
          setChecking(false);
          setRefreshError(
            "Update connection interrupted. Showing previously loaded data; reconnecting automatically.",
          );
        }
      });
      // Defer the initial HTTP-cache lookup past StrictMode's aborted setup.
      if (!current) queueMicrotask(() => void refresh("default"));
      else if (!fresh()) void refresh();
    }
    const resume = () => {
      if (document.visibilityState === "visible") connect();
      else stream?.close();
    };
    const ageTimer = setInterval(() => setNow(Date.now()), 30_000);
    setError(null);
    setRefreshError(null);
    setChecking(true);
    setData(null);
    connect();
    schedule();
    window.addEventListener("focus", resume);
    window.addEventListener("online", resume);
    document.addEventListener("visibilitychange", resume);
    return () => {
      controller.abort();
      stream?.close();
      clearTimeout(timer);
      clearInterval(ageTimer);
      window.removeEventListener("focus", resume);
      window.removeEventListener("online", resume);
      document.removeEventListener("visibilitychange", resume);
    };
  }, [boundary]);

  return {
    data: data
      ? { ...data, activity: currentStaleness(data.activity, now) }
      : null,
    error,
    refreshError,
    checking,
  };
}
