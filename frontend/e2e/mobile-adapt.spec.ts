import { test, expect, type Page } from "@playwright/test";
import { readFileSync, mkdirSync, writeFileSync, existsSync } from "node:fs";
import { resolve } from "node:path";
import { mockMidterm, midtermResults } from "./helpers";

const before = process.env.MOBILE_CAPTURE_BEFORE === "1";
const artifacts = resolve("../tmp/mobile-adapt");
mkdirSync(artifacts, { recursive: true });
async function capture(page: Page, name: string, desktop: boolean) {
  await page.evaluate(() => document.fonts.ready);
  await page.mouse.move(0, 0);
  const bytes = await page.screenshot({
    fullPage: true,
    animations: "disabled",
  });
  const baseline = resolve(artifacts, `before-${name}.png`);
  writeFileSync(
    resolve(artifacts, `${before ? "before" : "after"}-${name}.png`),
    bytes,
  );
  if (
    !before &&
    process.env.MOBILE_COMPARE_DESKTOP === "1" &&
    desktop &&
    existsSync(baseline)
  )
    expect(
      bytes.equals(readFileSync(baseline)),
      `${name}: desktop pixels unchanged`,
    ).toBe(true);
}
async function noOverflow(page: Page) {
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth,
    ),
  ).toBe(true);
  const clipped = await page
    .locator(
      ".summary-heading, .lead-candidate, .archive-heading, .panel-heading, .county-detail",
    )
    .evaluateAll((elements) =>
      elements
        .filter(
          (el) =>
            !el.classList.contains("sr-only") &&
            el.scrollWidth > el.clientWidth + 1,
        )
        .map((el) => el.className),
    );
  expect(clipped).toEqual([]);
}
const browserName =
  process.env.MOBILE_ENGINE === "webkit" ? "webkit" : "chromium";
