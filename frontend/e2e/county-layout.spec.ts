import { expect, test } from "@playwright/test";
import { mockMidterm, midtermResults } from "./helpers";

for (const width of [1440, 390]) {
  test(`county details preserve the reference layout at ${width}px`, async ({
    page,
  }, info) => {
    await page.setViewportSize({ width, height: 1000 });
    const url = "/api/elections/az-2006-governor/counties";
    const counties = await (await page.request.get(url)).json();
    const original = counties.find(
      (c: { name: string }) => c.name === "Maricopa",
    );
    expect(original).toBeTruthy();
    let current = original;
    await page.route(`**${url}*`, (route) =>
      route.fulfill({
        json: counties.map((c: { name: string }) =>
          c.name === "Maricopa" ? current : c,
        ),
      }),
    );
    const detail = page.getByRole("region", {
      name: "Selected county details",
    });
    for (const state of [
      "reference",
      "many",
      "missing",
      "empty",
      "zero",
    ] as const) {
      current = structuredClone(original);
      if (state === "many")
        current.candidates = Array.from({ length: 24 }, (_, i) => ({
          ...original.candidates[i % original.candidates.length],
          id: `candidate-${i}`,
          name: `Candidate ${i} with a long identifying name that must wrap without clipping`,
        }));
      if (state === "missing") {
        current.turnout = {
          ...current.turnout,
          percent: null,
          ballots_cast: null,
          registered_voters: null,
        };
        current.candidates[0] = {
          ...current.candidates[0],
          votes: null,
          percent: null,
        };
      }
      if (state === "empty") {
        current.candidates = [];
        current.total_votes = null;
      }
      if (state === "zero")
        current.candidates[0] = {
          ...current.candidates[0],
          votes: 0,
          percent: 0,
        };
      await page.goto("/elections/az-2006-governor");
      await page
        .getByRole("region", { name: "County results table" })
        .getByRole("button", { name: "Maricopa", exact: true })
        .click();
      await expect(
        detail.getByRole("heading", { name: "Maricopa County" }),
      ).toBeVisible();
      await expect(detail.locator(".candidate-row")).toHaveCount(
        current.candidates.length,
      );
      await expect(detail.locator(".turnout-panel")).toHaveCount(
        state === "missing" ? 0 : 1,
      );
      if (state === "zero")
        await expect(detail.locator(".candidate-row").first()).toContainText(
          "0.00%",
        );
      if (state === "missing") {
        await expect(detail.locator(".candidate-row").first()).toContainText(
          "Share unavailable",
        );
        await expect(
          detail.locator(".candidate-row").first(),
        ).not.toContainText("0.00%");
      }
      if (state === "empty")
        await expect(detail).toContainText(
          "Candidate results have not been verified",
        );
      const bounds = await detail.evaluate((el) => {
        const box = el.getBoundingClientRect();
        const grid = el.querySelector(".detail-grid")!;
        const columns = [...grid.children].map((c) =>
          c.getBoundingClientRect(),
        );
        return {
          overflow: el.scrollWidth > el.clientWidth,
          documentOverflow: document.documentElement.scrollWidth > innerWidth,
          contained: [
            ...el.querySelectorAll(
              ".candidate-info, .vote-value, .vote-track, .close-button",
            ),
          ].every((c) => {
            const r = c.getBoundingClientRect();
            return r.left >= box.left + 15 && r.right <= box.right - 15;
          }),
          stacked: columns.length === 2 && columns[1].top >= columns[0].bottom,
        };
      });
      expect(bounds.overflow).toBe(false);
      expect(bounds.documentOverflow).toBe(false);
      expect(bounds.contained).toBe(true);
      if (state === "reference") {
        expect(bounds.stacked).toBe(width < 900);
        await detail.screenshot({
          path: info.outputPath(`county-reference-${width}.png`),
        });
      }
      await detail
        .getByRole("button", { name: "Close county details" })
        .click();
      await expect(detail.locator(".candidate-row")).toHaveCount(0);
    }
    await mockMidterm(page, midtermResults());
    await page.goto("/");
    await page
      .getByRole("region", { name: "County results table" })
      .getByRole("button", { name: "Maricopa", exact: true })
      .click();
    await expect(detail).toContainText("Awaiting results");
    await expect(detail).not.toContainText("0.00%");
    await expect(detail.locator(".turnout-panel")).toHaveCount(0);
    await expect(detail).toContainText(
      "No votes reported in this contest yet.",
    );
    await detail.screenshot({
      path: info.outputPath(`county-awaiting-${width}.png`),
    });
    expect(
      await detail.evaluate((el) => el.scrollWidth <= el.clientWidth),
    ).toBe(true);
  });
}

