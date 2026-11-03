import { selectOffice } from "./helpers";
import { test, expect } from "@playwright/test";
import type { Election } from "../src/types";

// Never route requests here: interception disables the real browser HTTP cache.
test("selected federal office prefetches all page data and navigation uses HTTP cache", async ({
  page,
  context,
  request,
}) => {
  const catalog = (await (
    await request.get("/api/elections")
  ).json()) as Election[];
  const senate = catalog.filter((e) => e.office_id === "us-senate");
  const house = catalog.filter((e) => e.office_id === "us-house");
  expect(senate.length).toBeGreaterThanOrEqual(5);
  expect(house.length).toBeGreaterThanOrEqual(8);
  const dependencies = (entries: Election[], counties: boolean) =>
    new Set(
      entries.flatMap((e) =>
        // Historical statewide archives are served by their own overview endpoint.
        e.id.includes("-historical-")
          ? [`/api/historical-elections/${e.id}`]
          : [
              `/api/elections/${e.id}`,
              ...(counties
                ? [
                    `/api/elections/${e.id}/counties`,
                    `/api/elections/${e.id}/activity`,
                  ]
                : []),
              `/api/geography/${e.boundary_id}`,
            ],
      ),
    );
  const senateUrls = dependencies(senate, true);
  const houseUrls = dependencies(house, false);
  const ids = new Map<string, string>();
  const versions = new Set<string>();
  const completed = new Set<string>();
  const origin: string[] = [];
  const policies = new Map<string, string>();
  const statuses = new Map<string, number>();
  const network = await context.newCDPSession(page);
  await network.send("Network.enable");
  await network.send("Network.setCacheDisabled", { cacheDisabled: false });
  network.on("Network.requestWillBeSent", (e) => {
    const url = new URL(e.request.url);
    ids.set(e.requestId, url.pathname);
    if (senateUrls.has(url.pathname) || houseUrls.has(url.pathname)) {
      const version = url.searchParams.get("ui");
      if (version) versions.add(version);
    }
  });
  network.on("Network.responseReceivedExtraInfo", (e) => {
    const path = ids.get(e.requestId);
    if (path) origin.push(path);
  });
  network.on("Network.responseReceived", (e) => {
    const path = ids.get(e.requestId);
    if (!path) return;
    const headers = Object.fromEntries(
      Object.entries(e.response.headers).map(([key, value]) => [
        key.toLowerCase(),
        value,
      ]),
    );
    policies.set(path, String(headers["cache-control"] ?? ""));
    statuses.set(path, e.response.status);
  });
  const verify = (urls: Set<string>) => {
    for (const url of urls) {
      expect(statuses.get(url)).toBe(200);
      // Historical statewide overviews are not part of the one-day browser cache policy.
      if (!url.startsWith("/api/historical-elections/"))
        expect(policies.get(url)).toContain("max-age=86400");
    }
  };
  network.on("Network.loadingFinished", (e) => {
    const path = ids.get(e.requestId);
    if (path) completed.add(path);
  });
  const done = (urls: Set<string>) =>
    [...urls].every((url) => completed.has(url));
  await page.goto("/");
  await page.getByRole("tab", { name: "Federal Elections" }).click();
  await expect(page.getByLabel("Federal office")).toHaveValue("us-senate");
  await expect.poll(() => done(senateUrls)).toBe(true);
  verify(senateUrls);
  expect(origin.some((url) => url.includes("us-house"))).toBe(false);
  const senateOrigin = origin.filter((url) => senateUrls.has(url)).length;
  await page.getByRole("tab", { name: "State Elections" }).click();
  await page.getByRole("tab", { name: "Federal Elections" }).click();
  await page.locator(`a[href="/elections/${senate[0].id}"]`).click();
  await expect(page.getByLabel("Election year")).toBeVisible();
  for (const entry of senate) {
    await page.getByLabel("Election year").selectOption(entry.id);
    await expect(
      page.getByRole("heading", {
        name: `U.S. Senate ${entry.year}`,
        exact: true,
      }),
    ).toBeVisible();
    await expect(page.locator(".county-map path")).toHaveCount(
      entry.county_count,
    );
  }
  expect(origin.filter((url) => senateUrls.has(url)).length).toBe(senateOrigin);

  await page
    .getByRole("navigation", { name: "Main navigation" })
    .getByRole("link", { name: "Election catalog", exact: true })
    .click();
  await page.getByRole("tab", { name: "Federal Elections" }).click();
  await selectOffice(page, "Federal office", "us-house");
  await expect.poll(() => done(houseUrls)).toBe(true);
  verify(houseUrls);
  // Only the browser-cached URLs must not hit the network again; historical statewide overviews
  // are deliberately uncached and revalidate whenever the tab is re-entered.
  const cachedHouse = (url: string) =>
    houseUrls.has(url) && !url.startsWith("/api/historical-elections/");
  const houseOrigin = origin.filter(cachedHouse).length;
  await page.getByRole("tab", { name: "Early Voting" }).click();
  await page.getByRole("tab", { name: "Federal Elections" }).click();
  await expect(page.getByLabel("Federal office")).toHaveValue("us-house");
  await page.locator(`a[href="/elections/${house[0].id}"]`).click();
  // Historical archives render a different page; this loop covers the district-results page.
  for (const entry of house.filter((e) => !e.id.includes("-historical-"))) {
    await page.getByLabel("Election year").selectOption(entry.id);
    await expect(
      page.getByRole("heading", {
        name: `U.S. House ${entry.year}`,
        exact: true,
      }),
    ).toBeVisible();
    await expect(
      page
        .getByRole("region", { name: "District results table" })
        .locator("tbody tr"),
    ).toHaveCount(entry.district_count ?? 9);
    // All contested districts are present in the cached overview response.
    await expect(page.locator(".county-map path")).toHaveCount(9);
  }
  expect(origin.filter(cachedHouse).length).toBe(houseOrigin);
  expect(versions.size).toBe(1);
  const version = [...versions][0];
  expect(version).toMatch(/^[a-f0-9]{16}$/);
  const path = `/api/elections/${senate[0].id}`;
  const loadVersion = (v: string) =>
    page.evaluate(
      async ({ path, v }) => {
        const response = await fetch(`${path}?ui=${v}`);
        await response.json();
      },
      { path, v },
    );
  const before = origin.filter((url) => url === path).length;
  await loadVersion(`${version}-changed`);
  await expect
    .poll(() => origin.filter((url) => url === path).length)
    .toBe(before + 1);
  await loadVersion(`${version}-changed`);
  expect(origin.filter((url) => url === path).length).toBe(before + 1);
  await network.send("Network.clearBrowserCache");
  await loadVersion(`${version}-changed`);
  await expect
    .poll(() => origin.filter((url) => url === path).length)
    .toBe(before + 2);
});
