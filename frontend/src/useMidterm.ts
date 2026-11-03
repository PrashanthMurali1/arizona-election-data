import { useEffect, useState } from "react";
import { get } from "./api";
import type { MidtermResults } from "./types";

const API = "/api/midterm-2026";
const HOUR_MS = 60 * 60_000;
// The browser may cache results for two hours; this is only a backstop for a stream that never
// connects (for example one blocked by a proxy). Normal updates arrive from the stream.
export const BACKSTOP_MS = 2 * HOUR_MS;
// Live-fallback and stale responses are never covered by a stream notification, so check sooner.
export const DEGRADED_MS = 5 * 60_000;

// Results are cached by the browser for two hours. A scheduled job republishes them every 30
// minutes and the update stream announces each new revision, so the page revalidates (by ETag)
// only when something actually changed.
export function useMidterm() {
  const [data, setData] = useState<MidtermResults | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [refreshError, setRefreshError] = useState<string | null>(null);

  useEffect(() => {
    const controller = new AbortController();
    let current: MidtermResults | null = null;
    let pending = false;
    let target: string | null = null;
    let stream: EventSource | null = null;
    let timer: ReturnType<typeof setTimeout> | undefined;
    // Revisions already fetched for, and those whose fetch failed (retried on the next announcement).
    const attempted = new Set<string>();
    const failed = new Set<string>();

    function schedule() {
      clearTimeout(timer);
      if (controller.signal.aborted) return;
      const degraded = !current || current.stale || current.revision === "live";
      timer = setTimeout(
        () => {
          if (document.visibilityState === "visible")
            void refresh("no-cache", null);
          else schedule();
        },
        degraded ? DEGRADED_MS : BACKSTOP_MS,
      );
    }
    async function refresh(cache: RequestCache, announced: string | null) {
      if (controller.signal.aborted || pending) return;
      pending = true;
      try {
        const value = await get<MidtermResults>(API, controller.signal, cache);
        if (controller.signal.aborted) return;
        current = value;
        setData(value);
        setError(null);
        setRefreshError(null);
      } catch (exc) {
        if (controller.signal.aborted || (exc as Error).name === "AbortError")
          return;
        if (announced) failed.add(announced);
        // Keep showing the last good results if a later refresh fails.
        if (current) setRefreshError((exc as Error).message);
        else setError((exc as Error).message);
      } finally {
        pending = false;
        schedule();
        reconcile();
      }
    }
    // Refetch (past the HTTP cache) once per announced revision that differs from what is shown.
    function reconcile() {
      if (
        controller.signal.aborted ||
        pending ||
        !current ||
        !target ||
        target === current.revision ||
        attempted.has(target)
      )
        return;
      attempted.add(target);
      void refresh("no-cache", target);
    }
    function connect() {
      stream?.close();
      stream = null;
      if (document.visibilityState !== "visible") return;
      const source = new EventSource(`${API}/updates`);
      stream = source;
      source.addEventListener("revision", (event) => {
        if (controller.signal.aborted || stream !== source) return;
        try {
          const value = JSON.parse((event as MessageEvent).data).revision;
          if (typeof value !== "string" || !value) return;
          target = value;
          // A reconnect that announces a revision whose fetch failed earns one more attempt.
          if (failed.delete(value)) attempted.delete(value);
          reconcile();
        } catch {
          /* Invalid notifications cannot replace displayed data. */
        }
      });
      // EventSource reconnects by itself; the first event after a reconnect
      // announces the current revision, which catches anything missed.
    }
    const resume = () => {
      if (document.visibilityState !== "visible") {
        stream?.close();
        stream = null;
      } else if (!stream || stream.readyState === EventSource.CLOSED) connect();
    };
    // Defer the first HTTP-cache lookup past StrictMode's aborted setup.
    queueMicrotask(() => void refresh("default", null));
    connect();
    window.addEventListener("focus", resume);
    window.addEventListener("online", resume);
    document.addEventListener("visibilitychange", resume);
    return () => {
      controller.abort();
      clearTimeout(timer);
      stream?.close();
      window.removeEventListener("focus", resume);
      window.removeEventListener("online", resume);
      document.removeEventListener("visibilitychange", resume);
    };
  }, []);

  return { data, error, refreshError };
}
