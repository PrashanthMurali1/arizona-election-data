import { test, expect } from "@playwright/test";
import type { Activity, Detail, Election, Geography } from "../src/types";

// Catalog fixtures plus retained dashboard responses; no imports or source refreshes.
const offices: Record<string, string> = {
  "early-voting": "Early Voting",
  "us-senate": "U.S. Senate",
  "us-house": "U.S. House",
  governor: "Governor",
  "attorney-general": "Attorney General",
};
function election(office: string, year: number): Election {
  return {
    id: `az-${year}-${office}`,
    office_id: office,
    office: offices[office],
    year,
    date: `${year}-11-03`,
    kind: "general",
    status: office === "early-voting" ? "pre_results" : "verified",
    notes: "Catalog test fixture",
    county_count: 15,
    candidate_count: 3,
    boundary_id: "fixture-boundary",
    ...(office === "us-house" ? { district_count: 9 } : {}),
  };
}
const elections = [
  election("early-voting", 2026),
  election("governor", 2018),
  election("us-senate", 2018),
  election("attorney-general", 2022),
  election("us-house", 2024),
  election("governor", 2022),
  election("us-senate", 2024),
  election("us-house", 2022),
];
const categories = [
  { name: "Live Elections", ids: [] },
  {
    name: "Federal Elections",
    ids: [
      "az-2024-us-senate",
      "az-2018-us-senate",
      "az-2024-us-house",
      "az-2022-us-house",
    ],
  },
  {
    name: "State Elections",
    ids: ["az-2022-governor", "az-2018-governor", "az-2022-attorney-general"],
  },
];

let dashboard: {
  detail: Detail;
  geography: Geography;
  activity: Activity;
};

test.beforeAll(async ({ request }) => {
  const load = async (path: string) => {
    const response = await request.get(path);
    expect(response.ok()).toBeTruthy();
    return response.json();
  };
  const detail = await load("/api/elections/az-2026-early-voting");
  elections[0].boundary_id = detail.election.boundary_id;
  dashboard = {
    detail,
    geography: await load(`/api/geography/${detail.election.boundary_id}`),
    activity: await load("/api/elections/az-2026-early-voting/activity"),
  };
});

test.beforeEach(async ({ page }) => {
  await page.addInitScript(() => {
    const streams: EventSource[] = [];
    class FakeEventSource extends EventTarget {
      closed = false;
      constructor(public url: string) {
        super();
        streams.push(this as unknown as EventSource);
      }
      close() {
        this.closed = true;
      }
      emit(event: string, revision?: string) {
        if (!this.closed)
          this.dispatchEvent(
            event === "revision"
              ? new MessageEvent(event, { data: JSON.stringify({ revision }) })
              : new Event(event),
          );
      }
    }
    Object.assign(window, {
      EventSource: FakeEventSource,
      catalogStreams: streams,
    });
  });
  await page.route("**/api/elections/az-2026-early-voting/activity", (route) =>
    route.fulfill({ json: dashboard.activity }),
  );
  await page.route(
    `**/api/geography/${dashboard.detail.election.boundary_id}`,
    (route) => route.fulfill({ json: dashboard.geography }),
  );
  await page.route("**/api/elections", (route) =>
    route.fulfill({ json: elections }),
  );
});