test.use({ browserName, hasTouch: true });
for (const width of before
  ? [440, 1024, 1440]
  : [320, 375, 393, 430, 440, 768, 1024, 1440]) {
  test(`responsive exploration at ${width}px`, async ({ page }) => {
    await page.setViewportSize({ width, height: 956 });
    await mockMidterm(page, midtermResults());
    await page.goto("/");
    await expect(page.locator(".statewide")).toBeVisible();
    await expect(page.locator(".county-map path").first()).toBeVisible();
    await capture(page, `${browserName}-${width}-home`, width >= 1024);
    if (!before) {
      await noOverflow(page);
      const tabs = page.getByRole("tablist", {
        name: "Election categories",
      });
      for (const tab of await tabs.getByRole("tab").all()) {
        expect(
          await tab.evaluate((el) => {
            const range = document.createRange();
            range.selectNodeContents(el);
            return range.getClientRects().length;
          }),
        ).toBe(1);
      }
      if (width <= 560) {
        const heading = page.locator(".archive-heading");
        expect(
          await heading.evaluate(
            (el) =>
              el.children[1].getBoundingClientRect().top >=
              el.children[0].getBoundingClientRect().bottom,
          ),
        ).toBe(true);
      }
      await page
        .getByRole("button", { name: "Light theme", exact: true })
        .tap();
      await expect(page.locator("html")).toHaveAttribute("data-theme", "light");
      await noOverflow(page);
      await page.getByRole("button", { name: "Dark theme", exact: true }).tap();
      const table = page.getByRole("region", {
        name: "County results table",
      });
      await table.getByRole("button", { name: "Dem %", exact: true }).tap();
      await expect(table.locator("th[aria-sort='descending']")).toContainText(
        "Dem %",
      );
      const scroll = table.locator(".table-scroll");
      await scroll.evaluate((el) => {
        el.scrollLeft = el.scrollWidth;
      });
      if (width <= 440)
        expect(await scroll.evaluate((el) => el.scrollLeft)).toBeGreaterThan(0);
      await table.getByRole("button", { name: "Maricopa", exact: true }).tap();
      const detail = page.getByRole("region", {
        name: "Selected county details",
      });
      await expect(detail).toContainText("Maricopa County");
      await noOverflow(page);
      await detail.getByRole("button", { name: "Close county details" }).tap();
      await page.getByRole("button", { name: /^Pima County/ }).tap();
      await expect(detail).toContainText("Pima County");
      await detail.getByRole("button", { name: "Close county details" }).tap();
      if (width <= 560)
        await page
          .getByLabel("Midterm office", { exact: true })
          .selectOption("us-house");
      else
        await page
          .getByRole("navigation", { name: "Midterm office directory" })
          .getByRole("button", { name: "U.S. House", exact: true })
          .tap();
      await expect(
        page.getByRole("heading", {
          name: "District 1 · Candidate results",
        }),
      ).toBeVisible();
      await noOverflow(page);
      for (const name of [
        "Early Voting",
        "Federal Elections",
        "State Elections",
      ]) {
        await tabs.getByRole("tab", { name, exact: true }).tap();
        await expect(
          tabs.getByRole("tab", { name, exact: true }),
        ).toHaveAttribute("aria-selected", "true");
        await expect(page.locator("[role='tabpanel']:visible")).not.toBeEmpty();
        if (name === "Early Voting") {
          await expect(page.locator(".statewide-participation")).toBeVisible();
          if (width === 320 || width === 440)
            await capture(page, `${browserName}-${width}-early-voting`, false);
        } else await expect(page.locator(".archive-row").first()).toBeVisible();
        await noOverflow(page);
      }
      await page.locator(".footer").scrollIntoViewIfNeeded();
      await expect(page.locator(".footer")).toBeVisible();
      expect(await page.evaluate(() => scrollY)).toBeGreaterThan(0);
    }
    await page.goto("/elections/az-2006-governor");
    await page
      .getByRole("region", { name: "County results table" })
      .getByRole("button", { name: "Maricopa", exact: true })
      .press("Enter");
    await capture(page, `${browserName}-${width}-historical`, width >= 1024);
    if (!before) {
      await noOverflow(page);
      await expect(page.locator(".county-detail .turnout-panel")).toBeVisible();
      await page
        .getByRole("combobox", { name: "Election year", exact: true })
        .selectOption("az-2002-governor");
      await expect(
        page.getByRole("heading", { name: "Governor 2002", exact: true }),
      ).toBeVisible();
      await noOverflow(page);
      await page.goto("/methodology");
      await expect(
        page.getByRole("heading", {
          name: "Data Sources & Methodology",
          exact: true,
        }),
      ).toBeVisible();
      await noOverflow(page);
    }
  });
}

if (!before && browserName === "chromium") {
  test("touch swipes scroll the tab strip and the page on their respective axes", async ({
    page,
    context,
  }) => {
    await page.setViewportSize({ width: 440, height: 956 });
    await mockMidterm(page, midtermResults());
    await page.goto("/");
    const tabs = page.getByRole("tablist", { name: "Election categories" });
    await tabs.scrollIntoViewIfNeeded();
    const rect = (await tabs.boundingBox())!;
    const cdp = await context.newCDPSession(page);
    const swipe = async (x: number, y: number, dx: number, dy: number) => {
      await cdp.send("Input.dispatchTouchEvent", {
        type: "touchStart",
        touchPoints: [{ x, y }],
      });
      for (let step = 1; step <= 8; step++) {
        await cdp.send("Input.dispatchTouchEvent", {
          type: "touchMove",
          touchPoints: [{ x: x + (dx * step) / 8, y: y + (dy * step) / 8 }],
        });
        await page.waitForTimeout(20);
      }
      await cdp.send("Input.dispatchTouchEvent", {
        type: "touchEnd",
        touchPoints: [],
      });
    };
    await swipe(rect.x + rect.width - 24, rect.y + rect.height / 2, -240, 0);
    await expect
      .poll(() => tabs.evaluate((el) => el.scrollLeft))
      .toBeGreaterThan(0);
    const prior = await page.evaluate(() => scrollY);
    await swipe(220, rect.y + rect.height / 2, 0, -200);
    await expect
      .poll(() => page.evaluate(() => scrollY))
      .toBeGreaterThan(prior);
    await expect(tabs.getByRole("tab", { selected: true })).toHaveText(
      "2026 Midterm Results",
    );
    await noOverflow(page);
    await cdp.detach();
  });
}
