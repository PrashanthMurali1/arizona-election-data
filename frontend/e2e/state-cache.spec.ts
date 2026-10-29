import { test, expect } from "@playwright/test";
import type { Election } from "../src/types";

// Real preview and real HTTP cache: request interception is intentionally absent.
test("State Elections prefetches only the selected office and caches every election", async ({
  page,
  context,
  request,
}) => {
  const catalog = (await (
    await request.get("/api/elections")
  ).json()) as Election[];
  const governors = catalog.filter((e) => e.office_id === "governor");
  const attorneys = catalog.filter((e) => e.office_id === "attorney-general");
  expect(governors).toHaveLength(3);
  expect(attorneys).toHaveLength(3);
  const dependencies = (entries: Election[]) =>
    new Set(
      entries.flatMap((e) => [
        `/api/elections/${e.id}`,
        `/api/elections/${e.id}/counties`,
        `/api/elections/${e.id}/activity`,
        `/api/geography/${e.boundary_id}`,
      ]),
    );
  const governorUrls = dependencies(governors);
  const attorneyUrls = dependencies(attorneys);
  const urls = new Set([...governorUrls, ...attorneyUrls]);
  const network = await context.newCDPSession(page);
  await network.send("Network.enable");
  await network.send("Network.setCacheDisabled", { cacheDisabled: false });
  const paths = new Map<string, string>();
  const completed = new Set<string>();
  const origin: string[] = [];
  const versions = new Map<string, string | null>();
  const policies = new Map<string, string>();
  const statuses = new Map<string, number>();
  network.on("Network.requestWillBeSent", (e) => {
    const url = new URL(e.request.url);
    paths.set(e.requestId, url.pathname);
    if (urls.has(url.pathname))
      versions.set(url.pathname, url.searchParams.get("ui"));
  });
  network.on("Network.responseReceivedExtraInfo", (e) => {
    const path = paths.get(e.requestId);
    if (path) origin.push(path);
  });
  network.on("Network.responseReceived", (e) => {
    const path = paths.get(e.requestId);
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
  network.on("Network.loadingFinished", (e) => {
    const path = paths.get(e.requestId);
    if (path) completed.add(path);
  });
  const verifyBatch = async (batch: Set<string>) => {
    await expect
      .poll(() => [...batch].every((url) => completed.has(url)))
      .toBe(true);
    for (const url of batch) {
      expect(statuses.get(url)).toBe(200);
      expect(policies.get(url)).toContain("max-age=86400");
      expect(versions.get(url)).toMatch(/^[a-f0-9]{16}$/);
    }
  };
  await page.goto("/");
  await page.getByRole("tab", { name: "State Elections" }).click();
  await expect(page.getByLabel("State office")).toHaveValue("governor");
  await verifyBatch(governorUrls);
  expect(
    origin.some(
      (url) => url.includes("attorney-general") || url.includes("-us-"),
    ),
  ).toBe(false);
  const governorOrigin = origin.filter((url) => governorUrls.has(url)).length;
  await page.getByLabel("State office").selectOption("attorney-general");
  await verifyBatch(attorneyUrls);
  expect(origin.filter((url) => governorUrls.has(url)).length).toBe(
    governorOrigin,
  );
  const attorneyOrigin = origin.filter((url) => attorneyUrls.has(url)).length;
  await page.getByRole("tab", { name: "Live Elections" }).click();
  await page.getByRole("tab", { name: "State Elections" }).click();
  await expect(page.getByLabel("State office")).toHaveValue("attorney-general");
  await page.locator(`a[href="/elections/${attorneys[0].id}"]`).click();
  for (const election of attorneys) {
    await page.getByLabel("Election year").selectOption(election.id);
    await expect(
      page.getByRole("heading", {
        name: `Attorney General ${election.year}`,
        exact: true,
      }),
    ).toBeVisible();
    await expect(page.locator(".county-map path")).toHaveCount(15);
    await expect(
      page
        .getByRole("region", { name: "County results table" })
        .locator("tbody tr"),
    ).toHaveCount(15);
  }
  expect(origin.filter((url) => attorneyUrls.has(url)).length).toBe(
    attorneyOrigin,
  );
  await page
    .getByRole("navigation", { name: "Main navigation" })
    .getByRole("link", { name: "Election catalog", exact: true })
    .click();
  await page.getByRole("tab", { name: "State Elections" }).click();
  await page.locator(`a[href="/elections/${governors[0].id}"]`).click();
  for (const election of governors) {
    await page.getByLabel("Election year").selectOption(election.id);
    await expect(
      page.getByRole("heading", {
        name: `Governor ${election.year}`,
        exact: true,
      }),
    ).toBeVisible();
    await expect(page.locator(".county-map path")).toHaveCount(15);
    await expect(
      page
        .getByRole("region", { name: "County results table" })
        .locator("tbody tr"),
    ).toHaveCount(15);
  }
  expect(origin.filter((url) => governorUrls.has(url)).length).toBe(
    governorOrigin,
  );
  expect(new Set(versions.values()).size).toBe(1);
});