for (const width of [1440, 390, 320]) {
  test(`catalog tabs classify cards, retain links and fit at ${width}px`, async ({
    page,
  }) => {
    await page.setViewportSize({ width, height: 1000 });
    const errors: string[] = [];
    page.on("pageerror", (error) => errors.push(error.message));
    await page.goto("/");
    await expect(page.getByRole("heading", { level: 1 })).toHaveText(
      "Every county.Every vote, in context.",
    );
    const tabs = page.getByRole("tablist", { name: "Election categories" });
    await expect(tabs.getByRole("tab")).toHaveText(
      categories.map((c) => c.name),
    );
    await expect(tabs.getByRole("tab", { selected: true })).toHaveText(
      "Live Elections",
    );
    await expect(
      page.getByRole("heading", {
        name: "2026 Early Voting",
        exact: true,
        level: 3,
      }),
    ).toBeVisible();
    await expect(page.locator(".breadcrumbs")).toHaveCount(0);
    await expect(page.getByLabel("Election year")).toHaveCount(0);
    await expect(page.getByRole("heading", { level: 1 })).toHaveCount(1);

    for (const category of categories) {
      const tab = tabs.getByRole("tab", { name: category.name });
      await tab.click();
      await expect(tab).toHaveAttribute("aria-selected", "true");
      await expect(tab).toHaveAttribute("tabindex", "0");
      await expect(page.getByRole("tabpanel")).toHaveCount(1);
      const panel = page.getByRole("tabpanel", { name: category.name });
      await expect(panel).toHaveAttribute(
        "id",
        (await tab.getAttribute("aria-controls"))!,
      );
      await expect(panel).toHaveAttribute(
        "aria-labelledby",
        (await tab.getAttribute("id"))!,
      );
      await expect(panel.locator(".election-card")).toHaveCount(
        category.ids.length,
      );
      expect(
        await panel
          .locator(".election-card")
          .evaluateAll((cards) =>
            cards.map((card) => card.getAttribute("href")),
          ),
      ).toEqual(category.ids.map((id) => `/elections/${id}`));
      await expect(page.locator(".election-card")).toHaveCount(
        category.ids.length,
      );
      if (category.name === "Live Elections") {
        await expect(panel.locator(".county-map path")).toHaveCount(15);
        await expect(
          panel
            .getByRole("region", { name: "County participation table" })
            .locator("tbody tr"),
        ).toHaveCount(15);
        await panel
          .getByRole("button", {
            name: "Pima County. View early-voting activity.",
          })
          .click();
        await expect(
          panel.getByRole("heading", { name: "Pima County", exact: true }),
        ).toBeVisible();
        await expect(panel.locator(".sources")).toContainText(
          "statewide provider party breakdown",
        );
      }
      if (category.name !== "Live Elections") {
        await expect(
          page.getByRole("link", { name: "2026 Early Voting", exact: true }),
        ).toHaveCount(0);
      }
      expect(
        await page.evaluate(() => document.documentElement.scrollWidth),
      ).toBeLessThanOrEqual(width);
      for (const button of await tabs.getByRole("tab").all()) {
        const box = await button.boundingBox();
        expect(box!.x).toBeGreaterThanOrEqual(0);
        expect(box!.x + box!.width).toBeLessThanOrEqual(width);
        expect(box!.height).toBeGreaterThanOrEqual(44);
      }
      await panel.scrollIntoViewIfNeeded();
      await page.screenshot({
        path: `test-results/catalog-${width}-${category.name.split(" ")[0].toLowerCase()}.png`,
        fullPage: true,
      });
    }
    await page.getByRole("tabpanel").locator(".election-card").first().click();
    await expect(page).toHaveURL(/\/elections\/az-2022-governor$/);
    expect(errors).toEqual([]);
  });
}

test("tabs support roving focus, arrow wraparound, Home/End and panel focus", async ({
  page,
}) => {
  await page.goto("/");
  const tabs = page.getByRole("tab");
  await tabs.first().focus();
  for (const [key, name] of [
    ["ArrowRight", "Federal Elections"],
    ["ArrowRight", "State Elections"],
    ["ArrowRight", "Live Elections"],
    ["ArrowLeft", "State Elections"],
    ["Home", "Live Elections"],
    ["End", "State Elections"],
  ]) {
    await page.keyboard.press(key);
    const active = page.getByRole("tab", { name });
    await expect(active).toBeFocused();
    await expect(active).toHaveAttribute("aria-selected", "true");
    await expect(page.getByRole("tab", { selected: false })).toHaveCount(2);
    for (const inactive of await page
      .getByRole("tab", { selected: false })
      .all()) {
      await expect(inactive).toHaveAttribute("tabindex", "-1");
    }
    const outline = await active.evaluate((element) => {
      const style = getComputedStyle(element);
      return { width: style.outlineWidth, style: style.outlineStyle };
    });
    expect(outline.width).toBe("3px");
    expect(outline.style).toBe("solid");
  }
  await page.keyboard.press("Tab");
  await expect(
    page.getByRole("tabpanel", { name: "State Elections" }),
  ).toBeFocused();
  await page.keyboard.press("Tab");
  await expect(
    page.locator('a[href="/elections/az-2022-governor"]'),
  ).toBeFocused();
});

test("empty category retains tabs and gives a useful empty state", async ({
  page,
}) => {
  await page.route("**/api/elections", (route) =>
    route.fulfill({ json: [election("governor", 2022)] }),
  );
  await page.goto("/");
  await expect(
    page.getByRole("tabpanel", { name: "Live Elections" }),
  ).toContainText("No elections available in this category yet.");
  await page.getByRole("tab", { name: "Federal Elections" }).click();
  await expect(
    page.getByRole("tabpanel", { name: "Federal Elections" }),
  ).toContainText("No elections available in this category yet.");
  await page.getByRole("tab", { name: "State Elections" }).click();
  await expect(page.locator(".election-card")).toHaveCount(1);
});

