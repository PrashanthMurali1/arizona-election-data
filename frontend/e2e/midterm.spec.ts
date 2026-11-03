import { expect, test, type Page } from "@playwright/test";
import {
  candidate,
  countyRow,
  midtermResults,
  mockMidterm,
  race,
} from "./helpers";

const panel = (page: Page) =>
  page.getByRole("tabpanel", { name: "2026 Midterm Results" });
const nav = (page: Page) =>
  panel(page).getByRole("navigation", { name: "Midterm office directory" });

test("opens on Governor results with a grey county map and table, no extra click", async ({
  page,
}) => {
  await mockMidterm(page, midtermResults());
  await page.goto("/");
  await expect(page.getByRole("tab", { selected: true })).toHaveText(
    "2026 Midterm Results",
  );
  await expect(
    nav(page).getByRole("button", { name: "Governor", exact: true }),
  ).toHaveAttribute("aria-pressed", "true");
  const p = panel(page);
  await expect(
    p.getByRole("heading", { name: "Governor", level: 2 }),
  ).toBeVisible();
  await expect(
    p.getByRole("heading", { name: "Statewide candidate results" }),
  ).toBeVisible();
  await expect(p.getByText("0.00%").first()).toBeVisible();
  await expect(p.getByText("Unofficial results").first()).toBeVisible();
  // Map is present and every county is grey (no leader) until votes arrive.
  const maricopa = p.getByRole("button", { name: /^Maricopa County/ });
  await expect(maricopa).toHaveClass(/other/);
  await expect(maricopa).not.toHaveClass(/\bdem\b/);
  await expect(
    p.getByRole("region", { name: "County results table" }),
  ).toContainText("Maricopa");
  // No list of races to click through, and no separate race page.
  await expect(p.locator(".archive-row")).toHaveCount(0);
  await maricopa.press("Enter");
  await expect(
    p.getByRole("region", { name: "Selected county details" }),
  ).toContainText("Maricopa County");
});

test("every office shows its results as soon as it is selected", async ({
  page,
}) => {
  await mockMidterm(page, midtermResults());
  await page.goto("/");
  const p = panel(page);
  for (const label of ["Attorney General", "Secretary of State"]) {
    await nav(page).getByRole("button", { name: label, exact: true }).click();
    await expect(
      p.getByRole("heading", { name: label, level: 2, exact: true }),
    ).toBeVisible();
    await expect(
      p.getByRole("heading", { name: "Statewide candidate results" }),
    ).toBeVisible();
  }
});

for (const [label, seats] of [
  ["U.S. House", null],
  ["State Senate", "14 of 30 seats"],
  ["State House", "28 of 60 seats"],
] as const) {
  test(`${label}: every district on one map and one table`, async ({
    page,
  }) => {
    await mockMidterm(page, midtermResults());
    await page.goto("/");
    const p = panel(page);
    await nav(page).getByRole("button", { name: label, exact: true }).click();
    await expect(
      p.getByRole("heading", { name: label, level: 2, exact: true }),
    ).toBeVisible();
    await expect(
      p.getByRole("heading", { name: "District by district" }),
    ).toBeVisible();
    const table = p.getByRole("region", { name: "District results table" });
    await expect(table.locator("tbody tr")).toHaveCount(3);
    await expect(p.locator(".county-map path").first()).toBeVisible();
    if (seats) await expect(p.getByText(seats)).toBeVisible();
    // The first district is already shown at the top; selecting another swaps it in.
    await expect(
      p.getByRole("heading", { name: "District 1 · Candidate results" }),
    ).toBeVisible();
    await table.getByRole("button", { name: /^District 2/ }).click();
    await expect(
      p.getByRole("heading", { name: "District 2 · Candidate results" }),
    ).toBeVisible();
    await expect(p.locator(".archive-row")).toHaveCount(0);
  });
}

