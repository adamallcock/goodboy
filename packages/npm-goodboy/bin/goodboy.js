#!/usr/bin/env node

import { spawnSync } from "node:child_process";

const VERSION = "0.1.0";
const args = process.argv.slice(2);

function printHelp() {
  console.log(`Goodboy npm launcher ${VERSION}

Goodboy is a Python-first CLI for creating Codex pet packages from reference images.
This npm package gives Node/npm users a friendly entrypoint without auto-installing
Python dependencies behind their back.

Recommended setup:
  python3 -m pip install "goodboy @ git+https://github.com/adamallcock/goodboy.git"

Then run:
  npx @adamallcock/goodboy --help
  npx @adamallcock/goodboy start <project-dir> --pet-id <id> --display-name <name> --species dog --source <image>
  npx @adamallcock/goodboy advance <project-dir> --agent-mode

Environment:
  GOODBOY_PYTHON=/path/to/python  Choose the Python interpreter used to run Goodboy.
`);
}

function pythonCandidates() {
  const configured = process.env.GOODBOY_PYTHON;
  return configured ? [configured] : ["python3", "python"];
}

if (args.includes("--version") || args.includes("-v")) {
  console.log(VERSION);
  process.exit(0);
}

if (args.length === 0 || args.includes("--help") || args.includes("-h")) {
  printHelp();
  process.exit(0);
}

let lastError = "";
for (const python of pythonCandidates()) {
  const result = spawnSync(python, ["-m", "goodboy.cli", ...args], {
    stdio: "inherit"
  });

  if (result.error) {
    lastError = result.error.message;
    continue;
  }

  process.exit(result.status ?? 0);
}

console.error(`Goodboy could not start Python Goodboy CLI.

Install Goodboy first:
  python3 -m pip install "goodboy @ git+https://github.com/adamallcock/goodboy.git"

Then retry:
  npx goodboy ${args.join(" ")}

Last launcher error: ${lastError || "Python executable not found"}`);
process.exit(1);