type InstrumentedWindow = typeof window & {
  catalogStreams: {
    closed: boolean;
    emit: (event: string, revision?: string) => void;
  }[];
};
const streamCount = (page: import("@playwright/test").Page) =>
  page.evaluate(
    () =>
      (window as InstrumentedWindow).catalogStreams.filter(
        (source) => !source.closed,
      ).length,
  );
const emitRevision = (
  page: import("@playwright/test").Page,
  revision: string,
) =>
  page.evaluate((value) => {
    (window as InstrumentedWindow).catalogStreams
      .filter((source) => !source.closed)
      .forEach((source) => source.emit("revision", value));
  }, revision);

test("embedded live updates coalesce, preserve county selection, abort on exit and reload on return", async ({
  page,
}) => {
  let requests = 0;
  let revision = "initial";
  let delta = 0;
  let hold: Promise<void> | null = null;
  const original = dashboard.activity.statewide.metrics.find(
    (metric) => metric.key === "ballots_received",
  )!.value!;
  await page.route(
    "**/api/elections/az-2026-early-voting/activity",
    async (route) => {
      requests++;
      const data = structuredClone(dashboard.activity);
      data.revision = revision;
      data.statewide.metrics.find(
        (metric) => metric.key === "ballots_received",
      )!.value = original + delta;
      if (hold) await hold;
      await route.fulfill({ json: data });
    },
  );
  await page.goto("/");
  const state = page.getByRole("region", {
    name: "Statewide participation availability",
  });
  const table = page.getByRole("region", {
    name: "County participation table",
  });
  await expect.poll(() => streamCount(page)).toBe(1);
  expect(requests).toBe(1);
  await emitRevision(page, revision);
  expect(requests).toBe(1);
  await page
    .getByRole("button", { name: "Pima County. View early-voting activity." })
    .click();
  await table.getByRole("button", { name: "Returned", exact: false }).click();

  revision = "committed-1";
  delta = 10;
  let release = () => {};
  hold = new Promise<void>((resolve) => {
    release = resolve;
  });
  await emitRevision(page, revision);
  await expect.poll(() => requests).toBe(2);
  await emitRevision(page, revision);
  await emitRevision(page, revision);
  expect(requests).toBe(2);
  hold = null;
  release();
  await expect(state).toContainText((original + 10).toLocaleString("en-US"));
  await expect(
    page.getByRole("heading", { name: "Pima County", exact: true }),
  ).toBeVisible();
  await expect(table.locator('th[aria-sort="ascending"]')).toContainText(
    "Returned",
  );

  revision = "committed-2";
  delta = 20;
  hold = new Promise<void>((resolve) => {
    release = resolve;
  });
  const canceled = page.waitForEvent("requestfailed", (request) =>
    request.url().endsWith("/az-2026-early-voting/activity"),
  );
  await emitRevision(page, revision);
  await expect.poll(() => requests).toBe(3);
  await page.getByRole("tab", { name: "Federal Elections" }).click();
  await canceled;
  await expect.poll(() => streamCount(page)).toBe(0);
  await expect(
    page.getByRole("region", { name: "County participation table" }),
  ).toHaveCount(0);
  await page.evaluate(() =>
    document.dispatchEvent(new Event("visibilitychange")),
  );
  expect(requests).toBe(3);
  hold = null;
  release();

  await page.getByRole("tab", { name: "Live Elections" }).click();
  await expect.poll(() => streamCount(page)).toBe(1);
  await emitRevision(page, revision);
  await expect(state).toContainText((original + 20).toLocaleString("en-US"));
  await expect.poll(() => streamCount(page)).toBe(1);
  expect(requests).toBe(4);
  await emitRevision(page, revision);
  expect(requests).toBe(4);
  for (let index = 0; index < 2; index++) {
    await page.getByRole("tab", { name: "State Elections" }).click();
    await expect.poll(() => streamCount(page)).toBe(0);
    await page.getByRole("tab", { name: "Live Elections" }).click();
    await expect.poll(() => streamCount(page)).toBe(1);
  }
  expect(requests).toBe(4);
});

