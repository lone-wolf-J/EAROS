import { readFileSync, readdirSync, statSync } from "node:fs";
import { join, relative, resolve } from "node:path";

const sourceRoot = resolve("src");
const docsRoot = resolve("../docs");
const historicalDocAllowlist = new Set(["ATS_IMPLEMENTATION_DECISION.md"]);
const legacyProductName = /\btalentflow\b/i;

function collectFiles(directory) {
  return readdirSync(directory).flatMap((entry) => {
    const path = join(directory, entry);
    return statSync(path).isDirectory() ? collectFiles(path) : [path];
  });
}

const sourceViolations = collectFiles(sourceRoot)
  .filter((file) => /\.(?:js|jsx|ts|tsx|css|html|md)$/i.test(file))
  .flatMap((file) => legacyProductName.test(readFileSync(file, "utf8")) ? [relative(process.cwd(), file)] : []);

const documentationViolations = collectFiles(docsRoot)
  .filter((file) => file.endsWith(".md") && !historicalDocAllowlist.has(relative(docsRoot, file)))
  .flatMap((file) => legacyProductName.test(readFileSync(file, "utf8")) ? [relative(process.cwd(), file)] : []);

const violations = [...sourceViolations, ...documentationViolations];
if (violations.length) {
  throw new Error(`Legacy product branding appears outside approved historical or internal exceptions:\n${violations.join("\n")}`);
}

console.log("Verified active EAROS source and documentation contain no legacy product-facing TalentFlow branding.");
