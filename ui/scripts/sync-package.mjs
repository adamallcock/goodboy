import { createHash } from "node:crypto";
import { mkdir, readdir, readFile, rm, stat, writeFile } from "node:fs/promises";
import { dirname, extname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const scriptDir = dirname(fileURLToPath(import.meta.url));
const uiDir = resolve(scriptDir, "..");
const sourceDir = resolve(uiDir, "dist");
const targetDir = resolve(uiDir, "..", "src", "goodboy", "web", "static");
const checkOnly = process.argv.includes("--check");
const normalizedTextExtensions = new Set([".css", ".html", ".js", ".json", ".md", ".txt"]);

async function filesUnder(root, prefix = "") {
  const entries = await readdir(resolve(root, prefix), { withFileTypes: true });
  const files = [];
  for (const entry of entries) {
    const relative = prefix ? `${prefix}/${entry.name}` : entry.name;
    if (entry.isDirectory()) {
      files.push(...await filesUnder(root, relative));
    } else if (entry.isFile()) {
      files.push(relative);
    }
  }
  return files.sort();
}

async function packagedBytes(path) {
  const contents = await readFile(path);
  if (!normalizedTextExtensions.has(extname(path))) {
    return contents;
  }
  return Buffer.from(contents.toString("utf8").replace(/[\t ]+$/gmu, ""));
}

async function digest(path, normalize = false) {
  const contents = normalize ? await packagedBytes(path) : await readFile(path);
  return createHash("sha256").update(contents).digest("hex");
}

if (!(await stat(sourceDir).catch(() => null))?.isDirectory()) {
  throw new Error("ui/dist is missing; run `npm run build` first");
}

if (checkOnly) {
  if (!(await stat(targetDir).catch(() => null))?.isDirectory()) {
    throw new Error("packaged Review Room assets are missing; run `npm run build:package`");
  }
  const sourceFiles = await filesUnder(sourceDir);
  const targetFiles = await filesUnder(targetDir);
  if (JSON.stringify(sourceFiles) !== JSON.stringify(targetFiles)) {
    throw new Error("packaged Review Room file list is stale; run `npm run build:package`");
  }
  for (const relative of sourceFiles) {
    const [sourceHash, targetHash] = await Promise.all([
      digest(resolve(sourceDir, relative), true),
      digest(resolve(targetDir, relative))
    ]);
    if (sourceHash !== targetHash) {
      throw new Error(`packaged Review Room asset is stale: ${relative}`);
    }
  }
  console.log(`Packaged Review Room is current (${sourceFiles.length} files).`);
} else {
  await rm(targetDir, { recursive: true, force: true });
  for (const relative of await filesUnder(sourceDir)) {
    const target = resolve(targetDir, relative);
    await mkdir(dirname(target), { recursive: true });
    await writeFile(target, await packagedBytes(resolve(sourceDir, relative)));
  }
  console.log(`Synced ${sourceDir} to ${targetDir}.`);
}
