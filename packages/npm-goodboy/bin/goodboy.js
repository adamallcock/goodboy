#!/usr/bin/env node

import { spawnSync } from "node:child_process";
import { existsSync, realpathSync } from "node:fs";
import { join } from "node:path";
import { fileURLToPath } from "node:url";

const VERSION = "0.2.1";
const RUNTIME_SPEC = `goodboy-codex[ui]==${VERSION}`;
const args = process.argv.slice(2);
const launcherPath = realpathSync(fileURLToPath(import.meta.url));

function printHelp() {
  console.log(`Goodboy npm launcher ${VERSION}

Goodboy is a Python-first studio for creating source-faithful Codex pet v2 packages.
For Codex, install the Goodboy plugin; it checks and offers to bootstrap its matching
runtime on first use. This npm package remains a standalone launcher and never installs
Python dependencies without permission.

Recommended setup:
  uv tool install "${RUNTIME_SPEC}"

Then run:
  npx @adamallcock/goodboy --help
  npx @adamallcock/goodboy start <project-dir> --pet-id <id> --display-name <name> --species dog --source <image>
  npx @adamallcock/goodboy advance <project-dir> --agent-mode

Environment:
  GOODBOY_COMMAND=/path/to/goodboy  Choose an existing Goodboy executable.
  GOODBOY_PYTHON=/path/to/python  Choose the Python interpreter used to run Goodboy.
  GOODBOY_UV_COMMAND=/path/to/uv  Choose uv for tool-bin discovery.
`);
}

function sameExecutable(path) {
  try {
    return realpathSync(path) === launcherPath;
  } catch {
    return false;
  }
}

function uvRuntime() {
  const uv = process.env.GOODBOY_UV_COMMAND || "uv";
  const result = spawnSync(uv, ["tool", "dir", "--bin"], {
    encoding: "utf8",
    shell: false
  });
  if (result.error || result.status !== 0) {
    return null;
  }
  const binDir = String(result.stdout || "").trim().split(/\r?\n/u).at(-1);
  if (!binDir) {
    return null;
  }
  const command = join(binDir, process.platform === "win32" ? "goodboy.exe" : "goodboy");
  return existsSync(command) && !sameExecutable(command) ? command : null;
}

function runtimeCandidates() {
  const candidates = [];
  if (process.env.GOODBOY_COMMAND) {
    candidates.push({ command: process.env.GOODBOY_COMMAND, prefix: [] });
  }
  const managed = uvRuntime();
  if (managed) {
    candidates.push({ command: managed, prefix: [] });
  }
  const pythons = process.env.GOODBOY_PYTHON
    ? [process.env.GOODBOY_PYTHON]
    : ["python3", "python"];
  for (const python of pythons) {
    candidates.push({ command: python, prefix: ["-m", "goodboy.cli"] });
  }
  return candidates;
}

function runtimeVersion(candidate) {
  const result = spawnSync(candidate.command, [...candidate.prefix, "--version"], {
    encoding: "utf8",
    shell: false
  });
  const output = `${result.stdout || ""}\n${result.stderr || ""}`.trim();
  const match = output.match(/(?:^|\s)goodboy\s+v?(\d+\.\d+\.\d+)(?:\s|$)/iu)
    || output.match(/^v?(\d+\.\d+\.\d+)$/u);
  return {
    ...result,
    output,
    version: match ? match[1] : null
  };
}

if (args.includes("--version") || args.includes("-v")) {
  console.log(VERSION);
  process.exit(0);
}

if (args.length === 0 || args.includes("--help") || args.includes("-h")) {
  printHelp();
  process.exit(0);
}

const runtimeErrors = [];
for (const candidate of runtimeCandidates()) {
  if (sameExecutable(candidate.command)) {
    runtimeErrors.push(`${candidate.command}: candidate resolves to this npm launcher`);
    continue;
  }
  const checked = runtimeVersion(candidate);
  if (checked.error) {
    runtimeErrors.push(`${candidate.command}: ${checked.error.message}`);
    continue;
  }
  if (checked.status !== 0 || !checked.version) {
    runtimeErrors.push(`${candidate.command}: ${checked.output || `version check exited ${checked.status}`}`);
    continue;
  }
  if (checked.version !== VERSION) {
    runtimeErrors.push(`${candidate.command}: found Goodboy ${checked.version}; launcher requires ${VERSION}`);
    continue;
  }

  const result = spawnSync(candidate.command, [...candidate.prefix, ...args], {
    stdio: "inherit",
    shell: false
  });

  if (result.error) {
    runtimeErrors.push(`${candidate.command}: ${result.error.message}`);
    continue;
  }

  process.exit(result.status ?? 0);
}

console.error(`Goodboy could not start a compatible Goodboy ${VERSION} runtime.

Install Goodboy first:
  uv tool install "${RUNTIME_SPEC}"

Then retry:
  npx @adamallcock/goodboy ${args.join(" ")}

Runtime checks: ${runtimeErrors.join("; ") || "compatible Goodboy runtime not found"}`);
process.exit(1);