test("districts and counties turn from grey to the leading party as votes arrive", async ({
  page,
}) => {
  const counted = (votes: number) =>
    midtermResults({
      governor: [
        race(1, "Arizona Governor", null, {
          total_votes: votes,
          counties: [
            countyRow("04013", "Maricopa", votes),
            countyRow("04019", "Pima"),
          ],
          candidates: [
            candidate("Katie Hobbs", "Democratic", votes, 100),
            candidate("Andy Biggs", "Republican", 0, 0),
          ],
        }),
      ],
      "state-house": [
        race(31, "Arizona State House 1", 1, {
          total_votes: votes,
          candidates: [
            candidate("Zed", "Republican", votes, 100),
            candidate("Amy", "Democratic", 0, 0),
          ],
        }),
      ],
    });
  await mockMidterm(page, counted(0));
  await page.goto("/");
  await expect(
    page.getByRole("button", { name: /^Maricopa County/ }),
  ).toHaveClass(/other/);

  await page.unroute("**/api/midterm-2026");
  await page.unroute("**/api/midterm-2026/geography/*");
  await mockMidterm(page, counted(10));
  await page.reload();
  await expect(
    page.getByRole("button", { name: /^Maricopa County/ }),
  ).toHaveClass(/\bdem\b/);
  await expect(page.getByRole("button", { name: /^Pima County/ })).toHaveClass(
    /other/,
  );
  await nav(page)
    .getByRole("button", { name: "State House", exact: true })
    .click();
  await expect(
    panel(page).getByRole("button", { name: /^District 1,/ }),
  ).toHaveClass(/\brep\b/);
});

test("a failed refresh keeps the last results and warns; a cold failure shows an error", async ({
  page,
}) => {
  await mockMidterm(page, {
    ...midtermResults(),
    stale: true,
    refresh_error: "Timeout: down",
  });
  await page.goto("/");
  await expect(panel(page)).toContainText("Showing the last results we loaded");
  await expect(
    panel(page).getByRole("heading", { name: "Statewide candidate results" }),
  ).toBeVisible();

  await page.unroute("**/api/midterm-2026");
  await page.route("**/api/midterm-2026", (route) =>
    route.fulfill({ status: 503, json: { detail: "down" } }),
  );
  await page.reload();
  await expect(page.getByRole("alert")).toContainText(
    "Data couldn’t be loaded",
  );
  await page.getByRole("tab", { name: "Federal Elections" }).click();
  await expect(
    page.getByRole("tab", { name: "Federal Elections", selected: true }),
  ).toBeVisible();
});

test("midterm tab fits narrow screens and works through the mobile office picker", async ({
  page,
}) => {
  await mockMidterm(page, midtermResults());
  for (const width of [390, 320]) {
    await page.setViewportSize({ width, height: 900 });
    await page.goto("/");
    const p = panel(page);
    await expect(
      p.getByRole("heading", { name: "Statewide candidate results" }),
    ).toBeVisible();
    await p
      .getByLabel("Midterm office", { exact: true })
      .selectOption("state-house");
    await expect(
      p.getByRole("heading", { name: "District by district" }),
    ).toBeVisible();
    expect(
      await page.evaluate(() => document.documentElement.scrollWidth),
    ).toBeLessThanOrEqual(width);
  }
});

