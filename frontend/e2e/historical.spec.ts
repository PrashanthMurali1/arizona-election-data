import { test, expect } from "@playwright/test";

const election = {
  id: "az-1966-historical-state-senate",
  year: 1966,
  date: "1966-11-08",
  office_id: "state-senate",
  office: "State Senate",
  kind: "general",
  status: "reported",
  notes: "Historical canvass",
  county_count: 0,
  candidate_count: 2,
  district_count: 2,
  boundary_id: "historical-results-1966",
};

test("new office sections and map-free historical district navigation", async ({
  page,
}) => {
  const geographyRequests: string[] = [];
  page.on("request", (r) => {
    if (r.url().includes("/api/geography/")) geographyRequests.push(r.url());
  });
  await page.route("**/api/**", async (route) => {
    const path = new URL(route.request().url()).pathname;
    if (path === "/api/elections") return route.fulfill({ json: [election] });
    if (path === `/api/historical-elections/${election.id}`) {
      return route.fulfill({
        json: {
          election,
          map_available: false,
          multi_seat: true,
          sources: [
            {
              id: "source",
              title: "1966 official canvass",
              url: "https://example.test/canvass.pdf",
              notes: "Source fixture",
            },
          ],
          contests: ["7-A", "7-B"].map((district, i) => ({
            district,
            contest_id: `${election.id}-district-${district}`,
            page: 3,
            notes: "Printed contest totals.",
            results: {
              geoid: district,
              name: `District ${district}`,
              status: "reported",
              total_votes: 100,
              winner: null,
              turnout: {},
              candidates: [
                {
                  id: district,
                  name: i
                    ? "Second district candidate"
                    : "First district candidate",
                  party: "DEM",
                  party_name: "Democratic",
                  votes: 100,
                  percent: 100,
                  status: "verified",
                  write_in: false,
                  category: "named_candidate",
                },
              ],
            },
          })),
        },
      });
    }
    return route.fulfill({
      status: 404,
      json: { detail: "Unexpected request" },
    });
  });
  for (const width of [1440, 390]) {
    await page.setViewportSize({ width, height: 1000 });
    await page.goto("/?office=state-senate");
    await expect(
      page.getByRole("tab", { name: "State Elections" }),
    ).toHaveAttribute("aria-selected", "true");
    const mobileOffice = page.getByLabel("State office", { exact: true });
    if (width < 600) {
      await expect(
        mobileOffice.locator('option[value="secretary-of-state"]'),
      ).toHaveText("Secretary of State");
      await expect(
        mobileOffice.locator('option[value="state-house"]'),
      ).toHaveText("State House");
    } else {
      await expect(
        page.getByRole("button", { name: "Secretary of State", exact: true }),
      ).toBeVisible();
      await expect(
        page.getByRole("button", { name: "State House", exact: true }),
      ).toBeVisible();
    }
    await page.getByRole("link", { name: /Arizona State Senate/ }).click();
    await expect(
      page.getByRole("heading", { name: "State Senate 1966" }),
    ).toBeVisible();
    await expect(
      page.getByText("First district candidate", { exact: true }),
    ).toBeVisible();
    await page.getByLabel("District", { exact: true }).selectOption("7-B");
    await expect(
      page.getByText("Second district candidate", { exact: true }),
    ).toBeVisible();
    await expect(
      page.getByText("First district candidate", { exact: true }),
    ).toHaveCount(0);
    await expect(
      page.getByRole("link", { name: "View official canvass · page 3" }),
    ).toHaveAttribute("href", /#page=3$/);
    expect(
      await page.evaluate(
        () => document.documentElement.scrollWidth <= innerWidth,
      ),
    ).toBe(true);
    await page.screenshot({
      path: `test-results/historical-${width}.png`,
      fullPage: true,
    });
  }
  expect(geographyRequests).toEqual([]);
});

test("presidential candidates and early county maps are shown", async ({
  page,
}) => {
  const president = {
    ...election,
    id: "az-1964-historical-president",
    year: 1964,
    date: "1964-11-03",
    office_id: "president",
    office: "President",
    boundary_id: "county-1966-1982",
  };
  const statewide = {
    geoid: "04",
    name: "Arizona",
    status: "reported",
    total_votes: 100,
    winner: null,
    turnout: {
      ballots_cast: 100,
      registered_voters: 150,
      percent: 66.67,
      definition: "Official turnout.",
    },
    candidates: [
      {
        id: "johnson",
        name: "Lyndon B. Johnson",
        party: "DEM",
        party_name: "Democratic",
        votes: 100,
        percent: 100,
        status: "verified",
        write_in: false,
        category: "presidential_candidate",
      },
    ],
  };
  await page.route("**/api/**", async (route) => {
    const path = new URL(route.request().url()).pathname;
    if (path === "/api/elections") return route.fulfill({ json: [president] });
    if (path.endsWith("/counties")) return route.fulfill({ json: [] });
    if (path.endsWith("/activity")) return route.fulfill({ json: null });
    if (path.includes("/geography/"))
      return route.fulfill({
        json: { boundary_id: "county-1966-1982", vintage: 1966, features: [] },
      });
    return route.fulfill({
      json: {
        election: president,
        statewide,
        sources: [],
        reconciliation: { notes: "Official party returns.", candidates: [] },
      },
    });
  });
  for (const width of [1440, 390]) {
    await page.setViewportSize({ width, height: 1000 });
    await page.goto(`/elections/${president.id}`);
    await expect(
      page.getByRole("heading", { name: "President 1964" }),
    ).toBeVisible();
    await expect(
      page.getByText("Lyndon B. Johnson", { exact: true }),
    ).toBeVisible();
    await expect(
      page.getByRole("region", { name: "County winner map" }),
    ).toBeVisible();
    await expect(
      page.getByRole("region", { name: "Election turnout" }),
    ).toBeVisible();
    await expect(
      page.getByText("Elector results", { exact: true }),
    ).toHaveCount(0);
    expect(
      await page.evaluate(
        () => document.documentElement.scrollWidth <= innerWidth,
      ),
    ).toBe(true);
  }
});
