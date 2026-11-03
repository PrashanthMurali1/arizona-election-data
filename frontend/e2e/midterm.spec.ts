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

  await page.unroute("**/api/midterm-2026?office=*");
  await page.unroute("**/api/midterm-2026/geography/*");
  await mockMidterm(page, counted(10));
  await page.evaluate(() => localStorage.clear());
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

  await page.unroute("**/api/midterm-2026?office=*");
  await page.route("**/api/midterm-2026?office=*", (route) =>
    route.fulfill({ status: 503, json: { detail: "down" } }),
  );
  await page.evaluate(() => localStorage.clear());
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
    await page.evaluate(() => localStorage.clear());
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
  const offices = [
    "governor",
    "attorney-general",
    "secretary-of-state",
    "us-house",
    "state-senate",
    "state-house",
  ];
  type Announcement = { revision: string; offices?: string[] };
  async function fakeStream(page: Page) {
    await page.addInitScript(() => {
      const streams: { closed: boolean; emit(value: unknown): void }[] = [];
      class FakeEventSource extends EventTarget {
        static CLOSED = 2;
        readyState = 1;
        closed = false;
        constructor(public url: string) {
          super();
          streams.push(this);
        }
        close() {
          this.closed = true;
          this.readyState = 2;
        }
        emit(value: unknown) {
          if (!this.closed)
            this.dispatchEvent(
              new MessageEvent("revision", { data: JSON.stringify(value) }),
            );
        }
      }
      Object.assign(window, {
        EventSource: FakeEventSource,
        midtermStreams: streams,
      });
    });
  }
  const announce = (page: Page, value: Announcement) =>
    page.evaluate((value) => {
      (
        window as unknown as {
          midtermStreams: { closed: boolean; emit(value: unknown): void }[];
        }
      ).midtermStreams
        .filter((source) => !source.closed)
        .forEach((source) => source.emit(value));
    }, value);
  const open = (page: Page) =>
    page.evaluate(
      () =>
        (
          window as unknown as { midtermStreams: { closed: boolean }[] }
        ).midtermStreams.filter((source) => !source.closed).length,
    );
  function body(office: string, revision = "fixture") {
    const fixture = midtermResults();
    return {
      ...fixture,
      revision,
      offices: {
        [office]: (fixture.offices as Record<string, unknown[]>)[office],
      },
    };
  }
  async function setup(
    page: Page,
    handler?: (office: string, count: number) => Promise<object> | object,
  ) {
    await fakeStream(page);
    await mockMidterm(page, midtermResults());
    const calls = new Map<string, number>();
    await page.route("**/api/midterm-2026?office=*", async (route) => {
      const office = new URL(route.request().url()).searchParams.get("office")!;
      const count = (calls.get(office) ?? 0) + 1;
      calls.set(office, count);
      await route.fulfill({
        json: handler ? await handler(office, count) : body(office),
      });
    });
    return calls;
  }
  const ready = async (page: Page, calls: Map<string, number>) => {
    await expect(
      panel(page).getByRole("heading", { name: "Statewide candidate results" }),
    ).toBeVisible();
    await expect.poll(() => calls.get("governor")).toBe(2);
    await expect
      .poll(() => offices.every((office) => calls.has(office)))
      .toBe(true);
  };

  test("shows the cache-eligible Governor response while its fresh validation is pending", async ({
    page,
  }) => {
    let release: (() => void) | undefined;
    await page.addInitScript(() => {
      const original = window.fetch;
      const modes: (RequestCache | undefined)[] = [];
      Object.assign(window, { governorFetchModes: modes });
      window.fetch = (input, options) => {
        if (String(input).includes("office=governor"))
          modes.push(options?.cache);
        return original(input, options);
      };
    });
    const calls = await setup(page, async (office, count) => {
      if (office === "governor" && count === 2)
        await new Promise<void>((resolve) => {
          release = resolve;
        });
      const fixture = body(office);
      if (office === "governor" && count === 2)
        (
          fixture.offices.governor[0] as { percent_reporting: number }
        ).percent_reporting = 55;
      return fixture;
    });
    await page.goto("/");
    await expect(
      panel(page).getByRole("heading", { name: "Statewide candidate results" }),
    ).toBeVisible();
    await expect.poll(() => typeof release).toBe("function");
    await expect(panel(page)).not.toContainText("55.00%");
    await expect.poll(() => calls.size).toBe(6);
    release!();
    await expect(panel(page)).toContainText("55.00%");
    expect(
      await page.evaluate(
        () =>
          (window as unknown as { governorFetchModes: RequestCache[] })
            .governorFetchModes,
      ),
    ).toEqual(["default", "no-cache"]);
  });

  test("shows Governor first, validates it before bounded background prefetch, and keeps visits warm", async ({
    page,
  }) => {
    const releases: (() => void)[] = [];
    let backgroundActive = 0;
    let maxBackgroundActive = 0;
    let governorCalls = 0;
    const calls = await setup(page, async (office, count) => {
      if (office === "governor") {
        governorCalls = count;
        return body(office);
      }
      expect(governorCalls).toBe(2);
      expect(
        await panel(page)
          .getByRole("heading", { name: "Statewide candidate results" })
          .isVisible(),
      ).toBe(true);
      backgroundActive++;
      maxBackgroundActive = Math.max(backgroundActive, maxBackgroundActive);
      await new Promise<void>((resolve) => releases.push(resolve));
      backgroundActive--;
      return body(office);
    });
    await page.goto("/");
    await expect.poll(() => releases.length).toBe(2);
    expect(maxBackgroundActive).toBe(2);
    expect(
      [...calls.keys()].filter((office) => office !== "governor"),
    ).toHaveLength(2);
    releases.splice(0).forEach((release) => release());
    await expect.poll(() => releases.length).toBe(2);
    releases.splice(0).forEach((release) => release());
    await expect.poll(() => releases.length).toBe(1);
    releases.splice(0).forEach((release) => release());
    await expect.poll(() => backgroundActive).toBe(0);
    expect(calls.size).toBe(6);
    expect(maxBackgroundActive).toBeLessThanOrEqual(2);
    await nav(page)
      .getByRole("button", { name: "U.S. House", exact: true })
      .click();
    await expect(
      panel(page).getByRole("heading", { name: "District by district" }),
    ).toBeVisible();
    await page.getByRole("tab", { name: "Federal Elections" }).click();
    await page.getByRole("tab", { name: "2026 Midterm Results" }).click();
    await expect(
      nav(page).getByRole("button", { name: "U.S. House", exact: true }),
    ).toHaveAttribute("aria-pressed", "true");
    await expect(
      panel(page).getByRole("heading", { name: "District by district" }),
    ).toBeVisible();
    expect(calls.get("us-house")).toBe(1);
    expect(
      await page.evaluate(() =>
        Object.keys(localStorage).filter(
          (key) =>
            key.startsWith("az-midterm-2026:v1:") &&
            key !== "az-midterm-2026:v1:selected",
        ),
      ),
    ).toEqual([]);
  });

  test("a global revision refreshes all prefetched offices and a targeted revision refreshes only named offices", async ({
    page,
  }) => {
    let revision = "fixture";
    const calls = await setup(page, (office) => body(office, revision));
    await page.goto("/");
    await ready(page, calls);
    revision = "r2";
    await announce(page, { revision });
    await expect
      .poll(() =>
        offices.every(
          (office) => calls.get(office) === (office === "governor" ? 3 : 2),
        ),
      )
      .toBe(true);
    await announce(page, { revision });
    expect(calls.get("governor")).toBe(3);
    expect(calls.get("us-house")).toBe(2);
    revision = "r3";
    await announce(page, { revision, offices: ["us-house"] });
    await expect.poll(() => calls.get("us-house")).toBe(3);
    expect(calls.get("governor")).toBe(3);
    expect(calls.get("state-house")).toBe(2);
  });

  test("an announced refresh preserves selected county details and scroll while loading", async ({
    page,
  }) => {
    let refresh = false;
    let release: (() => void) | undefined;
    const calls = await setup(page, async (office) => {
      if (refresh && office === "governor")
        await new Promise<void>((resolve) => {
          release = resolve;
        });
      const fixture = body(office, refresh ? "r2" : "fixture");
      if (office === "governor" && refresh)
        (fixture.offices.governor[0] as { id: number }).id = 999;
      return fixture;
    });
    await page.goto("/");
    await ready(page, calls);
    await panel(page)
      .getByRole("button", { name: /^Maricopa County/ })
      .press("Enter");
    const detail = panel(page).getByRole("region", {
      name: "Selected county details",
    });
    await expect(detail).toContainText("Maricopa County");
    await detail.evaluate((element) =>
      element.setAttribute("data-preserved", "yes"),
    );
    const scroll = await page.evaluate(() => {
      window.scrollTo(0, 250);
      return window.scrollY;
    });
    refresh = true;
    await announce(page, { revision: "r2", offices: ["governor"] });
    await expect.poll(() => typeof release).toBe("function");
    await expect(detail).toContainText("Maricopa County");
    expect(await page.evaluate(() => window.scrollY)).toBe(scroll);
    const response = page.waitForResponse((response) =>
      response.url().includes("office=governor"),
    );
    release!();
    await response;
    await expect(detail).toContainText("Maricopa County");
    await expect(detail).toHaveAttribute("data-preserved", "yes");
    expect(await page.evaluate(() => window.scrollY)).toBe(scroll);
  });

  test("cached results age visibly offline without stream events or a completed refresh", async ({
    page,
  }) => {
    await page.clock.install();
    const calls = await setup(page, (office, count) => {
      if (office === "governor" && count > 2)
        return new Promise<object>(() => {});
      return body(office);
    });
    await page.goto("/");
    await ready(page, calls);
    await expect(panel(page)).not.toContainText(
      "Showing the last results we loaded",
    );
    await page.context().setOffline(true);
    await page.clock.fastForward(16 * 60_000);
    await expect(panel(page)).toContainText(
      "Showing the last results we loaded",
    );
    await page.getByRole("tab", { name: "Federal Elections" }).click();
    await page.getByRole("tab", { name: "2026 Midterm Results" }).click();
    await expect(
      panel(page).getByRole("heading", { name: "Statewide candidate results" }),
    ).toBeVisible();
    await expect(panel(page)).toContainText(
      "Showing the last results we loaded",
    );
  });

  test("leaving the tab closes the stream; returning opens one and catches missed revisions", async ({
    page,
  }) => {
    let revision = "fixture";
    const calls = await setup(page, (office) => body(office, revision));
    await page.goto("/");
    await ready(page, calls);
    await expect.poll(() => open(page)).toBe(1);
    await page.getByRole("tab", { name: "Federal Elections" }).click();
    await expect.poll(() => open(page)).toBe(0);
    await page.getByRole("tab", { name: "2026 Midterm Results" }).click();
    await expect.poll(() => open(page)).toBe(1);
    revision = "r2";
    await announce(page, { revision });
    await expect.poll(() => calls.get("governor")).toBe(3);
    await expect.poll(() => calls.get("us-house")).toBe(2);
  });

  test("a failed fresh request retains results and retries on a repeated revision", async ({
    page,
  }) => {
    let failing = false;
    let revision = "fixture";
    const calls = await setup(page, (office) => {
      if (failing && office === "governor") throw Error("test offline");
      return body(office, revision);
    });
    // Override the handler to use an HTTP failure rather than an unhandled test exception.
    await page.route("**/api/midterm-2026?office=governor", async (route) => {
      calls.set("governor", (calls.get("governor") ?? 0) + 1);
      await route.fulfill(
        failing
          ? { status: 503, json: { detail: "offline" } }
          : { json: body("governor", revision) },
      );
    });
    await page.goto("/");
    await ready(page, calls);
    failing = true;
    revision = "r2";
    await announce(page, { revision, offices: ["governor"] });
    await expect(panel(page)).toContainText(
      "Showing the last results we loaded",
    );
    await expect(
      panel(page).getByRole("heading", { name: "Statewide candidate results" }),
    ).toBeVisible();
    const failedCalls = calls.get("governor")!;
    failing = false;
    await announce(page, { revision, offices: ["governor"] });
    await expect.poll(() => calls.get("governor")).toBe(failedCalls + 1);
    await expect(panel(page)).not.toContainText(
      "Showing the last results we loaded",
    );
  });

  test("the five-minute backstop revalidates Governor and prefetched offices", async ({
    page,
  }) => {
    await page.clock.install();
    const calls = await setup(page);
    await page.goto("/");
    await ready(page, calls);
    await page.clock.fastForward(5 * 60_000 + 1);
    await expect.poll(() => calls.get("governor")).toBe(3);
    await expect.poll(() => calls.get("us-house")).toBe(2);
  });
});