test("removed Early Voting and legacy office browser URLs show the normal not-found page", async ({
  page,
}) => {
  for (const id of [
    "az-2026-early-voting",
    "az-2026-governor",
    "az-2026-attorney-general",
  ]) {
    let requests = 0;
    page.on("request", (request) => {
      if (request.url().includes("/api/")) requests++;
    });
    await page.goto(`/elections/${id}`);
    await expect(
      page.getByRole("heading", { name: "Page not found", exact: true }),
    ).toBeVisible();
    await expect(page).toHaveURL(new RegExp(`/elections/${id}$`));
    await expect(
      page.getByRole("link", { name: "Back to the catalog" }),
    ).toBeVisible();
    await expect(
      page.getByRole("region", { name: "County participation table" }),
    ).toHaveCount(0);
    expect(requests).toBe(0);
  }
});

test("embedded loading and API errors stay inside Live Elections and other tabs remain usable", async ({
  page,
}) => {
  let release = () => {};
  const hold = new Promise<void>((resolve) => {
    release = resolve;
  });
  await page.route(
    "**/api/elections/az-2026-early-voting/activity",
    async (route) => {
      await hold;
      await route.fulfill({
        status: 503,
        json: { error: "Synthetic preview failure" },
      });
    },
  );
  await page.goto("/");
  const panel = page.getByRole("tabpanel", { name: "Live Elections" });
  await expect(panel).toContainText("Loading");
  await expect(
    page.getByRole("heading", { name: "Election catalog", exact: true }),
  ).toBeVisible();
  release();
  await expect(panel.getByRole("alert")).toContainText("503");
  await expect.poll(() => streamCount(page)).toBe(1);
  await page.getByRole("tab", { name: "Federal Elections" }).click();
  await expect(page.locator(".election-card")).toHaveCount(4);
  await expect.poll(() => streamCount(page)).toBe(0);
});

test("fresh activity and geography are reused across tab visits; API revalidates after five minutes", async ({
  page,
}) => {
  await page.clock.install();
  let requests = 0;
  let geography = 0;
  await page.route(
    "**/api/elections/az-2026-early-voting/activity",
    (route) => {
      requests++;
      return route.fulfill({ json: dashboard.activity });
    },
  );
  await page.route(
    `**/api/geography/${dashboard.detail.election.boundary_id}`,
    (route) => {
      geography++;
      return route.fulfill({ json: dashboard.geography });
    },
  );
  await page.goto("/");
  await expect(
    page.getByRole("heading", { name: "2026 Early Voting", exact: true }),
  ).toBeVisible();
  await emitRevision(page, dashboard.activity.revision!);
  expect(requests).toBe(1);
  expect(geography).toBe(1);
  await page.getByRole("tab", { name: "Federal Elections" }).click();
  await expect.poll(() => streamCount(page)).toBe(0);
  await page.getByRole("tab", { name: "Live Elections" }).click();
  await expect(
    page.getByRole("region", { name: "County participation table" }),
  ).toBeVisible();
  await expect.poll(() => streamCount(page)).toBe(1);
  await emitRevision(page, dashboard.activity.revision!);
  expect(requests).toBe(1);
  expect(geography).toBe(1);
  await page.clock.fastForward(5 * 60_000 + 1);
  await expect.poll(() => requests).toBe(2);
  expect(geography).toBe(1);
});

test("inactive activity expires after thirty minutes and geography expires after a day", async ({
  page,
}) => {
  await page.clock.install();
  let requests = 0;
  let geography = 0;
  await page.route(
    "**/api/elections/az-2026-early-voting/activity",
    (route) => {
      requests++;
      return route.fulfill({ json: dashboard.activity });
    },
  );
  await page.route(
    `**/api/geography/${dashboard.detail.election.boundary_id}`,
    (route) => {
      geography++;
      return route.fulfill({ json: dashboard.geography });
    },
  );
  await page.goto("/");
  await expect(
    page.getByRole("heading", { name: "2026 Early Voting", exact: true }),
  ).toBeVisible();
  await page.getByRole("tab", { name: "State Elections" }).click();
  await page.clock.fastForward(31 * 60_000);
  await page.getByRole("tab", { name: "Live Elections" }).click();
  await expect(
    page.getByRole("heading", { name: "2026 Early Voting", exact: true }),
  ).toBeVisible();
  expect(requests).toBe(2);
  expect(geography).toBe(1);
  await page.getByRole("tab", { name: "State Elections" }).click();
  await page.clock.fastForward(24 * 60 * 60_000);
  await page.getByRole("tab", { name: "Live Elections" }).click();
  await expect(
    page.getByRole("heading", { name: "2026 Early Voting", exact: true }),
  ).toBeVisible();
  expect(requests).toBe(3);
  expect(geography).toBe(2);
});

