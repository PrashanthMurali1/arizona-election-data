/** Controlled Chromium benchmark; run `node scripts/benchmark_midterm_browser.mjs`.
 * Builds HEAD and working frontend in temporary directories; no live API/database access.
 * Environment: BASELINE_REF, BASELINE_DELAY_MS (800), CURRENT_DELAY_MS (5), VIEWPORT_WIDTH (1440).
 */
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import http from 'node:http';
import { execFileSync } from 'node:child_process';
import { createRequire } from 'node:module';
import { fileURLToPath } from 'node:url';
const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const require = createRequire(path.join(root, 'frontend/package.json'));
const { chromium } = require('@playwright/test');
const temp = fs.mkdtempSync(path.join(os.tmpdir(), 'midterm-browser-'));
const ref = process.env.BASELINE_REF || '537313abe112017c8cd117256bcb92b9458682e2';
const viewport = { width: Number(process.env.VIEWPORT_WIDTH || 1440), height: Number(process.env.VIEWPORT_HEIGHT || 1000) };
const git = (...args) => execFileSync('git', args, { cwd: root });
const fixture = JSON.parse(execFileSync(path.join(root, '.venv/Scripts/python.exe'), ['-c', `
import json
from backend.app import midterm
from pathlib import Path
v=midterm.normalize(json.loads(Path('backend/tests/midterm_search.json').read_text()),'2026-11-04T01:00:00+00:00')
for office in midterm.STATEWIDE:
 for race in v['offices'][office]:
  race.counties=[midterm.County(fips=f'04{2*i+1:03d}',name=f'County {i+1}',percent_reporting=0,total_votes=0,candidates=race.candidates) for i in range(15)]
print(json.dumps(dict(midterm.to_json(v),revision='fixture',stale=False,refresh_error=None)))
`], { cwd: root, encoding: 'utf8' }));
const reports = [];
let browser;
try {
  browser = await chromium.launch({ headless: true });
  for (const version of ['baseline', 'current']) {
    const dir = path.join(temp, version); fs.mkdirSync(dir);
    if (version === 'baseline') {
      const files = git('ls-tree', '-r', '--name-only', ref, 'frontend').toString().trim().split(/\r?\n/);
      for (const file of files) {
        const dest = path.join(dir, file.slice('frontend/'.length));
        fs.mkdirSync(path.dirname(dest), { recursive: true });
        fs.writeFileSync(dest, git('show', `${ref}:${file}`));
      }
    } else fs.cpSync(path.join(root, 'frontend'), dir, { recursive: true,
      filter: source => !['node_modules', 'dist', 'test-results', 'playwright-report'].includes(path.basename(source)) });
    fs.symlinkSync(path.join(root, 'frontend/node_modules'), path.join(dir, 'node_modules'), 'junction');
    execFileSync(process.execPath, [path.join(root, 'frontend/node_modules/vite/bin/vite.js'), 'build', '--configLoader', 'runner'], { cwd: dir, stdio: 'pipe' });
    const delay = Number(version === 'baseline' ? process.env.BASELINE_DELAY_MS || 800 : process.env.CURRENT_DELAY_MS || 5);
    const records = []; let revision = 'fixture'; let forceDelay = null;
    const server = http.createServer(async (req, res) => {
      const url = new URL(req.url, 'http://localhost'); let body, type = 'application/json';
      if (url.pathname === '/api/midterm-2026') {
        const office = url.searchParams.get('office');
        body = JSON.stringify({ ...fixture, revision, offices: office ? { [office]: fixture.offices[office] } : fixture.offices });
        records.push({ url: req.url, bytes: Buffer.byteLength(body) });
        await new Promise(resolve => setTimeout(resolve, forceDelay ?? delay));
      } else if (url.pathname === '/api/elections') body = '[]';
      else if (url.pathname.startsWith('/api/')) body = JSON.stringify({ boundary_id: 'county-2022', vintage: '2022', features: [] });
      else {
        let file = path.join(dir, 'dist', decodeURIComponent(url.pathname));
        if (!fs.existsSync(file) || fs.statSync(file).isDirectory()) file = path.join(dir, 'dist/index.html');
        type = ({ '.html': 'text/html', '.js': 'text/javascript', '.css': 'text/css', '.svg': 'image/svg+xml' })[path.extname(file)] || 'application/octet-stream';
        body = fs.readFileSync(file);
      }
      res.writeHead(200, { 'Content-Type': type, 'Content-Length': Buffer.byteLength(body), 'Cache-Control': 'no-store' }); res.end(body);
    });
    await new Promise(resolve => server.listen(0, '127.0.0.1', resolve));
    const origin = `http://127.0.0.1:${server.address().port}`;
    const context = await browser.newContext({ viewport });
    await context.route('**/*', route => new URL(route.request().url()).origin === origin ? route.continue() : route.abort());
    await context.addInitScript(() => {
      window.benchmarkStreams = [];
      window.EventSource = class {
        static CLOSED = 2; readyState = 1; listeners = {};
        constructor() { window.benchmarkStreams.push(this); }
        addEventListener(type, listener) { this.listeners[type] = listener; }
        close() { this.readyState = 2; }
        emit(revision) { this.listeners.revision?.({ data: JSON.stringify({ revision }) }); }
      };
    });
    const page = await context.newPage();
    const panel = page.getByRole('tabpanel', { name: '2026 Midterm Results' });
    const visible = panel.getByRole('heading', { name: 'Statewide candidate results' });
    async function measure(name, action) {
      const begin = records.length, started = performance.now(); await action();
      await visible.waitFor({ state: 'visible' });
      await page.evaluate(() => new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve))));
      return { phase: name, governor_visible_ms: +(performance.now() - started).toFixed(1),
        results_requests: records.length - begin,
        results_body_bytes: records.slice(begin).reduce((sum, row) => sum + row.bytes, 0) };
    }
    const phases = [];
    phases.push(await measure('cold_navigation', () => page.goto(origin)));
    phases.push(await measure('warm_reload', () => page.reload()));
    phases.push(await measure('tab_revisit', async () => {
      await page.getByRole('tab', { name: 'Federal Elections', exact: true }).click();
      await page.getByRole('tab', { name: '2026 Midterm Results', exact: true }).click();
    }));
    // Select a county, then observe whether an SSE refresh preserves its DOM and scroll.
    await panel.getByRole('region', { name: 'County results table' }).getByRole('button', { name: /County 1/ }).first().click();
    const detail = panel.getByRole('region', { name: 'Selected county details' });
    await detail.getByRole('heading', { name: 'County 1 County', exact: true }).waitFor();
    await detail.evaluate(el => el.dataset.benchmarkPreserved = 'yes');
    const scrollBefore = await page.evaluate(() => { window.scrollTo(0, 250); return window.scrollY; });
    revision = 'updated'; forceDelay = 200;
    const beforeUpdate = records.length;
    await page.evaluate(() => window.benchmarkStreams.filter(s => s.readyState === 1).forEach(s => s.emit('updated')));
    await page.waitForTimeout(80);
    const during = { details_preserved: await detail.getByRole('heading', { name: 'County 1 County', exact: true }).count() === 1,
      scroll_preserved: await page.evaluate(() => window.scrollY) === scrollBefore };
    await page.waitForTimeout(300);
    const after = { details_preserved: await detail.getByRole('heading', { name: 'County 1 County', exact: true }).count() === 1,
      same_dom_node: await detail.getAttribute('data-benchmark-preserved') === 'yes',
      scroll_preserved: await page.evaluate(() => window.scrollY) === scrollBefore,
      results_requests: records.length - beforeUpdate };
    reports.push({ version, simulated_api_delay_ms: delay, phases, update_during: during, update_after: after });
    await context.close(); await new Promise(resolve => server.close(resolve));
  }
  console.log(JSON.stringify({ baseline_commit: git('rev-parse', ref).toString().trim(), viewport, reports,
    limitations: ['Controlled simulation: response delays are injected, not measured backend performance.',
      'Production frontend bundles in Chromium, one run per phase; navigation timings include app startup, automation and two animation frames.',
      'API/asset HTTP caching disabled equally; this script does not measure browser HTTP-cache reuse. Use midterm-http-cache.spec.ts for real cache/304 validation.',
      'Bytes are delivered uncompressed results JSON bodies, excluding headers/assets/SSE; 20 fixture races and synthetic county data.',
      'No live upstream, production database, or deployed website was accessed.'] }, null, 2));
} finally {
  await browser?.close();
  fs.rmSync(temp, { recursive: true, force: true });
}
