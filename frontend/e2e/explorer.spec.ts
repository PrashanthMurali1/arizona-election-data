import { test, expect } from "@playwright/test";

test("Senate archive reuses results, county selection, year navigation and responsive layout", async ({
  page,
}) => {
  const errors: string[] = [];
  page.on("pageerror", (e) => errors.push(e.message));
  await page.goto("/");
  const office = page
    .locator(".office-section")
    .filter({ hasText: "Arizona U.S. Senate" });
  await expect(office.locator(".election-card")).toHaveCount(5);
  await expect(
    office.locator(".election-card").filter({ hasText: "2020" }),
  ).toContainText("SPECIAL ELECTION");
  await office.locator(".election-card").filter({ hasText: "2024" }).click();
  const elections: [number, string, number, string][] = [
    [2024, "az-2024-us-senate", 10, "3,348,814"],
    [2022, "az-2022-us-senate", 11, "2,572,294"],
    [2020, "az-2020-us-senate-special", 19, "3,355,317"],
    [2018, "az-2018-us-senate", 10, "2,384,308"],
    [2016, "az-2016-us-senate", 11, "2,530,730"],
  ];
  for (const [year, id, count, total] of elections) {
    await page.getByLabel("Election year").selectOption(id);
    await expect(
      page.getByRole("heading", { name: `U.S. Senate ${year}`, exact: true }),
    ).toBeVisible();
    await expect(page.locator(".statewide .candidate-row")).toHaveCount(count);
    await expect(page.locator(".contest-total strong")).toHaveText(total);
    await expect(page.locator(".county-map path")).toHaveCount(15);
    await expect(
      page
        .getByRole("region", { name: "County results table" })
        .locator("tbody tr"),
    ).toHaveCount(15);
  }
  const years = page.getByLabel("Election year");
  await expect(years.locator("option")).toHaveCount(5);
  await expect(
    years.locator('option[value="az-2020-us-senate-special"]'),
  ).toContainText("special election");
  await years.selectOption("az-2020-us-senate-special");
  await expect(page.locator(".election-heading .eyebrow")).toContainText(
    "SPECIAL ELECTION",
  );
  const table = page.getByRole("region", { name: "County results table" });
  await table.getByRole("button", { name: "Contest votes" }).click();
  await expect(table.locator("tbody tr").first()).toContainText("Greenlee");
  await table.getByRole("button", { name: "Contest votes" }).click();
  await expect(table.locator("tbody tr").first()).toContainText("Maricopa");
  await table.getByRole("button", { name: "Pima", exact: true }).focus();
  await page.keyboard.press("Enter");
  const detail = page.getByRole("region", { name: "Selected county details" });
  await expect(
    detail.getByRole("heading", { name: "Pima County" }),
  ).toBeVisible();
  await expect(detail.locator(".candidate-row")).toHaveCount(19);
  await expect(detail).toContainText("309,142");
  await page
    .getByRole("button", {
      name: "Mohave County, Martha McSally. View county results.",
    })
    .click();
  await expect(
    detail.getByRole("heading", { name: "Mohave County" }),
  ).toBeVisible();
  await page.setViewportSize({ width: 390, height: 844 });
  expect(
    await page.evaluate(() => document.documentElement.scrollWidth),
  ).toBeLessThanOrEqual(390);
  await table.getByRole("button", { name: "Apache", exact: true }).click();
  await expect(
    detail.getByRole("heading", { name: "Apache County" }),
  ).toBeVisible();
  await page.screenshot({
    path: "test-results/senate-2020-mobile.png",
    fullPage: true,
  });
  expect(errors).toEqual([]);
});

