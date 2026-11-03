/** Real HTTP cache integration: no page/context routing (routing disables Chromium's cache).
 * Run with PLAYWRIGHT_BASE_URL=http://127.0.0.1:1 to skip the normal backend/dev servers.
 * This spec builds a temporary production frontend and serves only controlled fixtures.
 */
import { test, expect } from "@playwright/test";
import { createServer, type ServerResponse } from "node:http";
import { execFileSync } from "node:child_process";
import {
  mkdtempSync,
  readFileSync,
  existsSync,
  statSync,
  rmSync,
} from "node:fs";
import { tmpdir } from "node:os";
import path from "node:path";
import { midtermResults } from "./helpers";

type Hit = {
  office: string;
  validator: string | undefined;
  status: number;
  completed: boolean;
  governorValidationStartedAtStart: boolean;
};
let origin: string, build: string;
let revision = "fixture";
const retrievedAt = new Date().toISOString();
let hits: Hit[] = [];
let active = 0,
  maximum = 0;
let holdGovernorValidation = false;
let releaseGovernorValidation: (() => void) | undefined;
const streams = new Set<ServerResponse>();
const server = createServer(async (req, res) => {
  const url = new URL(req.url!, "http://localhost");
  if (url.pathname === "/api/midterm-2026/updates") {
    res.writeHead(200, {
      "Content-Type": "text/event-stream",
      "Cache-Control": "no-store",
      Connection: "keep-alive",
    });
    res.write(`event: revision\ndata: ${JSON.stringify({ revision })}\n\n`);
    streams.add(res);
    req.on("close", () => streams.delete(res));
    return;
  }
  if (url.pathname === "/api/midterm-2026") {
    const office = url.searchParams.get("office") || "governor";
    const tag = `"${revision}:${office}"`;
    const hit = {
      office,
      validator: req.headers["if-none-match"],
      status: req.headers["if-none-match"] === tag ? 304 : 200,
      completed: false,
      governorValidationStartedAtStart: hits.some(
        (hit) => hit.office === "governor" && hit.status === 304,
      ),
    };
    hits.push(hit);
    maximum = Math.max(maximum, ++active);
    if (holdGovernorValidation && office === "governor" && hit.status === 304)
      await new Promise<void>((resolve) => {
        releaseGovernorValidation = resolve;
      });
    await new Promise((resolve) => setTimeout(resolve, 100));
    const value = midtermResults();
    value.revision = revision;
    // Stable body per revision: retrieval time is irrelevant to these assertions; keep the ETag truthful.
    value.retrieved_at = retrievedAt;
    const body = JSON.stringify({
      ...value,
      offices: {
        [office]: value.offices[office as keyof typeof value.offices],
      },
    });
    res.writeHead(hit.status, {
      "Content-Type": "application/json",
      ETag: tag,
      "Cache-Control": "private, max-age=60, must-revalidate",
    });
    res.end(hit.status === 304 ? undefined : body);
    hit.completed = true;
    active--;
    return;
  }
  if (url.pathname.startsWith("/api/")) {
    res.writeHead(200, {
      "Content-Type": "application/json",
      "Cache-Control": "no-store",
    });
    res.end(
      JSON.stringify(
        url.pathname === "/api/elections"
          ? []
          : { boundary_id: "county-2022", vintage: "2022", features: [] },
      ),
    );
    return;
  }
  if (url.pathname === "/blank") {
    res.end("<!doctype html><title>HTTP cache test</title>");
    return;
  }
  let file = path.join(build, decodeURIComponent(url.pathname));
  if (!existsSync(file) || statSync(file).isDirectory())
    file = path.join(build, "index.html");
  res.writeHead(200, {
    "Content-Type":
      (
        {
          ".html": "text/html",
          ".js": "text/javascript",
          ".css": "text/css",
        } as Record<string, string>
      )[path.extname(file)] || "application/octet-stream",
  });
  res.end(readFileSync(file));
});

test.beforeAll(async () => {
  build = mkdtempSync(path.join(tmpdir(), "midterm-http-cache-"));
  execFileSync(
    process.execPath,
    [
      path.resolve("node_modules/vite/bin/vite.js"),
      "build",
      "--configLoader",
      "runner",
      "--outDir",
      build,
      "--emptyOutDir",
    ],
    { cwd: process.cwd(), stdio: "pipe" },
  );
  await new Promise<void>((resolve) => server.listen(0, "127.0.0.1", resolve));
  origin = `http://127.0.0.1:${(server.address() as { port: number }).port}`;
});
test.beforeEach(() => {
  hits = [];
  active = maximum = 0;
  revision = "fixture";
  holdGovernorValidation = false;
});
test.afterEach(() => {
  releaseGovernorValidation?.();
  releaseGovernorValidation = undefined;
});
test.afterAll(async () => {
  for (const stream of streams) stream.end();
  server.closeAllConnections();
  await new Promise<void>((resolve) => server.close(() => resolve()));
  if (build) rmSync(build, { recursive: true, force: true });
});

