import { useEffect, useState, useSyncExternalStore } from "react";
import { midtermIsStale } from "./midterm";
import {
  initializeGovernor,
  officeSnapshot,
  prefetchOffices,
  refreshOffice,
  revalidateOffices,
  subscribeOffices,
} from "./midtermCache";

const API = "/api/midterm-2026";
export const BACKSTOP_MS = 5 * 60_000;
export const DEGRADED_MS = BACKSTOP_MS;

export function useMidterm(office = "governor") {
  const [now, setNow] = useState(Date.now);
  const snapshot = useSyncExternalStore(
    subscribeOffices,
    () => officeSnapshot(office),
    () => officeSnapshot(office),
  );
  const governor = useSyncExternalStore(
    subscribeOffices,
    () => officeSnapshot("governor"),
    () => officeSnapshot("governor"),
  );
  const data =
    snapshot.data && midtermIsStale(snapshot.data, Math.max(now, Date.now()))
      ? { ...snapshot.data, stale: true }
      : snapshot.data;

  useEffect(() => {
    void initializeGovernor().catch(() => {});
    const tick = () => setNow(Date.now());
    const timer = setInterval(tick, 60_000);
    window.addEventListener("focus", tick);
    document.addEventListener("visibilitychange", tick);
    return () => {
      clearInterval(timer);
      window.removeEventListener("focus", tick);
      document.removeEventListener("visibilitychange", tick);
    };
  }, []);
  useEffect(() => {
    if (office !== "governor" && !officeSnapshot(office).data)
      void refreshOffice(office, "default").catch(() => {});
  }, [office]);
  useEffect(() => {
    if (!governor.data) return;
    // Two frames let Governor paint before background prefetch. Its fresh check goes first.
    let second = 0;
    const first = requestAnimationFrame(() => {
      second = requestAnimationFrame(() => {
        // Governor validation already started after the cache lookup. A slow validation
        // occupies one queue slot but cannot prevent the remaining offices warming.
        void prefetchOffices();
      });
    });
    return () => {
      cancelAnimationFrame(first);
      cancelAnimationFrame(second);
    };
  }, [governor.data]);
  // One stream, independent of office selection. Reconnect announces the current revision,
  // as early voting does; every revalidation retains the displayed results.
  useEffect(() => {
    let stream: EventSource | null = null;
    let disposed = false;
    function connect() {
      stream?.close();
      stream = null;
      if (disposed || document.visibilityState !== "visible") return;
      const source = new EventSource(`${API}/updates`);
      stream = source;
      source.addEventListener("revision", (event) => {
        if (disposed || stream !== source) return;
        try {
          const value = JSON.parse((event as MessageEvent).data);
          if (typeof value.revision !== "string" || !value.revision) return;
          const offices = Array.isArray(value.offices)
            ? value.offices
            : undefined;
          void revalidateOffices(value.revision, offices);
        } catch {
          /* Invalid events cannot replace visible results. */
        }
      });
    }
    const resume = () => {
      if (document.visibilityState !== "visible") {
        stream?.close();
        stream = null;
      } else if (!stream || stream.readyState === EventSource.CLOSED) connect();
    };
    const timer = setInterval(() => {
      if (document.visibilityState === "visible") void revalidateOffices();
    }, BACKSTOP_MS);
    connect();
    window.addEventListener("focus", resume);
    window.addEventListener("online", resume);
    document.addEventListener("visibilitychange", resume);
    return () => {
      disposed = true;
      stream?.close();
      clearInterval(timer);
      window.removeEventListener("focus", resume);
      window.removeEventListener("online", resume);
      document.removeEventListener("visibilitychange", resume);
    };
  }, []);
  return {
    data,
    error: data ? null : snapshot.error,
    refreshError: data ? snapshot.error : null,
  };
}
