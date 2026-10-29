import { test, expect } from "@playwright/test";

test("House archive uses each district's candidates and historical geometry", async ({
  page,
}) => {
  const errors: string[] = [];
  page.on("pageerror", (e) => errors.push(e.message));
  await page.goto("/");
  await page.getByRole("tab", { name: "Federal Elections" }).click();
  const office = page
    .locator(".office-section")
    .filter({ hasText: "Arizona U.S. House" });
  await expect(office.locator(".election-card")).toHaveCount(8);
  await office.locator('a[href="/elections/az-2024-us-house"]').click();
  const picker = page.getByLabel("Election year");
  await expect(picker.locator("option")).toHaveCount(8);
  const table = page.getByRole("region", { name: "District results table" });
  const details = page.getByRole("region", {
    name: "Selected district details",
  });
  const years: [number, number, string][] = [
    [2024, 2, "434,504"],
    [2022, 2, "361,477"],
    [2020, 2, "365,178"],
    [2018, 3, "266,089"],
    [2016, 3, "280,710"],
    [2014, 2, "185,114"],
  ];
  const shapes: Record<number, string | null> = {};
  for (const [year, candidates, total] of years) {
    await picker.selectOption(`az-${year}-us-house`);
    await expect(
      page.getByRole("heading", { name: `U.S. House ${year}`, exact: true }),
    ).toBeVisible();
    await expect(page.locator(".county-map path")).toHaveCount(9);
    await expect(table.locator("tbody tr")).toHaveCount(9);
    await expect(
      details.getByRole("heading", { name: "District 1", exact: true }),
    ).toBeVisible();
    await expect(page.locator(".statewide .candidate-row")).toHaveCount(
      candidates,
    );
    await expect(page.locator(".contest-total strong")).toHaveText(total);
    await expect(page.locator(".statewide")).not.toContainText(
      "Statewide results",
    );
    shapes[year] = await page
      .locator(".county-map path")
      .first()
      .getAttribute("d");
  }
  expect(shapes[2014]).toEqual(shapes[2020]);
  expect(shapes[2022]).toEqual(shapes[2024]);
  expect(shapes[2020]).not.toEqual(shapes[2022]);
  await picker.selectOption("az-2024-us-house");
  await table.getByRole("button", { name: "District 3", exact: true }).focus();
  await page.keyboard.press("Enter");
  await expect(
    details.getByRole("heading", { name: "District 3", exact: true }),
  ).toBeVisible();
  await expect(page.locator(".statewide .candidate-row")).toHaveCount(4);
  await expect(page.locator(".statewide")).toContainText("Yassamin Ansari");
  await expect(page.locator(".statewide")).not.toContainText(
    "David Schweikert",
  );
  const district9 = page.getByRole("button", {
    name: "District 9, Paul Gosar. View district results.",
  });
  await district9.focus();
  await page.keyboard.press("Space");
  await expect(
    details.getByRole("heading", { name: "District 9", exact: true }),
  ).toBeVisible();
  await expect(page.locator(".statewide")).toContainText("249,583 votes");
  await expect(page.locator(".contest-total strong")).toHaveText("382,223");
  await table.getByRole("button", { name: "Contest votes" }).click();
  await expect(table.locator("tbody tr").first()).toContainText("District 3");
  await table.getByRole("button", { name: "Contest votes" }).click();
  await expect(table.locator("tbody tr").first()).toContainText("District 1");
  await page.getByRole("button", { name: "Close district details" }).click();
  await expect(details).toContainText("Explore a district’s story");
  await table.getByRole("button", { name: "District 1", exact: true }).click();
  await expect(
    details.getByRole("heading", { name: "District 1", exact: true }),
  ).toBeVisible();
  const boxes = await page
    .locator(".county-map path")
    .evaluateAll((paths) =>
      paths.map((p) => (p as SVGGraphicsElement).getBBox().width),
    );
  expect(Math.max(...boxes)).toBeLessThan(450);
  expect(Math.max(...boxes)).toBeGreaterThan(50);
  await page.screenshot({
    path: "test-results/house-2024-desktop.png",
    fullPage: true,
  });
  await page.setViewportSize({ width: 390, height: 844 });
  expect(
    await page.evaluate(() => document.documentElement.scrollWidth),
  ).toBeLessThanOrEqual(390);
  await table.getByRole("button", { name: "District 6", exact: true }).click();
  await expect(
    details.getByRole("heading", { name: "District 6", exact: true }),
  ).toBeVisible();
  await page.screenshot({
    path: "test-results/house-2024-mobile.png",
    fullPage: true,
  });
  expect(errors).toEqual([]);
});

test("special elections display civicAPI reports and distinguish not contested districts", async ({
  page,
}) => {
  const errors: string[] = [];
  page.on("pageerror", (e) => errors.push(e.message));
  for (const [year, district, count] of [
    [2018, 8, 2],
    [2025, 7, 4],
  ]) {
    await page.goto(
      `/elections/az-${year}-us-house-special-${String(district).padStart(2, "0")}`,
    );
    await expect(
      page.getByRole("heading", { name: `U.S. House ${year}`, exact: true }),
    ).toBeVisible();
    await expect(page.locator(".election-meta .badge")).toContainText(
      "civicAPI report",
    );
    await expect(page.locator(".notice")).toContainText(
      "civicAPI report · not an official canvass",
    );
    await expect(page.locator(".county-map path")).toHaveCount(9);
    await expect(
      page.locator('.county-map path[aria-disabled="true"]'),
    ).toHaveCount(8);
    await expect(
      page.locator('.county-map path[aria-disabled="true"]').first(),
    ).toHaveAttribute("tabindex", "-1");
    await expect(page.locator(".county-map path.other")).toHaveCount(8);
    await expect(
      page
        .getByRole("region", { name: "District results table" })
        .locator("tbody tr"),
    ).toHaveCount(1);
    await expect(page.locator(".statewide .candidate-row")).toHaveCount(count);
    await expect(page.locator(".contest-total strong")).not.toHaveText("N/A");
    await expect(page.locator(".sources")).toContainText("civicAPI");
    await expect(page.locator(".sources")).toContainText("not official canvass");
    const details = page.getByRole("region", {
      name: "Selected district details",
    });
    await expect(
      details.getByRole("heading", {
        name: `District ${district}`,
        exact: true,
      }),
    ).toBeVisible();
    await expect(details).toContainText("N/A");
    await page.setViewportSize({ width: 390, height: 844 });
    expect(
      await page.evaluate(() => document.documentElement.scrollWidth),
    ).toBeLessThanOrEqual(390);
  }
  await page.getByLabel("Election year").selectOption("az-2018-us-house");
  await expect(page.locator(".county-map path[aria-disabled]")).toHaveCount(0);
  await expect(
    page
      .getByRole("region", { name: "District results table" })
      .locator("tbody tr"),
  ).toHaveCount(9);
  expect(errors).toEqual([]);
});