test("stale source flags update with no revision change or additional API request", async ({
  page,
}) => {
  const now = new Date("2026-10-29T08:00:00Z");
  await page.clock.install({ time: now });
  const activity = structuredClone(dashboard.activity);
  const retrieved = new Date(
    now.getTime() - 12 * 60 * 60_000 + 30_000,
  ).toISOString();
  activity.stale = false;
  activity.failures = [];
  for (const release of activity.releases)
    Object.assign(release, {
      stale: false,
      error: null,
      retrieved_at: retrieved,
    });
  for (const row of [activity.statewide, ...activity.counties]) {
    for (const metric of row.metrics)
      Object.assign(metric, { stale: false, retrieved_at: retrieved });
  }
  let requests = 0;
  await page.route(
    "**/api/elections/az-2026-early-voting/activity",
    (route) => {
      requests++;
      return route.fulfill({ json: activity });
    },
  );
  await page.goto("/");
  await expect(
    page.getByRole("heading", { name: "2026 Early Voting", exact: true }),
  ).toBeVisible();
  await emitRevision(page, activity.revision!);
  await expect(page.locator(".sources")).not.toContainText(
    "Early-voting data may be outdated",
  );
  await page
    .getByRole("button", { name: "Pima County. View early-voting activity." })
    .click();
  await page.clock.fastForward(60_000);
  await expect(page.locator(".sources")).toContainText(
    "Early-voting data may be outdated",
  );
  await expect(
    page.getByRole("region", { name: "Selected county details" }),
  ).toContainText("Stale");
  expect(requests).toBe(1);
});

test("hidden and offline reconnects recover missed revisions without refetching geography", async ({
  page,
  context,
}) => {
  let revision = "initial";
  let requests = 0;
  await page.route(
    "**/api/elections/az-2026-early-voting/activity",
    (route) => {
      requests++;
      return route.fulfill({ json: { ...dashboard.activity, revision } });
    },
  );
  await page.goto("/");
  await expect.poll(() => streamCount(page)).toBe(1);
  await emitRevision(page, revision);
  await page.evaluate(() => {
    Object.defineProperty(document, "visibilityState", {
      configurable: true,
      get: () => "hidden",
    });
    document.dispatchEvent(new Event("visibilitychange"));
  });
  await expect.poll(() => streamCount(page)).toBe(0);
  revision = "missed-while-hidden";
  await page.evaluate(() => {
    Object.defineProperty(document, "visibilityState", {
      configurable: true,
      get: () => "visible",
    });
    document.dispatchEvent(new Event("visibilitychange"));
  });
  await expect.poll(() => streamCount(page)).toBe(1);
  await emitRevision(page, revision);
  await expect.poll(() => requests).toBe(2);
  await expect(
    page.getByRole("status").filter({ hasText: "Checking for updates" }),
  ).toHaveCount(0);
  await context.setOffline(true);
  await page.evaluate(() =>
    (window as InstrumentedWindow).catalogStreams
      .filter((s) => !s.closed)
      .forEach((s) => s.emit("error")),
  );
  await expect(page.locator(".sources")).toContainText(
    "Update connection interrupted",
  );
  revision = "missed-while-offline";
  await context.setOffline(false);
  await expect.poll(() => streamCount(page)).toBe(1);
  await emitRevision(page, revision);
  await expect.poll(() => requests).toBe(3);
  await expect(page.locator(".sources")).not.toContainText(
    "Update connection interrupted",
  );
});

test("cached data revalidates if the initial SSE revision is unavailable", async ({
  page,
}) => {
  await page.clock.install();
  let requests = 0;
  await page.route(
    "**/api/elections/az-2026-early-voting/activity",
    (route) => {
      requests++;
      return route.fulfill({ json: dashboard.activity });
    },
  );
  await page.goto("/");
  await expect(
    page.getByRole("heading", { name: "2026 Early Voting", exact: true }),
  ).toBeVisible();
  await page.getByRole("tab", { name: "Federal Elections" }).click();
  await page.getByRole("tab", { name: "Live Elections" }).click();
  await expect.poll(() => streamCount(page)).toBe(1);
  expect(requests).toBe(1);
  await page.clock.fastForward(5_000);
  await expect.poll(() => requests).toBe(2);
  await expect(
    page.getByRole("status").filter({ hasText: "Checking for updates" }),
  ).toHaveCount(0);
});
