import { test, expect } from "@playwright/test";
test("catalog, candidate results, county map, details, sorting, year navigation and error handling", async ({
  page,
}) => {
  const errors: string[] = [];
  page.on("pageerror", (e) => errors.push(e.message));
  await page.goto("/");
  await expect(
    page.getByRole("heading", { name: "Election catalog" }),
  ).toBeVisible();
  await expect(page.locator(".election-card")).toHaveCount(8);
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
  await expect(page.locator(".election-card")).toHaveCount(8);
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

test("2026 participation is distinct from candidate results", async ({
  page,
}) => {
  const errors: string[] = [];
  page.on("pageerror", (e) => errors.push(e.message));
  await page.goto("/");
  const card = page
    .locator(".office-section")
    .filter({ hasText: "Arizona Governor" })
    .locator(".election-card")
    .filter({ hasText: "2026" });
  await expect(card).toContainText("Voting in progress");
  await card.click();
  await expect(
    page.getByRole("heading", { name: "Governor 2026", exact: true }),
  ).toBeVisible();
  await expect(
    page.getByText("Voting in progress — candidate results not yet released."),
  ).toBeVisible();
  await expect(
    page.getByRole("heading", { name: "Candidate results", exact: true }),
  ).toHaveCount(0);
  await expect(page.locator(".candidate-row")).toHaveCount(0);
  await expect(page.locator(".county-map path.other")).toHaveCount(15);
  await expect(page.locator(".county-map path.dem")).toHaveCount(0);
  await expect(page.locator(".county-map path.rep")).toHaveCount(0);
  const state = page.getByRole("region", {
    name: "Statewide participation availability",
  });
  await expect(state).toContainText("4,374,827");
  await expect(state).toContainText("N/A");
  await expect(state).toContainText("2 / 15");
  await page
    .getByRole("button", { name: "Pima County. View early-voting activity." })
    .click();
  const detail = page.getByRole("region", { name: "Selected county details" });
  await expect(
    detail.getByRole("heading", { name: "Pima County" }),
  ).toBeVisible();
  await expect(detail).toContainText("190,232");
  await expect(detail).toContainText("494,284");
  await expect(detail).toContainText("date only");
  const table = page.getByRole("region", {
    name: "County participation table",
  });
  await expect(table.locator("tbody tr")).toHaveCount(15);
  await table.getByRole("button", { name: "Returns", exact: false }).click();
  await expect(table.locator("tbody tr").first()).toContainText("Maricopa");
  await table.getByRole("button", { name: "Returns", exact: false }).click();
  await expect(table.locator("tbody tr").first()).toContainText("Pima");
  await table.getByRole("button", { name: "Apache" }).focus();
  await page.keyboard.press("Enter");
  await expect(
    detail.getByRole("heading", { name: "Apache County" }),
  ).toBeVisible();
  await expect(detail).toContainText("N/A");
  await page.getByText("Source checks & cautions (1)").click();
  await expect(
    page.getByRole("region", { name: "Reporting dates and source status" }),
  ).toContainText("difference +108");
  await expect(
    page.getByText("Manual refresh · America/Phoenix (MST)"),
  ).toBeVisible();
  await page.setViewportSize({ width: 390, height: 844 });
  expect(
    await page.evaluate(() => document.documentElement.scrollWidth),
  ).toBeLessThanOrEqual(390);
  await page.screenshot({
    path: "test-results/2026-mobile.png",
    fullPage: true,
  });
  await page.getByLabel("Election year").selectOption("az-2022-governor");
  await expect(page.locator(".statewide .candidate-row")).toHaveCount(9);
  expect(errors).toEqual([]);
});

test("Attorney General archive and 2026 participation share the existing interface", async ({
  page,
}) => {
  await page.goto("/");
  const office = page
    .locator(".office-section")
    .filter({ hasText: "Arizona Attorney General" });
  await expect(office.locator(".election-card")).toHaveCount(4);
  await office.locator(".election-card").filter({ hasText: "2026" }).click();
  await expect(
    page.getByRole("heading", { name: "Attorney General 2026", exact: true }),
  ).toBeVisible();
  await expect(page.locator(".county-map path.other")).toHaveCount(15);
  await expect(page.locator(".candidate-row")).toHaveCount(0);
  await expect(page.locator(".notice")).toContainText(
    "not votes cast specifically for Attorney General",
  );
  await page.getByLabel("Election year").selectOption("az-2022-attorney-general");
  await expect(
    page.getByRole("heading", { name: "Attorney General 2022", exact: true }),
  ).toBeVisible();
  await expect(page.locator(".statewide .candidate-row")).toHaveCount(3);
  await expect(page.locator(".contest-total strong")).toHaveText("2,509,133");
});
