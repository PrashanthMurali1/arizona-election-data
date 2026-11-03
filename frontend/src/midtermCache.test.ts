import { beforeEach, expect, it, vi } from "vitest";
import type { MidtermResults } from "./types";

const get = vi.hoisted(() => vi.fn());
vi.mock("./api", () => ({ get }));
const result = (office: string, revision = "r1"): MidtermResults => ({
  election_date: "2026-11-03",
  source_url: "https://civicapi.org",
  retrieved_at: new Date().toISOString(),
  stale: false,
  refresh_error: null,
  revision,
  offices: { [office]: [] },
});
const fromUrl = (url: string) =>
  new URL(url, "http://localhost").searchParams.get("office")!;
const flush = async () => {
  for (let index = 0; index < 10; index++) await Promise.resolve();
};
let storageRead: ReturnType<typeof vi.fn>;
let storageWrite: ReturnType<typeof vi.fn>;
beforeEach(() => {
  vi.resetModules();
  get.mockReset();
  storageRead = vi.fn(() => {
    throw Error("storage unavailable");
  });
  storageWrite = vi.fn(() => {
    throw Error("storage unavailable");
  });
  vi.stubGlobal("localStorage", {
    getItem: storageRead,
    setItem: storageWrite,
  });
});

it("deduplicates in-flight requests and keeps out-of-order office responses separate", async () => {
  const cache = await import("./midtermCache");
  const resolves = new Map<string, (value: MidtermResults) => void>();
  get.mockImplementation(
    (url: string) =>
      new Promise((resolve) => resolves.set(fromUrl(url), resolve)),
  );
  const governor = cache.refreshOffice("governor", "default");
  expect(cache.refreshOffice("governor", "default")).toBe(governor);
  const house = cache.refreshOffice("us-house", "default");
  await flush();
  resolves.get("us-house")!(result("us-house", "r2"));
  await house;
  resolves.get("governor")!(result("governor"));
  await governor;
  expect(get).toHaveBeenCalledTimes(2);
  expect(cache.officeSnapshot("us-house").data?.revision).toBe("r2");
  expect(cache.officeSnapshot("governor").data?.revision).toBe("r1");
});

it("uses browser-cache lookup before mandatory Governor revalidation and bootstraps once per module", async () => {
  const cache = await import("./midtermCache");
  get.mockImplementation((url: string) =>
    Promise.resolve(result(fromUrl(url))),
  );
  await Promise.all([cache.initializeGovernor(), cache.initializeGovernor()]);
  expect(get.mock.calls.map(([url, , mode]) => [fromUrl(url), mode])).toEqual([
    ["governor", "default"],
    ["governor", "no-cache"],
  ]);
  await cache.initializeGovernor();
  expect(get).toHaveBeenCalledTimes(2);
});

it("prefetches the other five offices with no more than two concurrent requests", async () => {
  const cache = await import("./midtermCache");
  get.mockImplementation((url: string) =>
    Promise.resolve(result(fromUrl(url))),
  );
  await cache.initializeGovernor();
  const releases: (() => void)[] = [];
  let active = 0;
  let maximum = 0;
  get.mockImplementation(
    (url: string) =>
      new Promise<MidtermResults>((resolve) => {
        active++;
        maximum = Math.max(maximum, active);
        releases.push(() => {
          active--;
          resolve(result(fromUrl(url)));
        });
      }),
  );
  const prefetch = cache.prefetchOffices();
  await flush();
  expect(active).toBe(2);
  expect(get).toHaveBeenCalledTimes(4);
  for (let round = 0; round < 5; round++) {
    releases.splice(0).forEach((release) => release());
    await flush();
  }
  await prefetch;
  expect(maximum).toBe(2);
  expect(get).toHaveBeenCalledTimes(7);
  expect(
    new Set(get.mock.calls.slice(2).map(([url]) => fromUrl(url))).size,
  ).toBe(5);
});

it("revalidates all prefetched offices globally or only the targeted office and ignores duplicate revisions", async () => {
  const cache = await import("./midtermCache");
  let revision = "r1";
  get.mockImplementation((url: string) =>
    Promise.resolve(result(fromUrl(url), revision)),
  );
  await cache.initializeGovernor();
  await cache.prefetchOffices();
  get.mockClear();
  revision = "r2";
  await cache.revalidateOffices(revision);
  expect(get).toHaveBeenCalledTimes(6);
  expect(get.mock.calls.every(([, , mode]) => mode === "no-cache")).toBe(true);
  await cache.revalidateOffices(revision);
  expect(get).toHaveBeenCalledTimes(6);
  get.mockClear();
  revision = "r3";
  await cache.revalidateOffices(revision, ["us-house"]);
  expect(get.mock.calls.map(([url]) => fromUrl(url))).toEqual(["us-house"]);
  expect(cache.officeSnapshot("governor").data?.revision).toBe("r2");
  expect(cache.officeSnapshot("us-house").data?.revision).toBe("r3");
});

it("retains successful results during refresh and after a failed refresh", async () => {
  const cache = await import("./midtermCache");
  get.mockResolvedValueOnce(result("governor"));
  await cache.refreshOffice("governor", "default");
  get.mockRejectedValueOnce(new Error("offline"));
  const refresh = cache.refreshOffice("governor", "no-cache");
  expect(cache.officeSnapshot("governor").data?.revision).toBe("r1");
  await expect(refresh).rejects.toThrow("offline");
  expect(cache.officeSnapshot("governor").data?.revision).toBe("r1");
  expect(cache.officeSnapshot("governor").error).toBe("offline");
});

it("revalidates late prefetched HTTP-cache responses against an already announced revision", async () => {
  const cache = await import("./midtermCache");
  get.mockImplementation((url: string) =>
    Promise.resolve(result(fromUrl(url))),
  );
  await cache.initializeGovernor();
  get.mockImplementation((url: string, _signal: unknown, mode: RequestCache) =>
    Promise.resolve(result(fromUrl(url), mode === "no-cache" ? "r2" : "r1")),
  );
  await cache.revalidateOffices("r2");
  await cache.prefetchOffices();
  for (const office of [
    "governor",
    "attorney-general",
    "secretary-of-state",
    "us-house",
    "state-senate",
    "state-house",
  ]) {
    expect(cache.officeSnapshot(office).data?.revision).toBe("r2");
  }
});

it("keeps results and selection only in memory without reading or writing localStorage", async () => {
  let cache = await import("./midtermCache");
  get.mockResolvedValue(result("state-house"));
  await cache.refreshOffice("state-house", "default");
  cache.rememberMidtermOffice("state-house");
  expect(cache.initialMidtermOffice()).toBe("state-house");
  expect(cache.officeSnapshot("state-house").data?.revision).toBe("r1");
  expect(storageRead).not.toHaveBeenCalled();
  expect(storageWrite).not.toHaveBeenCalled();
  vi.resetModules();
  cache = await import("./midtermCache");
  expect(cache.initialMidtermOffice()).toBe("governor");
  expect(cache.officeSnapshot("state-house").data).toBeNull();
  expect(storageRead).not.toHaveBeenCalled();
  expect(storageWrite).not.toHaveBeenCalled();
});