test("catalog, candidate results, county map, details, sorting, year navigation and error handling", async ({
  page,
}) => {
  const errors: string[] = [];
  page.on("pageerror", (e) => errors.push(e.message));
  await page.goto("/");
  await expect(
    page.getByRole("heading", { name: "Election catalog" }),
  ).toBeVisible();
  await expect(page.locator(".election-card")).toHaveCount(20);
  await page
    .locator(".office-section")
    .filter({ hasText: "Arizona Governor" })
    .locator(".election-card")
    .filter({ hasText: "2022" })
    .click();
  await expect(
    page.getByRole("heading", { name: "Governor 2022", exact: true }),
  ).toBeVisible();
  await expect(page.locator(".statewide .candidate-row")).toHaveCount(9);
  await expect(page.locator(".county-map path")).toHaveCount(15);
  // Paths must fit the actual map, not render world-spanning inverse polygons.
  const widths = await page
    .locator(".county-map path")
    .evaluateAll((paths) =>
      paths.map((p) => (p as SVGGraphicsElement).getBBox().width),
    );
  expect(Math.max(...widths)).toBeLessThan(450);
  expect(Math.max(...widths)).toBeGreaterThan(50);
  const table = page.getByRole("region", { name: "County results table" });
  await expect(table.locator("tbody tr").first()).toContainText("Maricopa");
  await page
    .getByRole("button", {
      name: "Pima County, Katie Hobbs. View county results.",
    })
    .click();
  const detail = page.getByRole("region", { name: "Selected county details" });
  await expect(
    detail.getByRole("heading", { name: "Pima County" }),
  ).toBeVisible();
  await expect(detail).toContainText("63.07%");
  await expect(detail.locator(".candidate-row")).toHaveCount(9);
  await expect(page.locator(".statewide .candidate-row")).toHaveCount(9);
  await expect(table.locator("tbody tr")).toHaveCount(15);
  await table.getByRole("button", { name: "Contest votes" }).click();
  await expect(table.locator("tbody tr").first()).toContainText("Greenlee");
  await table.getByRole("button", { name: "Contest votes" }).click();
  await expect(table.locator("tbody tr").first()).toContainText("Maricopa");
  // Table provides a keyboard-accessible alternative to the map.
  await table.getByRole("button", { name: "Apache" }).focus();
  await page.keyboard.press("Enter");
  await expect(
    detail.getByRole("heading", { name: "Apache County" }),
  ).toBeVisible();
  await page.getByLabel("Election year").selectOption("az-2014-governor");
  await expect(
    page.getByRole("heading", { name: "Governor 2014", exact: true }),
  ).toBeVisible();
  await expect(page.locator(".statewide .candidate-row")).toHaveCount(10);
  await page.getByLabel("Election year").selectOption("az-2018-governor");
  await expect(
    page.getByRole("heading", { name: "Governor 2018", exact: true }),
  ).toBeVisible();
  await expect(page.locator(".contest-total strong")).toHaveText("2,376,441");
  await expect(page.locator(".statewide .candidate-row")).toHaveCount(8);
  await expect(page.locator(".county-map path.rep")).toHaveCount(11);
  await expect(page.locator(".county-map path.dem")).toHaveCount(4);
  await page.goto("/elections/does-not-exist");
  await expect(page.getByRole("alert")).toContainText("404");
  expect(errors).toEqual([]);
});
test("mobile layout contains overflow and supports county selection", async ({
  page,
}) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/elections/az-2022-governor");
  await expect(page.locator(".county-map path")).toHaveCount(15);
  expect(
    await page.evaluate(() => document.documentElement.scrollWidth),
  ).toBeLessThanOrEqual(390);
  await page
    .getByRole("region", { name: "County results table" })
    .getByRole("button", { name: "Maricopa" })
    .click();
  await expect(
    page.getByRole("heading", { name: "Maricopa County" }),
  ).toBeVisible();
  await page.screenshot({ path: "test-results/mobile.png", fullPage: true });
});
test("desktop layout and catalog screenshots", async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 1000 });
  await page.goto("/");
  await expect(page.locator(".election-card")).toHaveCount(20);
  await page.screenshot({ path: "test-results/catalog.png", fullPage: true });
  await page.goto("/elections/az-2022-governor");
  await expect(page.locator(".county-map path")).toHaveCount(15);
  const map = await page.locator(".map-panel").boundingBox(),
    table = await page.locator(".table-panel").boundingBox();
  expect(map!.x).toBeLessThan(table!.x);
  expect(map!.y).toBe(table!.y);
  await page.screenshot({ path: "test-results/results.png", fullPage: true });
});

