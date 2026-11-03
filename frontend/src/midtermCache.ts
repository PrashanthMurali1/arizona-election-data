import { get } from "./api";
import { midtermOffices } from "./midterm";
import type { MidtermResults } from "./types";

type Snapshot = {
  data: MidtermResults | null;
  error: string | null;
  savedAt: number;
};
const entries = new Map<string, Snapshot>();
const pending = new Map<
  string,
  { promise: Promise<void>; cache: RequestCache }
>();
const listeners = new Set<() => void>();
const ids: string[] = midtermOffices.map(([id]) => id);
let selectedOffice = "governor";
let governorStart: Promise<void> | undefined;
let prefetch: Promise<void> | undefined;
let active = 0;
const desiredRevision = new Map<string, string>();
const queue: {
  office: string;
  run: () => Promise<void>;
  resolve: () => void;
  reject: (error: unknown) => void;
}[] = [];

// Memory retains render state only. HTTP cache owns persistent responses, freshness and ETags.
export function initialMidtermOffice() {
  return selectedOffice;
}
export function rememberMidtermOffice(office: string) {
  selectedOffice = office;
}
export function officeSnapshot(office: string): Snapshot {
  let entry = entries.get(office);
  if (!entry) {
    entry = { data: null, error: null, savedAt: 0 };
    entries.set(office, entry);
  }
  return entry;
}
export function subscribeOffices(listener: () => void) {
  listeners.add(listener);
  return () => {
    listeners.delete(listener);
  };
}
function priority(office: string) {
  return office === "governor" ? 0 : office === selectedOffice ? 1 : 2;
}
function drain() {
  while (active < 2 && queue.length) {
    queue.sort((a, b) => priority(a.office) - priority(b.office));
    const task = queue.shift()!;
    active++;
    task
      .run()
      .then(task.resolve, task.reject)
      .finally(() => {
        active--;
        drain();
      });
  }
}
export function refreshOffice(
  office: string,
  cache: RequestCache,
): Promise<void> {
  const existing = pending.get(office);
  if (existing) {
    // A notification during a default cache lookup still earns conditional validation.
    if (cache === "no-cache" && existing.cache !== "no-cache")
      return existing.promise
        .catch(() => {})
        .then(() => refreshOffice(office, "no-cache"));
    return existing.promise;
  }
  officeSnapshot(office);
  const promise = new Promise<void>((resolve, reject) => {
    queue.push({
      office,
      resolve,
      reject,
      run: async () => {
        try {
          const data = await get<MidtermResults>(
            `/api/midterm-2026?office=${encodeURIComponent(office)}`,
            undefined,
            cache,
          );
          if (!Array.isArray(data.offices?.[office]))
            throw new Error("Invalid office results received.");
          entries.set(office, {
            data: { ...data, offices: { [office]: data.offices[office] } },
            error: null,
            savedAt: Date.now(),
          });
        } catch (error) {
          entries.set(office, {
            ...officeSnapshot(office),
            error:
              error instanceof Error
                ? error.message
                : "Unable to load results.",
          });
          throw error;
        } finally {
          pending.delete(office);
          listeners.forEach((listener) => listener());
        }
      },
    });
  });
  pending.set(office, { promise, cache });
  drain();
  return promise;
}
export function initializeGovernor(): Promise<void> {
  governorStart ??= (async () => {
    // HTTP cache can paint immediately; no-cache then validates with its stored ETag.
    try {
      await refreshOffice("governor", "default");
    } finally {
      await refreshOffice("governor", "no-cache");
    }
  })();
  return governorStart;
}
export function prefetchOffices(): Promise<void> {
  prefetch ??= Promise.allSettled(
    ids
      .filter((id) => id !== "governor")
      .map(async (id) => {
        await refreshOffice(id, "default");
        const revision = desiredRevision.get(id);
        if (revision && officeSnapshot(id).data?.revision !== revision)
          await revalidateOffices(revision, [id]);
      }),
  ).then(() => {});
  return prefetch;
}
const notifications = new Map<
  string,
  { revision: string; promise: Promise<void> }
>();
export function revalidateOffices(
  revision?: string,
  offices?: string[],
): Promise<void> {
  const targeted =
    offices?.length && offices.every((office) => ids.includes(office));
  if (revision)
    for (const id of targeted ? offices! : ids)
      desiredRevision.set(id, revision);
  const targets = targeted ? offices! : [...entries.keys()];
  return Promise.allSettled(
    targets.map(async (office) => {
      const snapshot = officeSnapshot(office);
      if (
        revision &&
        snapshot.data?.revision === revision &&
        !snapshot.data.stale &&
        !snapshot.error
      )
        return;
      const ongoing = notifications.get(office);
      if (ongoing && ongoing.revision === revision) return ongoing.promise;
      const request = (async () => {
        // Serialize different notifications so an older office response never wins.
        if (ongoing) await ongoing.promise.catch(() => {});
        const shared = pending.has(office);
        await refreshOffice(office, "no-cache");
        // A request started before this announcement may complete with the old revision.
        // It may be shared for dedupe, but must not swallow the newer invalidation.
        if (
          shared &&
          revision &&
          officeSnapshot(office).data?.revision !== revision
        )
          await refreshOffice(office, "no-cache");
      })();
      notifications.set(office, { revision: revision ?? "", promise: request });
      try {
        await request;
      } finally {
        if (notifications.get(office)?.promise === request)
          notifications.delete(office);
      }
    }),
  ).then(() => {});
}