test("midterm cards show % reporting instead of turnout; tables show Dem %, Rep %, leader and Reporting %", async ({
  page,
}) => {
  const reporting = midtermResults({
    governor: [
      race(1, "Arizona Governor", null, {
        percent_reporting: 41,
        total_votes: 100,
        counties: [
          { ...countyRow("04013", "Maricopa", 100), percent_reporting: 62.5 },
          countyRow("04019", "Pima"),
        ],
        candidates: [
          candidate("Katie Hobbs", "Democratic", 60, 60),
          candidate("Andy Biggs", "Republican", 40, 40),
        ],
      }),
    ],
    "us-house": [1, 2, 3].map((n) =>
      race(10 + n, `Arizona US House ${n}`, n, { percent_reporting: n * 10 }),
    ),
  });
  await mockMidterm(page, reporting);
  await page.goto("/");
  const p = panel(page);
  const summary = p.getByRole("region", { name: "Candidate results" });
  await expect(summary).toContainText("% Reporting");
  await expect(summary).toContainText("41.00%");
  await expect(summary).not.toContainText("turnout");
  const headers = p
    .getByRole("region", { name: "County results table" })
    .locator("thead th");
  await expect(headers).toHaveText([
    /County/,
    /Dem %/,
    /Rep %/,
    /Current leader/,
    /Reporting %/,
  ]);
  await expect(
    p.getByRole("region", { name: "County results table" }),
  ).toContainText("62.50%");
  await expect(
    p.getByRole("region", { name: "County results table" }),
  ).not.toContainText("Turnout");

  await nav(page)
    .getByRole("button", { name: "U.S. House", exact: true })
    .click();
  await expect(
    p.getByRole("region", { name: "Candidate results" }),
  ).toContainText("10.00%");
  await expect(
    p
      .getByRole("region", { name: "District results table" })
      .locator("thead th"),
  ).toHaveText([/District/, /Dem %/, /Rep %/, /Current leader/, /Reporting %/]);
});

test("no Reporting % column or value when the API does not return it", async ({
  page,
}) => {
  const none = midtermResults({
    governor: [
      race(1, "Arizona Governor", null, {
        percent_reporting: null,
        counties: [
          { ...countyRow("04013", "Maricopa"), percent_reporting: null },
          { ...countyRow("04019", "Pima"), percent_reporting: null },
        ],
      }),
    ],
  });
  await mockMidterm(page, none);
  await page.goto("/");
  const p = panel(page);
  await expect(
    p.getByRole("region", { name: "County results table" }).locator("thead th"),
  ).toHaveText([/County/, /Dem %/, /Rep %/, /Current leader/]);
  await expect(
    p.getByRole("region", { name: "Candidate results" }),
  ).toContainText("% Reporting");
  await expect(
    p.getByRole("region", { name: "Candidate results" }),
  ).toContainText("N/A");
});

