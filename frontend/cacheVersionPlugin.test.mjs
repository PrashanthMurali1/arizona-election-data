import { test } from "node:test";
import assert from "node:assert/strict";
import { mkdtempSync, mkdirSync, writeFileSync, rmSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { frontendVersion, cacheVersionPlugin } from "./cacheVersionPlugin.mjs";

test("source/style/HTML changes invalidate versions; unchanged builds and test edits preserve them", () => {
  const root = mkdtempSync(join(tmpdir(), "election-cache-version-"));
  try {
    mkdirSync(join(root, "src"));
    const source = join(root, "src", "page.tsx");
    writeFileSync(source, "first");
    writeFileSync(join(root, "index.html"), "html");
    const first = frontendVersion(root);
    assert.equal(frontendVersion(root), first);
    writeFileSync(join(root, "src", "page.test.tsx"), "test only");
    assert.equal(frontendVersion(root), first);
    writeFileSync(source, "second");
    assert.notEqual(frontendVersion(root), first);
    const second = frontendVersion(root);
    writeFileSync(join(root, "src", "styles.css"), "body {color:green}");
    assert.notEqual(frontendVersion(root), second);
    const plugin = cacheVersionPlugin();
    plugin.configResolved({ root });
    const id = plugin.resolveId("virtual:election-cache-version");
    const oldModule = plugin.load(id);
    writeFileSync(join(root, "index.html"), "changed html");
    assert.notEqual(plugin.load(id), oldModule);
    let invalidated = false;
    let reloaded = false;
    plugin.handleHotUpdate({
      file: source,
      server: {
        moduleGraph: {
          getModuleById: () => ({}),
          invalidateModule: () => {
            invalidated = true;
          },
        },
        ws: {
          send: (event) => {
            reloaded = event.type === "full-reload";
          },
        },
      },
    });
    assert.ok(invalidated && reloaded);
  } finally {
    rmSync(root, { recursive: true, force: true });
  }
});

test("historical data corrections invalidate the API cache version", () => {
  const project = mkdtempSync(join(tmpdir(), "election-data-version-"));
  const root = join(project, "frontend");
  try {
    mkdirSync(join(root, "src"), { recursive: true });
    writeFileSync(join(root, "index.html"), "html");
    const dir = join(project, "data/raw/early-canvasses");
    mkdirSync(dir, { recursive: true });
    const source = join(dir, "1911.json");
    writeFileSync(source, '{"votes":null}');
    const before = frontendVersion(root);
    writeFileSync(source, '{"votes":10476}');
    assert.notEqual(frontendVersion(root), before);
    const plugin = cacheVersionPlugin();
    plugin.configResolved({ root });
    let reload = false;
    plugin.handleHotUpdate({ file: source, server: {
      moduleGraph: { getModuleById: () => null },
      ws: { send: () => { reload = true; } },
    } });
    assert.ok(reload);
  } finally {
    rmSync(project, { recursive: true, force: true });
  }
});
