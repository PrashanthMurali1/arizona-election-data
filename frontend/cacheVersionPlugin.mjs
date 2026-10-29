import { createHash } from "node:crypto";
import { readdirSync, readFileSync } from "node:fs";
import { resolve, relative, isAbsolute } from "node:path";

// Content-based, so rebuilding unchanged frontend files preserves cached data.
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
    resolveId(source) {
      if (source === id) return resolvedId;
    },
    load(source) {
      if (source === resolvedId)
        return `export default ${JSON.stringify(frontendVersion(root))};`;
    },
    handleHotUpdate({ file, server }) {
      const changed = relative(resolve(root, "src"), file);
      if (
        ((changed.startsWith("..") || isAbsolute(changed)) &&
          file !== resolve(root, "index.html")) ||
        /\.(test|spec)\./.test(file)
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
