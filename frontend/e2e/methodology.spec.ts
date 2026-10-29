import { test, expect } from "@playwright/test";

test("methodology preserves the supplied structure, formatting, links and mobile layout", async ({ page }) => {
  await page.goto("/methodology");
  const article = page.locator("article.methodology");
  await expect(page.getByRole("navigation").getByRole("link", { name: "About the data" })).toHaveAttribute("href", "/methodology");
  await expect(article.getByRole("heading", { level: 1 })).toHaveText("Data Sources & Methodology");
  await expect(article.getByRole("heading", { level: 2 })).toHaveText([
    "About This Project",
    "Understanding the Data",
    "1. Historical Election Results",
    "2. Early-Voting Participation",
    "3. Candidates, Vote Shares, and Write-In Votes",
    "4. Voter Turnout and Ballots Cast",
    "5. Maps and Geographic Boundaries",
    "6. U.S. House Elections",
    "7. Additional Historical Data Sources",
    "8. Missing, Incomplete, and Unavailable Data",
    "9. Accuracy, Transparency, and Limitations",
    "Independence & Disclaimer",
  ]);
  await expect(article.getByRole("heading", { level: 3 })).toHaveText([
    "Official Election Records", "Data Collection and Processing", "Verifying Election Results",
    "Understanding Early-Voting Reports", "Participation Is Not Candidate Support", "Reporting and Updates",
    "Candidate Results", "Calculating Vote Percentages", "Arizona County Maps", "Interpreting Map Colors",
    "Historical Congressional Results", "Special Elections",
  ]);
  await expect(article.locator("ul")).toHaveCount(4);
  await expect(article.locator("li")).toHaveCount(12);
  await expect(article.locator("strong").filter({ hasText: "Candidate Vote Share =" })).toHaveText("Candidate Vote Share = (Candidate Votes ÷ Total Contest Votes) × 100");
  await expect(article.locator("em")).toHaveText("Not contested");
  await expect(article.getByRole("link", { name: "Arizona Secretary of State", exact: true })).toHaveAttribute("href", "https://azsos.gov/elections");
  await expect(article.locator("section").first().locator("p")).toHaveCount(7);
  await expect(article.locator("section").last().locator("p")).toHaveCount(3);
  await expect(article.locator("section").first().locator("strong")).toHaveText("This is not a commercial product or an official election information service.");
  await expect(article.getByRole("heading", { name: "About This Project", exact: true })).toHaveCount(1);
  await expect(article.getByRole("heading").filter({ hasText: /^(Top section|Bottom section)$/ })).toHaveCount(0);
  await expect(article.getByRole("link", { name: "← Back to election catalog" })).toHaveAttribute("href", "/");
  for (const width of [1280, 390, 320]) {
    await page.setViewportSize({ width, height: 900 });
    expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBeLessThanOrEqual(width);
    const overflow = await article.locator("h1, h2, h3, p, li").evaluateAll((elements) => elements.some((element) => element.scrollWidth > element.clientWidth));
    expect(overflow).toBe(false);
  }
  await page.setViewportSize({ width: 1280, height: 900 });
  await page.screenshot({ path: "test-results/methodology-desktop.png" });
  await page.setViewportSize({ width: 390, height: 844 });
  await page.screenshot({ path: "test-results/methodology-mobile.png" });
  await article.getByRole("link", { name: "← Back to election catalog" }).click();
  await expect(page).toHaveURL(/\/$/);
});
