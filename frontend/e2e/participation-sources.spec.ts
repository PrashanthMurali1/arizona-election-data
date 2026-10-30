import { test, expect } from "@playwright/test";
import type { Activity } from "../src/types";
import { reportTime } from "../src/activity";

for (const theme of ["dark", "light"]) {
  test(`approved early-voting layout, notices and retrieval line work in ${theme}`, async ({
    page,
  }) => {
    await page.goto("/");
    await page
      .getByRole("button", {
        name: `${theme === "dark" ? "Dark" : "Light"} theme`,
        exact: true,
      })
      .click();
    const sources = page.getByRole("region", {
      name: "Sources & coverage",
      exact: true,
    });
    await expect(sources).toContainText(
      "Participation reports from civicAPI, which collects counts from state election offices.",
    );
    await expect(
      sources.getByRole("link", { name: "civicAPI", exact: true }),
    ).toHaveAttribute("href", "https://civicapi.org/early-vote/");
    await expect(sources.locator(".release-dates,.reporting-help")).toHaveCount(
      0,
    );
    await expect(page.locator(".county-detail")).toHaveCount(0);
    await expect(page.locator(".table-panel .table-note")).toHaveCount(0);
    const activity: Activity = await (
      await page.request.get("/api/elections/az-2026-early-voting/activity")
    ).json();
    const times = [
      ...new Set(
        activity.statewide.metrics
          .filter(
            (metric) =>
              metric.key.startsWith("ballots_received") && metric.source_id,
          )
          .map((metric) => `Retrieved: ${reportTime(metric.retrieved_at)}`),
      ),
    ];
    await expect(page.locator(".statewide .county-timestamps")).toHaveText(
      times.join(" | "),
    );
    await expect(
      page.locator(".statewide .county-timestamps"),
    ).not.toContainText(/As of|date only|Stale/);
    for (const width of [320, 390, 768, 1440]) {
      await page.setViewportSize({ width, height: 1000 });
      expect(
        await page.evaluate(() => document.documentElement.scrollWidth),
      ).toBe(width);
      for (const notice of await page.locator(".participation-notice").all()) {
        const positions = await notice.evaluate((element) => {
          const heading = element.querySelector("strong")!,
            paragraph = element.querySelector("p")!;
          const rect = (node: Element) => {
            const range = document.createRange();
            range.selectNodeContents(node);
            return range.getClientRects()[0];
          };
          return {
            heading: rect(heading).y,
            body: rect(paragraph).y,
            headingBottom: heading.getBoundingClientRect().bottom,
            paragraphTop: paragraph.getBoundingClientRect().top,
          };
        });
        if (width > 900)
          expect(
            Math.abs(positions.heading - positions.body),
          ).toBeLessThanOrEqual(2);
        else
          expect(positions.paragraphTop).toBeGreaterThanOrEqual(
            positions.headingBottom + 5,
          );
      }
      if (width === 1440) {
        const h = await sources.locator("h4").boundingBox(),
          p = await sources.locator("p").boundingBox();
        expect(Math.abs(h!.y - p!.y)).toBeLessThan(8);
      }
    }
    const table = page.getByRole("region", {
      name: "County participation table",
    });
    const county = table.getByRole("button", { name: "Maricopa", exact: true });
    await county.focus();
    await page.keyboard.press("Enter");
    const detail = page.getByRole("region", {
      name: "Selected county details",
    });
    await expect(detail).toBeFocused();
    await detail.locator("summary").click();
    await expect(detail.locator(".county-definitions")).toHaveJSProperty(
      "open",
      true,
    );
    await expect(detail).toContainText("Source report");
    await expect(detail).toContainText("date only");
    await expect(detail).toContainText("Retrieved");
    await page
      .getByRole("button", {
        name: theme === "dark" ? "Light theme" : "Dark theme",
        exact: true,
      })
      .click();
    await expect(detail.locator(".county-definitions")).toHaveJSProperty(
      "open",
      true,
    );
    await page
      .getByRole("button", { name: "Close county details", exact: true })
      .click();
    await expect(detail).toHaveCount(0);
    await expect(county).toBeFocused();
  });
}

test("other catalog categories and routes retain their original footer", async ({
  page,
}) => {
  await page.goto("/");
  const footer = page.getByRole("contentinfo");
  const content = await footer.innerHTML();
  await page.getByRole("tab", { name: "State Elections", exact: true }).click();
  await expect(page.locator(".provenance-banner")).toBeVisible();
  expect(await footer.innerHTML()).toBe(content);
  await page
    .getByRole("tab", { name: "Federal Elections", exact: true })
    .click();
  await expect(page.locator(".provenance-banner")).toBeVisible();
  expect(await footer.innerHTML()).toBe(content);
  for (const route of [
    "/elections/az-2022-governor",
    "/methodology",
    "/missing-route",
  ]) {
    await page.goto(route);
    expect(await footer.innerHTML()).toBe(content);
  }
});