test("2018 certified results, source caveat, county selection, sorting and mobile layout", async ({
  page,
}) => {
  const errors: string[] = [];
  page.on("pageerror", (e) => errors.push(e.message));
  await page.goto("/");
  const card = page
    .locator(".office-section")
    .filter({ hasText: "Arizona Governor" })
    .locator(".election-card")
    .filter({ hasText: "2018" });
  await expect(card).toContainText("Verified results");
  await card.click();
  await expect(
    page.getByRole("heading", { name: "Governor 2018", exact: true }),
  ).toBeVisible();
  await expect(page.locator(".contest-total strong")).toHaveText("2,376,441");
  await expect(page.locator(".statewide .candidate-row")).toHaveCount(8);
  await expect(page.locator(".county-map path")).toHaveCount(15);
  await page
    .getByRole("button", {
      name: "Pima County, David Garcia. View county results.",
    })
    .click();
  const detail = page.getByRole("region", { name: "Selected county details" });
  await expect(
    detail.getByRole("heading", { name: "Pima County" }),
  ).toBeVisible();
  await page
    .getByRole("region", { name: "County results table" })
    .getByRole("button", { name: "Maricopa" })
    .click();
  await expect(
    detail.getByRole("heading", { name: "Maricopa County" }),
  ).toBeVisible();
  await expect(detail.locator(".candidate-row")).toHaveCount(8);
  await expect(detail).toContainText("64.50%");
  await expect(detail).toContainText("1,454,103");
  const table = page.getByRole("region", { name: "County results table" });
  await expect(table.locator("tbody tr")).toHaveCount(15);
  await table.getByRole("button", { name: "Contest votes" }).click();
  await expect(table.locator("tbody tr").first()).toContainText("Greenlee");
  await table.getByRole("button", { name: "Contest votes" }).click();
  await expect(table.locator("tbody tr").first()).toContainText("Maricopa");
  await table.getByRole("button", { name: "Navajo" }).focus();
  await page.keyboard.press("Enter");
  const dole = detail
    .locator(".candidate-row")
    .filter({ hasText: "Cary D. Dolego" });
  await expect(dole).toContainText("0 votes");
  await expect(dole).toContainText("0.00%");
  await expect(page.locator(".sources")).toContainText("3,203 versus 275");
  await expect(page.locator(".sources-grid a")).toHaveCount(4);
  await page.setViewportSize({ width: 390, height: 844 });
  expect(
    await page.evaluate(() => document.documentElement.scrollWidth),
  ).toBeLessThanOrEqual(390);
  await table.getByRole("button", { name: "Pinal" }).click();
  await expect(
    detail.getByRole("heading", { name: "Pinal County" }),
  ).toBeVisible();
  await expect(
    detail.locator(".candidate-row").filter({ hasText: "Cary D. Dolego" }),
  ).toContainText("1 votes");
  await page.screenshot({
    path: "test-results/2018-mobile.png",
    fullPage: true,
  });
  expect(errors).toEqual([]);
});

