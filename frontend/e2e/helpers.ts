import { expect, test as base, type Page } from "@playwright/test";

const officeNames: Record<string, string> = {
  "us-senate": "U.S. Senate",
  "us-house": "U.S. House",
  governor: "Governor",
  "attorney-general": "Attorney General",
};

export async function selectOffice(page: Page, label: string, value: string) {
  const select = page.getByLabel(label, { exact: true });
  if (await select.isVisible()) await select.selectOption(value);
  else
    await page
      .getByRole("navigation", { name: "Office directory" })
      .getByRole("button", { name: officeNames[value], exact: true })
      .click();
  await expect(select).toHaveValue(value);
}

export async function expectCandidateCount(page: Page, count: number) {
  const summary = page.locator(".statewide");
  const roster = summary.locator("details.roster");
  if (
    (await roster.count()) &&
    !(await roster.evaluate((el) => (el as HTMLDetailsElement).open))
  )
    await roster.locator("summary").click();
  const rows = summary.locator(".lead-candidate, .candidate-row");
  await expect(rows).toHaveCount(count);
  for (const row of await rows.all()) await expect(row).toBeVisible();
}

// Catalog sizes grow with every data release, so specs read them from the API under test
// instead of hard-coding a number that breaks the deploy's test phase on the next import.
export async function catalogCount(page: Page, officeId: string) {
  const elections: { office_id: string }[] = await (
    await page.request.get("/api/elections")
  ).json();
  return elections.filter((e) => e.office_id === officeId).length;
}

// Shared 2026 midterm API fixture so specs never depend on civicAPI being reachable.
export const candidate = (
  name: string,
  party: string,
  votes: number,
  percent: number,
  extra: object = {},
) => ({
  name,
  party,
  color: null,
  votes,
  percent,
  winner: false,
  seats: null,
  ...extra,
});
export const race = (
  id: number,
  name: string,
  district: number | null,
  extra = {},
) => ({
  id,
  name,
  district,
  percent_reporting: 0,
  total_votes: 0,
  called: false,
  source_url: `https://civicapi.org/api/v2/race/${id}`,
  counties: [],
  seats: null,
  candidates: [
    candidate("Katie Hobbs", "Democratic", 0, 0),
    candidate("Andy Biggs", "Republican", 0, 0),
  ],
  ...extra,
});
export const countyRow = (fips: string, name: string, leaderVotes = 0) => ({
  fips,
  name,
  percent_reporting: leaderVotes ? 100 : 0,
  total_votes: leaderVotes,
  candidates: [
    candidate("Katie Hobbs", "Democratic", leaderVotes, leaderVotes ? 100 : 0),
    candidate("Andy Biggs", "Republican", 0, 0),
  ],
});
const chamber = (id: number, name: string, seats: number, dem: number) =>
  race(id, name, null, {
    seats,
    candidates: [
      candidate("Democratic", "Democratic", 0, 0, { seats: dem }),
      candidate("Republican", "Republican", 0, 0, { seats: seats - dem }),
    ],
  });
export const midtermResults = (
  overrides: Record<string, unknown[]> = {},
  stale = false,
) => ({
  election_date: "2026-11-03",
  source_url: "https://civicapi.org/api/v2/race/search?province=AZ",
  retrieved_at: new Date().toISOString(),
  stale,
  refresh_error: stale ? "Timeout: down" : null,
  revision: "fixture",
  offices: {
    governor: [
      race(1, "Arizona Governor", null, {
        counties: [countyRow("04013", "Maricopa"), countyRow("04019", "Pima")],
      }),
    ],
    "attorney-general": [race(2, "Arizona Attorney General", null)],
    "secretary-of-state": [race(3, "Arizona Secretary of State", null)],
    "us-house": [1, 2, 3].map((n) => race(10 + n, `Arizona US House ${n}`, n)),
    "state-senate": [
      chamber(20, "Arizona State Senate", 30, 14),
      ...[1, 2, 3].map((n) => race(20 + n, `Arizona State Senate ${n}`, n)),
    ],
    "state-house": [
      chamber(30, "Arizona State House", 60, 28),
      ...[1, 2, 3].map((n) => race(30 + n, `Arizona State House ${n}`, n)),
    ],
    ...overrides,
  },
});

// Three square districts are enough to exercise the one-map, one-table layout.
export const chamberGeography = {
  type: "FeatureCollection",
  features: [1, 2, 3].map((n) => ({
    type: "Feature",
    properties: { district: n, name: `District ${n}`, label: String(n) },
    geometry: {
      type: "Polygon",
      coordinates: [
        [
          [-113 + n, 33],
          [-112 + n, 33],
          [-112 + n, 34],
          [-113 + n, 34],
          [-113 + n, 33],
        ],
      ],
    },
  })),
};

export async function mockMidterm(page: Page, ...bodies: object[]) {
  let calls = 0;
  await page.route("**/api/midterm-2026?office=*", (route) =>
    route.fulfill({ json: bodies[Math.min(calls++, bodies.length - 1)] }),
  );
  // One announcement of the fixture revision, then no reconnect for ten minutes.
  await page.route("**/api/midterm-2026/updates", (route) =>
    route.fulfill({
      status: 200,
      contentType: "text/event-stream",
      body: `retry: 600000\nevent: revision\ndata: {"revision":"fixture"}\n\n`,
    }),
  );
  await page.route("**/api/midterm-2026/geography/*", (route) =>
    route.fulfill({ json: chamberGeography }),
  );
  return () => calls;
}

// Use instead of the Playwright test export in specs that land on "/" but do not test midterm
// results. Not for specs that rely on the real browser HTTP cache: any route disables it.
export const test = base.extend({
  page: async ({ page }, use) => {
    await mockMidterm(page, midtermResults());
    await use(page);
  },
});
