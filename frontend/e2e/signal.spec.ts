import { test, expect } from "@playwright/test";
import { selectOffice } from "./helpers";

test("theme switching preserves historical selection, sorting, disclosure and cached data", async ({
  page,
}) => {
  const requests: string[] = [];
  page.on("request", (request) => {
    if (request.url().includes("/api/")) requests.push(request.url());
  });
  await page.goto("/elections/az-2022-governor");
  await expect(page.locator("html")).toHaveAttribute("data-theme", "dark");
  await expect(page.getByLabel("Election year").locator("option")).toHaveCount(
    3,
  );
  const table = page.getByRole("region", { name: "County results table" });
  const details = page.getByRole("region", { name: "Selected county details" });
  await table.getByRole("button", { name: "Pima", exact: true }).click();
  await table.getByRole("button", { name: "County", exact: true }).click();
  const roster = page.locator(".statewide details.roster");
  await roster.locator("summary").click();
  const before = requests.length;
  const figures = await page.locator(".statewide").innerText();
  for (const theme of ["Light", "Dark", "Light"]) {
    await page
      .getByRole("button", { name: `${theme} theme`, exact: true })
      .click();
    await expect(page.locator("html")).toHaveAttribute(
      "data-theme",
      theme.toLowerCase(),
    );
    await expect(
      page.getByRole("button", { name: `${theme} theme`, exact: true }),
    ).toHaveAttribute("aria-pressed", "true");
    await expect(
      details.getByRole("heading", { name: "Pima County", exact: true }),
    ).toBeVisible();
    await expect(table.locator('th[aria-sort="ascending"]')).toContainText(
      "County",
    );
    await expect(roster).toHaveJSProperty("open", true);
    expect(await page.locator(".statewide").innerText()).toEqual(figures);
  }
  expect(requests.length).toBe(before);
  await page.reload();
  await expect(page.locator("html")).toHaveAttribute("data-theme", "light");
  await page
    .getByRole("navigation", { name: "Main navigation" })
    .getByRole("link", { name: "About the data" })
    .click();
  await expect(page.locator("html")).toHaveAttribute("data-theme", "light");
  await expect(
    page.getByRole("heading", {
      name: "Data Sources & Methodology",
      exact: true,
    }),
  ).toBeVisible();
});

test("changing themes does not reconnect or refetch the embedded participation dashboard", async ({
  page,
}) => {
  await page.addInitScript(() => {
    const state = { created: 0, closed: 0, active: 0 };
    (window as unknown as { signalStreams: typeof state }).signalStreams =
      state;
    class Source extends EventTarget {
      constructor() {
        super();
        state.created++;
        state.active++;
      }
      close() {
        state.closed++;
        state.active--;
      }
    }
    window.EventSource = Source as unknown as typeof EventSource;
  });
  let activityRequests = 0;
  page.on("request", (r) => {
    if (r.url().includes("/az-2026-early-voting/activity")) activityRequests++;
  });
  await page.goto("/");
  await page
    .getByRole("button", {
      name: /^Pima County\. View early-voting activity\./,
    })
    .click();
  const table = page.getByRole("region", {
    name: "County participation table",
  });
  await table
    .getByRole("button", {
      name: "Total Early Votes (Returned Ballots)",
      exact: false,
    })
    .click();
  const before = await page.evaluate(
    () =>
      (
        window as unknown as {
          signalStreams: { created: number; closed: number; active: number };
        }
      ).signalStreams,
  );
  const requestCount = activityRequests;
  const figures = await page
    .getByRole("region", { name: "Statewide participation availability" })
    .innerText();
  await page.getByRole("button", { name: "Light theme", exact: true }).click();
  await page.getByRole("button", { name: "Dark theme", exact: true }).click();
  await expect(
    page
      .getByRole("region", { name: "Selected county details" })
      .getByRole("heading", { name: "Pima County", exact: true }),
  ).toBeVisible();
  await expect(table.locator('th[aria-sort="ascending"]')).toContainText(
    "Total Early Votes",
  );
  expect(
    await page
      .getByRole("region", { name: "Statewide participation availability" })
      .innerText(),
  ).toEqual(figures);
  expect(activityRequests).toBe(requestCount);
  expect(
    await page.evaluate(
      () => (window as unknown as { signalStreams: unknown }).signalStreams,
    ),
  ).toEqual(before);
});

test("office navigation and selected theme survive switching between catalog categories", async ({
  page,
}) => {
  await page.goto("/");
  await page.getByRole("button", { name: "Light theme", exact: true }).click();
  await page.getByRole("tab", { name: "State Elections", exact: true }).click();
  await selectOffice(page, "State office", "attorney-general");
  await page.getByRole("button", { name: "Dark theme", exact: true }).click();
  await expect(page.getByLabel("State office", { exact: true })).toHaveValue(
    "attorney-general",
  );
  await page.setViewportSize({ width: 390, height: 844 });
  await selectOffice(page, "State office", "governor");
  await page.getByRole("button", { name: "Light theme", exact: true }).click();
  await expect(page.getByLabel("State office", { exact: true })).toHaveValue(
    "governor",
  );
  await expect(page.locator("html")).toHaveAttribute("data-theme", "light");
});

test("theme controls work when browser preference storage is unavailable", async ({
  page,
}) => {
  await page.addInitScript(() => {
    Object.defineProperty(Storage.prototype, "getItem", {
      value() {
        throw new DOMException("Storage unavailable", "SecurityError");
      },
    });
    Object.defineProperty(Storage.prototype, "setItem", {
      value() {
        throw new DOMException("Storage unavailable", "SecurityError");
      },
    });
  });
  const errors: string[] = [];
  page.on("pageerror", (e) => errors.push(e.message));
  await page.goto("/methodology");
  await expect(page.locator("html")).toHaveAttribute("data-theme", "dark");
  await page.getByRole("button", { name: "Light theme", exact: true }).click();
  await expect(page.locator("html")).toHaveAttribute("data-theme", "light");
  await page.getByRole("button", { name: "Dark theme", exact: true }).focus();
  await page.keyboard.press("Enter");
  await expect(page.locator("html")).toHaveAttribute("data-theme", "dark");
  expect(errors).toEqual([]);
});

test("closing geographic detail returns keyboard focus to the initiating table control", async ({
  page,
}) => {
  await page.goto("/elections/az-2022-governor");
  const table = page.getByRole("region", { name: "County results table" });
  const county = table.getByRole("button", { name: "Pima", exact: true });
  await county.focus();
  await page.keyboard.press("Enter");
  await expect(
    page.getByRole("region", { name: "Selected county details" }),
  ).toBeFocused();
  await page
    .getByRole("button", { name: "Close county details", exact: true })
    .click();
  await expect(county).toBeFocused();
});

for (const id of ["az-2014-us-house", "az-2018-us-house-special-08"]) {
  test(`closing initially open district details retains keyboard focus: ${id}`, async ({
    page,
  }) => {
    await page.goto(`/elections/${id}`);
    const table = page.getByRole("region", { name: "District results table" });
    const selected = table.locator('tbody button[aria-pressed="true"]');
    const close = page.getByRole("button", {
      name: "Close district details",
      exact: true,
    });
    await close.focus();
    await page.keyboard.press("Enter");
    await expect(selected).toBeFocused();
    await page.keyboard.press("Enter");
    await expect(
      page.getByRole("region", { name: "Selected district details" }),
    ).toBeFocused();
    await close.focus();
    await page.keyboard.press("Enter");
    await expect(selected).toBeFocused();
  });
}
