import { createHash } from "node:crypto";
import { existsSync, readdirSync, readFileSync } from "node:fs";
import { resolve, relative, isAbsolute } from "node:path";

const dataDirectories = (root) => [
  resolve(root, "../data/raw/early-canvasses"),
  resolve(root, "../data/raw/historical-canvasses"),
];
const within = (directory, file) => {
  const path = relative(directory, file);
  return !path.startsWith("..") && !isAbsolute(path);
};

// Corrections to historical data must also invalidate browser API caches.
export function frontendVersion(root) {
  const hash = createHash("sha256");
  function visit(dir) {
    for (const entry of readdirSync(dir, { withFileTypes: true }).sort((a, b) =>
      a.name.localeCompare(b.name),
    )) {
      const path = resolve(dir, entry.name);
      if (entry.isDirectory()) visit(path);
      else if (!/\.(test|spec)\./.test(entry.name)) {
        hash.update(relative(root, path));
        hash.update(readFileSync(path));
      }
    }
  }
  visit(resolve(root, "src"));
  for (const directory of dataDirectories(root)) {
    if (!existsSync(directory)) continue;
    for (const name of readdirSync(directory).filter((name) => name.endsWith(".json")).sort()) {
      hash.update(relative(root, resolve(directory, name)));
      hash.update(readFileSync(resolve(directory, name)));
    }
  }
  hash.update(readFileSync(resolve(root, "index.html")));
  return hash.digest("hex").slice(0, 16);
}

export function cacheVersionPlugin() {
  const id = "virtual:election-cache-version";
  const resolvedId = "\0" + id;
  let root;
  return {
    name: "election-cache-version",
    configResolved(config) {
      root = config.root;
    },
    configureServer(server) {
      server.watcher.add(dataDirectories(root));
    },
    resolveId(source) {
      if (source === id) return resolvedId;
    },
    load(source) {
      if (source === resolvedId)
        return `export default ${JSON.stringify(frontendVersion(root))};`;
    },
    handleHotUpdate({ file, server }) {
      const dataChanged = file.endsWith(".json") && dataDirectories(root).some((dir) => within(dir, file));
      const changed = relative(resolve(root, "src"), file);
      if (
        !dataChanged && (((changed.startsWith("..") || isAbsolute(changed)) &&
          file !== resolve(root, "index.html")) ||
        /\.(test|spec)\./.test(file))
      )
        return;
      const module = server.moduleGraph.getModuleById(resolvedId);
      if (module) server.moduleGraph.invalidateModule(module);
      // Keep the preview's URL namespace in sync with source/style edits too.
      server.ws.send({ type: "full-reload" });
      return [];
    },
  };
}
