import { readFileSync, readdirSync, statSync } from "node:fs";
import { join, resolve } from "node:path";

const distRoot = resolve("dist");
const prohibitedMarkers = [
  /react-refresh/i,
  /webpack-dev-server/i,
  /\bcraco\b/i,
  /emergent-(?:visual-)?editor/i,
  /visual[-_ ]editor(?:-runtime)?/i,
];

function collectFiles(directory) {
  return readdirSync(directory).flatMap((entry) => {
    const path = join(directory, entry);
    return statSync(path).isDirectory() ? collectFiles(path) : [path];
  });
}

const files = collectFiles(distRoot);
const violations = files.flatMap((file) => {
  const contents = readFileSync(file, "utf8");
  return prohibitedMarkers
    .filter((marker) => marker.test(contents))
    .map((marker) => `${file}: ${marker}`);
});

if (violations.length) {
  throw new Error(`Production artifact contains retired development runtime marker(s):\n${violations.join("\n")}`);
}

console.log(`Verified ${files.length} EAROS production artifact files contain no inherited development-only runtimes.`);