test.describe("update notifications and caching", () => {
  async function fakeStream(page: Page) {
    await page.addInitScript(() => {
      const streams: { url: string; closed: boolean; emit(r: string): void }[] =
        [];
      class FakeEventSource extends EventTarget {
        closed = false;
        constructor(public url: string) {
          super();
          streams.push(this);
        }
        close() {
          this.closed = true;
        }
        emit(revision: string) {
          if (!this.closed)
            this.dispatchEvent(
              new MessageEvent("revision", {
                data: JSON.stringify({ revision }),
              }),
            );
        }
      }
      Object.assign(window, {
        EventSource: FakeEventSource,
        midtermStreams: streams,
      });
    });
  }
  const announce = (page: Page, revision: string) =>
    page.evaluate((value) => {
      (
        window as unknown as {
          midtermStreams: { closed: boolean; emit(r: string): void }[];
        }
      ).midtermStreams
        .filter((s) => !s.closed)
        .forEach((s) => s.emit(value));
    }, revision);
  const open = (page: Page) =>
    page.evaluate(
      () =>
        (
          window as unknown as { midtermStreams: { closed: boolean }[] }
        ).midtermStreams.filter((s) => !s.closed).length,
    );

  test("a new revision refetches past the cache; the same revision and duplicates do not; no polling", async ({
    page,
  }) => {
    await fakeStream(page);
    const requests: (string | undefined)[] = [];
    const updated = {
      ...midtermResults({
        governor: [
          race(1, "Arizona Governor", null, {
            percent_reporting: 55,
            total_votes: 10,
            candidates: [
              candidate("Katie Hobbs", "Democratic", 6, 60),
              candidate("Andy Biggs", "Republican", 4, 40),
            ],
          }),
        ],
      }),
      revision: "r2",
    };
    await page.clock.install();
    await page.route("**/api/midterm-2026", async (route) => {
      requests.push(
        (await route.request().headerValue("cache-control")) ?? undefined,
      );
      await route.fulfill({
        json: requests.length === 1 ? midtermResults() : updated,
      });
    });
    await page.goto("/");
    const p = panel(page);
    await expect(p.getByText("% Reporting")).toBeVisible();
    await expect.poll(() => open(page)).toBe(1);
    // The page announces the revision it already shows: nothing to fetch.
    await announce(page, "fixture");
    // Hours pass with no timer-driven requests.
    await page.clock.fastForward(3 * 60 * 60_000);
    expect(requests).toHaveLength(1);
    // The job publishes: one refetch, then the new figures are shown.
    await announce(page, "r2");
    await expect(p).toContainText("55.00%");
    expect(requests).toHaveLength(2);
    await announce(page, "r2");
    await announce(page, "r2");
    expect(requests).toHaveLength(2);
  });

  test("leaving the tab closes the stream; returning opens one and catches a missed revision", async ({
    page,
  }) => {
    await fakeStream(page);
    let calls = 0;
    await page.route("**/api/midterm-2026", (route) =>
      route.fulfill({
        json:
          ++calls === 1
            ? midtermResults()
            : { ...midtermResults(), revision: "r2" },
      }),
    );
    await page.goto("/");
    await expect.poll(() => open(page)).toBe(1);
    await page.getByRole("tab", { name: "Federal Elections" }).click();
    await expect.poll(() => open(page)).toBe(0);
    await page.getByRole("tab", { name: "2026 Midterm Results" }).click();
    await expect.poll(() => open(page)).toBe(1);
    // The new stream's first event announces the revision published while away.
    await announce(page, "r2");
    await expect.poll(() => calls).toBeGreaterThanOrEqual(2);
  });

  test("a failed refetch is retried when the same revision is announced again", async ({
    page,
  }) => {
    await fakeStream(page);
    let calls = 0;
    let failing = false;
    const updated = { ...midtermResults(), revision: "r2" };
    await page.route("**/api/midterm-2026", (route) => {
      calls++;
      if (failing) return route.fulfill({ status: 503, json: { detail: "x" } });
      return route.fulfill({
        json: calls === 1 ? midtermResults() : updated,
      });
    });
    await page.goto("/");
    await expect.poll(() => open(page)).toBe(1);
    await expect(panel(page).getByText("% Reporting")).toBeVisible();
    failing = true;
    await announce(page, "r2");
    await expect(panel(page)).toContainText(
      "Showing the last results we loaded",
    );
    const failedCalls = calls;
    await announce(page, "r2"); // the stream reconnected and announced the revision again
    await expect.poll(() => calls).toBe(failedCalls + 1);
    failing = false;
    await announce(page, "r2");
    await expect(panel(page)).not.toContainText(
      "Showing the last results we loaded",
    );
  });

  test("degraded (live or stale) results are rechecked every five minutes; healthy ones are not", async ({
    page,
  }) => {
    await fakeStream(page);
    await page.clock.install();
    let calls = 0;
    await page.route("**/api/midterm-2026", (route) => {
      calls++;
      return route.fulfill({
        json: {
          ...midtermResults(),
          revision: calls < 3 ? "live" : "snapshot-1",
        },
      });
    });
    await page.goto("/");
    await expect(panel(page).getByText("% Reporting")).toBeVisible();
    expect(calls).toBe(1);
    await page.clock.fastForward(5 * 60_000 + 1);
    await expect.poll(() => calls).toBe(2);
    await page.clock.fastForward(5 * 60_000 + 1);
    await expect.poll(() => calls).toBe(3); // now a real snapshot: back to the long backstop
    await page.clock.fastForward(30 * 60_000);
    expect(calls).toBe(3);
  });
});