test("one 2026 Early Voting catalog entry shows registration colors and populated columns", async ({ page }) => {
  const errors: string[] = [];
  page.on("pageerror", (e) => errors.push(e.message));
  await page.goto("/");
  const card = page.getByRole("link", { name: "2026 Early Voting", exact: true });
  await expect(card).toHaveCount(1);
  await expect(page.locator('.catalog a[href="/elections/az-2026-governor"]')).toHaveCount(0);
  await expect(page.locator('.catalog a[href="/elections/az-2026-attorney-general"]')).toHaveCount(0);
  await card.click();
  await expect(page).toHaveURL(/\/elections\/az-2026-early-voting$/);
  await expect(page.getByRole("heading", { name: "2026 Early Voting", exact: true })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Source snapshots", exact: true })).toHaveCount(0);
  await expect(page.getByRole("region", { name: "Reporting dates and source status" })).toHaveCount(0);
  await expect(page.locator(".notice > strong")).toHaveText("Early-voting participation reports.");
  await expect(page.locator(".candidate-row")).toHaveCount(0);
  await expect(page.locator(".county-map path.dem")).toHaveCount(5);
  await expect(page.locator(".county-map path.rep")).toHaveCount(10);
  await expect(page.locator(".county-map path.other")).toHaveCount(0);
  await expect(page.locator('.county-map path[aria-label^="Apache County."]')).toHaveClass(/dem/);
  await expect(page.locator('.county-map path[aria-label^="Maricopa County."]')).toHaveClass(/rep/);
  await expect(page.locator('.county-map path[aria-label^="Apache County."] title')).toContainText("Democratic registration");
  await expect(page.getByText("Colors show the largest party-registration group among returned early ballots in each county. They do not show which candidates voters selected or how they voted.", { exact: true })).toBeVisible();
  const state = page.getByRole("region", { name: "Statewide participation availability" });
  await expect(state).toContainText("3,289,914");
  await expect(state).toContainText("1,143,275");
  await expect(state).toContainText("15 / 15");
  await page.getByRole("button", { name: "Pima County. View early-voting activity." }).click();
  const detail = page.getByRole("region", { name: "Selected county details" });
  await expect(detail.getByRole("heading", { name: "Pima County" })).toBeVisible();
  await expect(detail.locator(".activity-metric")).toHaveCount(8);
  await expect(detail).not.toContainText("N/A");
  await expect(detail.getByText("Active registered voters", { exact: true })).toHaveCount(0);
  await expect(detail).toContainText("492,659");
  await expect(detail).toContainText("183,930");
  await expect(detail).toContainText("89,873");
  await expect(detail).toContainText("date only");
  await expect(detail).toContainText("As of:");
  await expect(detail).toContainText("Retrieved:");
  await expect(detail).toContainText("Early ballots requested in this county.");
  await expect(detail).toContainText("Early ballots returned, grouped by Democratic voter registration.");
  await expect(detail).not.toContainText(/civicAPI/i);
  const table = page.getByRole("region", { name: "County participation table" });
  await expect(table.locator("thead th")).toHaveCount(3);
  for (const [i, label] of ["County", "Requested", "Returned"].entries())
    await expect(table.locator("thead th").nth(i)).toContainText(label);
  await expect(table.locator("tbody tr")).toHaveCount(15);
  await expect(table.locator("tbody")).not.toContainText("N/A");
  await expect(table.locator('th[aria-sort="descending"]')).toContainText("Returned");
  await expect(table.locator("tbody tr").first()).toContainText("Maricopa");
  await table.getByRole("button", { name: "Returned", exact: false }).click();
  await expect(table.locator("tbody tr").first()).toContainText("Greenlee");
  await table.getByRole("button", { name: "Returned", exact: false }).click();
  await expect(table.locator("tbody tr").first()).toContainText("Maricopa");
  await table.getByRole("button", { name: "Apache" }).focus();
  await page.keyboard.press("Enter");
  await expect(detail.getByRole("heading", { name: "Apache County" })).toBeVisible();
  await expect(page.locator('.county-map path[aria-label^="Apache County."]')).toHaveClass(/selected/);
  await expect(page.locator(".sources")).toContainText("Democratic: 1,053,507");
  await expect(page.locator(".sources")).toContainText("Democratic: 430,622");
  await expect(page.getByRole("heading", { name: "Sources & coverage", exact: true })).toBeVisible();
  await expect(page.locator(".sources")).toContainText("civicAPI");
  await expect(page.locator('.sources a[href^="https://civicapi.org/api/v2/early-vote/AZ/"]')).toHaveCount(2);
  expect((await page.locator("main > :not(.sources)").allTextContents()).join(" ")).not.toMatch(/civicAPI/i);
  await page.setViewportSize({ width: 390, height: 844 });
  expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBeLessThanOrEqual(390);
  await page.screenshot({ path: "test-results/2026-mobile.png", fullPage: true });
  expect(errors).toEqual([]);
});

test("both old 2026 page URLs redirect and historical Attorney General entries remain", async ({ page }) => {
  for (const office of ["governor", "attorney-general"]) {
    await page.goto(`/elections/az-2026-${office}`);
    await expect(page).toHaveURL(/\/elections\/az-2026-early-voting$/);
    await expect(page.getByRole("heading", { name: "2026 Early Voting", exact: true })).toBeVisible();
  }
  await page.goto("/");
  const office = page.locator(".office-section").filter({ hasText: "Arizona Attorney General" });
  await expect(office.locator(".election-card")).toHaveCount(3);
  await office.locator(".election-card").filter({ hasText: "2022" }).click();
  await expect(page.getByRole("heading", { name: "Attorney General 2022", exact: true })).toBeVisible();
  await expect(page.locator(".statewide .candidate-row")).toHaveCount(3);
  await expect(page.locator(".contest-total strong")).toHaveText("2,509,133");
});

test("early-voting columns preserve zero and partial data; ties, Other and missing registration are neutral", async ({ page }) => {
  await page.route("**/api/elections/az-2026-early-voting/activity", async (route) => {
    const response = await route.fetch();
    const data = await response.json();
    for (const county of data.counties) {
      for (const metric of county.metrics) {
        metric.value = metric.key === "ballots_requested" && county.geoid === "04001" ? 10
          : metric.key === "ballots_accepted" && county.geoid === "04003" ? 0 : null;
        if (metric.value === 0) {
          metric.definition = "Synthetic zero-count participation fixture.";
          metric.coverage_note = "";
          metric.completeness = "complete";
        }
      }
    }
    const returned = data.provider_participation.reports.find((r: {category: string}) => r.category === "returned");
    returned.breakdowns["04001"] = { Democratic: 10, Republican: 10, Other: 0 };
    returned.breakdowns["04003"] = { Democratic: 2, Republican: 1, Other: 3 };
    returned.breakdowns["04005"] = { Democratic: 5, Republican: null, Other: 0 };
    const requested = data.provider_participation.reports.find((r: {category: string}) => r.category === "requested");
    requested.breakdowns["04021"] = { Democratic: 100000, Republican: 0, Other: 0 };
    await route.fulfill({ response, json: data });
  });
  await page.goto("/elections/az-2026-early-voting");
  const table = page.getByRole("region", { name: "County participation table" });
  await expect(table.locator("thead th")).toHaveCount(3);
  await expect(table.locator("thead")).toContainText("Requested");
  await expect(table.locator("thead")).toContainText("Accepted");
  await expect(table.locator("thead")).not.toContainText("Returned");
  await expect(table.locator('th[aria-sort="descending"]')).toContainText("Requested");
  await expect(table.locator("tbody tr").first()).toContainText("Apache");
  await expect(table.locator("tbody tr").filter({ hasText: "Cochise" }).locator("td").last()).toHaveText("0");
  await expect(table.locator("tbody tr").filter({ hasText: "Coconino" })).toContainText("N/A");
  await table.getByRole("button", { name: "Accepted", exact: false }).click();
  await expect(table.locator("tbody tr").first()).toContainText("Cochise");
  await table.getByRole("button", { name: "Cochise", exact: true }).click();
  const detail = page.getByRole("region", { name: "Selected county details" });
  await expect(detail.locator(".activity-metric")).toHaveCount(1);
  await expect(detail.locator(".activity-value strong").last()).toHaveText("0");
  await expect(detail).not.toContainText("N/A");
  for (const name of ["Apache", "Cochise", "Coconino"])
    await expect(page.locator(`.county-map path[aria-label^="${name} County."]`)).toHaveClass(/other/);
  // Requested is Democratic in this fixture; Returned still determines Pinal's red color.
  await expect(page.locator('.county-map path[aria-label^="Pinal County."]')).toHaveClass(/rep/);
  await page.locator('.county-map path[aria-label^="Apache County."]').focus();
  await page.keyboard.press("Space");
  await expect(page.getByRole("region", { name: "Selected county details" }).getByRole("heading", { name: "Apache County" })).toBeVisible();
  await expect(detail.locator(".activity-metric")).toHaveCount(1);
  await expect(detail.locator(".activity-value strong").last()).toHaveText("10");
  await expect(detail).not.toContainText("N/A");
});