test("real default HTTP reuse and no-cache conditional 304 preserve the cached JSON body", async ({
  page,
}) => {
  await page.goto(`${origin}/blank`);
  const load = (cache: RequestCache = "default") =>
    page.evaluate(async (cache) => {
      const response = await fetch("/api/midterm-2026?office=governor", {
        cache,
      });
      return {
        status: response.status,
        etag: response.headers.get("etag"),
        body: await response.json(),
      };
    }, cache);
  const first = await load();
  expect(hits).toHaveLength(1);
  expect(hits[0].status).toBe(200);
  expect(await load()).toEqual(first);
  expect(hits).toHaveLength(1);
  await page.reload();
  expect(await load()).toEqual(first);
  expect(hits).toHaveLength(1);
  expect(await load("no-cache")).toEqual(first);
  expect(hits).toHaveLength(2);
  expect(hits[1]).toMatchObject({
    status: 304,
    validator: first.etag,
    completed: true,
  });
});

test("app uses Governor first, bounded HTTP prefetch and SSE updates without persistent result copies", async ({
  page,
}) => {
  holdGovernorValidation = true;
  await page.goto(origin);
  const panel = page.getByRole("tabpanel", { name: "2026 Midterm Results" });
  await expect(
    panel.getByRole("heading", { name: "Statewide candidate results" }),
  ).toBeVisible();
  expect(hits[0].office).toBe("governor");
  await expect
    .poll(
      () =>
        new Set(hits.filter((hit) => hit.completed).map((hit) => hit.office))
          .size,
    )
    .toBe(6);
  expect(
    hits.filter((hit) => hit.office === "governor").map((hit) => hit.status),
  ).toEqual([200, 304]);
  expect(
    hits
      .filter((hit) => hit.office !== "governor")
      .every((hit) => hit.governorValidationStartedAtStart),
  ).toBe(true);
  // All five offices warmed while Governor's validation was deliberately held.
  expect(hits.filter((hit) => hit.office === "governor").at(-1)).toMatchObject({
    status: 304,
    completed: false,
  });
  expect(maximum).toBeLessThanOrEqual(2);
  releaseGovernorValidation!();
  releaseGovernorValidation = undefined;
  holdGovernorValidation = false;
  await expect.poll(() => active).toBe(0);
  const storage = await page.evaluate(() => ({
    local: { ...localStorage },
    session: { ...sessionStorage },
  }));
  expect(JSON.stringify(storage)).not.toMatch(
    /offices|candidates|retrieved_at/,
  );
  // Leave Chromium's disk/memory HTTP cache intact and clear the app's module cache by reloading.
  holdGovernorValidation = true;
  await page.reload();
  await expect.poll(() => !!releaseGovernorValidation).toBe(true);
  await expect(
    panel.getByRole("heading", { name: "Statewide candidate results" }),
  ).toBeVisible();
  expect(hits.filter((hit) => hit.office === "governor").at(-1)).toMatchObject({
    status: 304,
    completed: false,
  });
  releaseGovernorValidation!();
  releaseGovernorValidation = undefined;
  holdGovernorValidation = false;
  await expect.poll(() => active).toBe(0);
  const count = hits.length;
  revision = "published-2";
  for (const stream of streams)
    stream.write(`event: revision\ndata: ${JSON.stringify({ revision })}\n\n`);
  await expect
    .poll(
      () =>
        new Set(
          hits
            .slice(count)
            .filter((hit) => hit.completed)
            .map((hit) => hit.office),
        ).size,
    )
    .toBe(6);
  expect(hits.slice(count).every((hit) => !!hit.validator)).toBe(true);
  expect(hits.slice(count).every((hit) => hit.status === 200)).toBe(true);
  expect(maximum).toBeLessThanOrEqual(2);
  const beforeSwitch = hits.length;
  await panel
    .getByRole("navigation", { name: "Midterm office directory" })
    .getByRole("button", { name: "Attorney General", exact: true })
    .click();
  await expect(
    panel.getByRole("heading", { name: "Attorney General", exact: true }),
  ).toBeVisible();
  expect(hits).toHaveLength(beforeSwitch);
});
