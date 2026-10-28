import { test, expect } from "@playwright/test";
import { execFileSync } from "node:child_process";
import { resolve } from "node:path";

test("production imports reach an open browser and reconnect recovers missed imports", async ({ page, context }) => {
  test.skip(!process.env.PLAYWRIGHT_BASE_URL, "Requires the private production Compose stack and active scheduler");
  test.setTimeout(120_000);
  const refresh = () => execFileSync("docker", ["compose", "exec", "--user", "app", "scheduler", "python", "production/refresh_job.py"],
    { cwd: resolve(".."), timeout: 90_000, stdio: "pipe" });
  const activityPath = "/api/elections/az-2026-early-voting/activity";
  await page.goto("/elections/az-2026-early-voting");
  await page.getByRole("button", {name: "Pima County. View early-voting activity."}).click();
  const details = page.getByRole("region", {name: "Selected county details"});
  const table = page.getByRole("region", {name: "County participation table"});
  await table.getByRole("button", {name: "Returned", exact: false}).click();
  const before = await (await page.request.get(activityPath)).json();
  const delivered = page.waitForResponse((response) => response.url().endsWith(activityPath));
  refresh();
  const updated = await (await delivered).json();
  expect(updated.revision).not.toBe(before.revision);
  await expect(details.getByRole("heading", {name: "Pima County"})).toBeVisible();
  await expect(table.locator('th[aria-sort="ascending"]')).toContainText("Returned");
  await expect(page.locator('.county-map path[aria-label^="Pima County."]')).toHaveClass(/selected/);

  await context.setOffline(true);
  await page.evaluate(() => document.dispatchEvent(new Event("visibilitychange")));
  refresh(); // Import commits while this browser cannot receive its notification.
  const recovered = page.waitForResponse((response) => response.url().endsWith(activityPath));
  await context.setOffline(false);
  await page.evaluate(() => document.dispatchEvent(new Event("visibilitychange")));
  expect((await (await recovered).json()).revision).not.toBe(updated.revision);
  await expect(details.getByRole("heading", {name: "Pima County"})).toBeVisible();
  await expect(table.locator('th[aria-sort="ascending"]')).toContainText("Returned");
  await expect(page.locator(".sources")).not.toContainText("Update connection interrupted");
});
