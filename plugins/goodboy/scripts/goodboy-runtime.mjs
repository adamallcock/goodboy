#!/usr/bin/env node

import { spawnSync } from "node:child_process";
import { readFileSync } from "node:fs";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const SCRIPT_DIR = dirname(fileURLToPath(import.meta.url));
const PLUGIN_ROOT = resolve(SCRIPT_DIR, "..");
const CONTRACT_PATH = join(PLUGIN_ROOT, "runtime.json");
const CONTRACT = JSON.parse(readFileSync(CONTRACT_PATH, "utf8"));

const EXPECTED_VERSION = String(CONTRACT.version);
const COMMAND_NAME = String(CONTRACT.command);
const EXTRAS = Array.isArray(CONTRACT.extras) ? CONTRACT.extras.map(String) : [];
const EXTRA_SUFFIX = EXTRAS.length > 0 ? `[${EXTRAS.join(",")}]` : "";
const PACKAGE_SPEC = `${CONTRACT.distribution}${EXTRA_SUFFIX}==${EXPECTED_VERSION}`;

const EXIT = Object.freeze({
  ready: 0,
  usage: 2,
  missing: 10,
  mismatch: 11,
  invalid: 12,
  approvalRequired: 20,
  uvMissing: 21,
  installFailed: 22,
  postInstallFailed: 23
});

function executableName(name) {
  return process.platform === "win32" ? `${name}.exe` : name;
}

function runCaptured(command, args) {
  return spawnSync(command, args, {
    encoding: "utf8",
    env: process.env,
    shell: false
  });
}

function commandWorks(command, args = ["--version"]) {
  const result = runCaptured(command, args);
  return !result.error && result.status === 0;
}

function findUv() {
  const command = process.env.GOODBOY_UV_COMMAND || "uv";
  return commandWorks(command) ? command : null;
}

function uvToolBin(uvCommand) {
  if (!uvCommand) {
    return null;
  }
  const result = runCaptured(uvCommand, ["tool", "dir", "--bin"]);
  if (result.error || result.status !== 0) {
    return null;
  }
  const output = String(result.stdout || "").trim();
  return output ? output.split(/\r?\n/u).at(-1).trim() : null;
}

function parseVersion(output) {
  const text = String(output).trim();
  const match = text.match(/(?:^|\r?\n)\s*goodboy\s+v?(\d+\.\d+\.\d+(?:[-+][0-9A-Za-z.-]+)?)\s*(?:\r?\n|$)/iu)
    || text.match(/^v?(\d+\.\d+\.\d+(?:[-+][0-9A-Za-z.-]+)?)$/u);
  return match ? match[1] : null;
}

function runtimeCandidates({ preferUv = true } = {}) {
  const configured = process.env.GOODBOY_RUNTIME_COMMAND;
  if (configured) {
    return [configured];
  }

  const uvCommand = findUv();
  const uvBin = uvToolBin(uvCommand);
  const uvRuntime = uvBin ? join(uvBin, executableName(COMMAND_NAME)) : null;
  const candidates = preferUv ? [uvRuntime, COMMAND_NAME] : [COMMAND_NAME, uvRuntime];
  return [...new Set(candidates.filter(Boolean))];
}

function inspectRuntime(options = {}) {
  let firstMismatch = null;
  let firstInvalid = null;

  for (const command of runtimeCandidates(options)) {
    const result = runCaptured(command, ["--version"]);
    if (result.error && result.error.code === "ENOENT") {
      continue;
    }
    const combined = `${result.stdout || ""}\n${result.stderr || ""}`.trim();
    if (result.error || result.status !== 0) {
      firstInvalid ||= {
        status: "invalid",
        command,
        found_version: null,
        detail: combined || result.error?.message || `exited ${result.status}`
      };
      continue;
    }
    const foundVersion = parseVersion(combined);
    if (!foundVersion) {
      firstInvalid ||= {
        status: "invalid",
        command,
        found_version: null,
        detail: `could not parse version from: ${combined || "empty output"}`
      };
      continue;
    }
    if (foundVersion === EXPECTED_VERSION) {
      return {
        status: "ready",
        command,
        found_version: foundVersion,
        detail: "compatible runtime found"
      };
    }
    firstMismatch ||= {
      status: "mismatch",
      command,
      found_version: foundVersion,
      detail: `plugin requires ${EXPECTED_VERSION}, but this runtime is ${foundVersion}`
    };
  }

  return firstMismatch || firstInvalid || {
    status: "missing",
    command: null,
    found_version: null,
    detail: "no Goodboy runtime was found"
  };
}

