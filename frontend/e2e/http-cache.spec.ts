import { test, expect } from "@playwright/test";

// No request routing: Playwright routing disables the browser HTTP cache.
test("HTTP cache survives reloads and forced validation transfers no unchanged body", async ({
  page,
  context,
}) => {
  const network = await context.newCDPSession(page);
  await network.send("Network.enable");
  const statuses: number[] = [];
  const requests = new Map<string, string>();
  let target = "";
  network.on("Network.requestWillBeSent", (event) =>
    requests.set(event.requestId, event.request.url),
  );
  network.on("Network.responseReceivedExtraInfo", (event) => {
    if (requests.get(event.requestId) === target)
      statuses.push(event.statusCode);
  });
  await page.goto("/methodology");
  const url = `/api/elections/az-2026-early-voting/activity?cache-test=${Date.now()}`;
  target = new URL(url, page.url()).href;
  const load = (cache: RequestCache = "default") =>
    page.evaluate(
      async ({ url, cache }) => {
        const response = await fetch(url, { cache });
        const data = await response.json();
        return {
          data,
          etag: response.headers.get("etag"),
          policy: response.headers.get("cache-control"),
        };
      },
      { url, cache },
    );
  const first = await load();
  expect(first.policy).toContain("private, max-age=300");
  expect(first.etag).toBeTruthy();
  statuses.length = 0;
  expect(await load()).toEqual(first);
  expect(statuses).toEqual([]); // Fresh reuse makes no origin request.
  await page.reload();
  statuses.length = 0;
  expect(await load()).toEqual(first);
  expect(statuses).toEqual([]);
  expect(await load("no-cache")).toEqual(first); // Fetch exposes the cached body as 200.
  await expect.poll(() => statuses.filter((s) => s === 304).length).toBe(1);
});
