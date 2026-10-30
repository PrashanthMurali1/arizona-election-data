import { expect, type Page } from "@playwright/test";

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