function publicStatus(status) {
  return {
    ...status,
    expected_version: EXPECTED_VERSION,
    package_spec: PACKAGE_SPEC,
    installer: CONTRACT.installer
  };
}

function printStatus(status, stream = process.stdout) {
  stream.write(`${JSON.stringify(publicStatus(status))}\n`);
}

function exitForStatus(status) {
  if (status.status === "ready") {
    return EXIT.ready;
  }
  if (status.status === "missing") {
    return EXIT.missing;
  }
  if (status.status === "mismatch") {
    return EXIT.mismatch;
  }
  return EXIT.invalid;
}

function installRuntime(args) {
  const allowed = new Set(["--user-approved"]);
  const unexpected = args.filter((arg) => !allowed.has(arg));
  if (unexpected.length > 0) {
    process.stderr.write(`Unknown install option: ${unexpected.join(" ")}\n`);
    return EXIT.usage;
  }
  if (!args.includes("--user-approved")) {
    printStatus({
      status: "approval_required",
      command: null,
      found_version: null,
      detail: `ask the user before installing ${PACKAGE_SPEC}`
    }, process.stderr);
    return EXIT.approvalRequired;
  }

  const before = inspectRuntime();
  if (before.status === "ready") {
    printStatus(before);
    return EXIT.ready;
  }

  const uvCommand = findUv();
  if (!uvCommand) {
    printStatus({
      status: "uv_missing",
      command: null,
      found_version: before.found_version,
      detail: "uv is not available; do not install uv without separate user approval"
    }, process.stderr);
    return EXIT.uvMissing;
  }

  const install = spawnSync(uvCommand, ["tool", "install", PACKAGE_SPEC], {
    encoding: "utf8",
    env: process.env,
    shell: false
  });
  if (install.stdout) {
    process.stdout.write(install.stdout);
  }
  if (install.stderr) {
    process.stderr.write(install.stderr);
  }
  if (install.error || install.status !== 0) {
    printStatus({
      status: "install_failed",
      command: uvCommand,
      found_version: before.found_version,
      detail: install.error?.message || `uv exited ${install.status}`
    }, process.stderr);
    return EXIT.installFailed;
  }

  const after = inspectRuntime({ preferUv: true });
  if (after.status !== "ready") {
    printStatus({
      ...after,
      status: "post_install_failed",
      detail: `installation completed, but ${EXPECTED_VERSION} could not be verified: ${after.detail}`
    }, process.stderr);
    return EXIT.postInstallFailed;
  }
  printStatus(after);
  return EXIT.ready;
}

function runRuntime(args) {
  const separator = args[0] === "--" ? 1 : 0;
  const runtimeArgs = args.slice(separator);
  if (runtimeArgs.length === 0) {
    process.stderr.write("Usage: goodboy-runtime.mjs run -- <goodboy arguments>\n");
    return EXIT.usage;
  }

  const status = inspectRuntime();
  if (status.status !== "ready") {
    printStatus(status, process.stderr);
    return exitForStatus(status);
  }

  const result = spawnSync(status.command, runtimeArgs, {
    stdio: "inherit",
    env: process.env,
    shell: false
  });
  if (result.error) {
    process.stderr.write(`${result.error.message}\n`);
    return EXIT.invalid;
  }
  return result.status ?? EXIT.invalid;
}

function printUsage() {
  process.stdout.write(`Goodboy plugin runtime ${EXPECTED_VERSION}\n\n`);
  process.stdout.write("Usage:\n");
  process.stdout.write("  goodboy-runtime.mjs check\n");
  process.stdout.write("  goodboy-runtime.mjs install --user-approved\n");
  process.stdout.write("  goodboy-runtime.mjs run -- <goodboy arguments>\n\n");
  process.stdout.write("check and run never install software. install requires explicit user approval.\n");
}

function main(argv) {
  const [command = "check", ...args] = argv;
  if (command === "check") {
    if (args.length > 0 && !(args.length === 1 && args[0] === "--json")) {
      process.stderr.write(`Unknown check option: ${args.join(" ")}\n`);
      return EXIT.usage;
    }
    const status = inspectRuntime();
    printStatus(status);
    return exitForStatus(status);
  }
  if (command === "install") {
    return installRuntime(args);
  }
  if (command === "run") {
    return runRuntime(args);
  }
  if (command === "help" || command === "--help" || command === "-h") {
    printUsage();
    return EXIT.ready;
  }
  process.stderr.write(`Unknown command: ${command}\n`);
  printUsage();
  return EXIT.usage;
}

process.exitCode = main(process.argv.slice(2));
