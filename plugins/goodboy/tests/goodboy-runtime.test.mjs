import assert from "node:assert/strict";
import { chmodSync, existsSync, mkdtempSync, readFileSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { dirname, join, resolve } from "node:path";
import { spawnSync } from "node:child_process";
import { fileURLToPath } from "node:url";
import test from "node:test";

const HERE = dirname(fileURLToPath(import.meta.url));
const RUNNER = resolve(HERE, "..", "scripts", "goodboy-runtime.mjs");
const SKIP_ON_WINDOWS = process.platform === "win32";

function tempRoot() {
  return mkdtempSync(join(tmpdir(), "goodboy-runtime-"));
}

function writeExecutable(path, body) {
  writeFileSync(path, `#!/bin/sh\nset -eu\n${body}\n`, "utf8");
  chmodSync(path, 0o755);
}

function goodboyScript(version, runLog = null) {
  const logLine = runLog ? `printf '%s\\n' "$*" >> "${runLog}"` : ":";
  return `${logLine}\nif [ "$1" = "--version" ]; then\n  printf 'goodboy ${version}\\n'\nelse\n  printf 'ran:%s\\n' "$*"\nfi`;
}

function invoke(args, env) {
  return spawnSync(process.execPath, [RUNNER, ...args], {
    encoding: "utf8",
    env: { ...process.env, ...env }
  });
}

function parseStatus(output) {
  const line = String(output)
    .split(/\r?\n/u)
    .filter(Boolean)
    .findLast((candidate) => candidate.startsWith("{"));
  assert.ok(line, `missing JSON status in: ${output}`);
  return JSON.parse(line);
}

function baseEnv(root) {
  return {
    PATH: root,
    GOODBOY_RUNTIME_COMMAND: "",
    GOODBOY_UV_COMMAND: "uv"
  };
}

test("check accepts an exact installed runtime", { skip: SKIP_ON_WINDOWS }, () => {
  const root = tempRoot();
  try {
    writeExecutable(join(root, "goodboy"), goodboyScript("0.2.1"));
    const result = invoke(["check", "--json"], baseEnv(root));
    assert.equal(result.status, 0, result.stderr);
    const status = parseStatus(result.stdout);
    assert.equal(status.status, "ready");
    assert.equal(status.found_version, "0.2.1");
    assert.equal(status.package_spec, "goodboy-codex[ui]==0.2.1");
  } finally {
    rmSync(root, { recursive: true, force: true });
  }
});

test("check reports a missing runtime without installing", { skip: SKIP_ON_WINDOWS }, () => {
  const root = tempRoot();
  try {
    const result = invoke(["check"], baseEnv(root));
    assert.equal(result.status, 10);
    assert.equal(parseStatus(result.stdout).status, "missing");
  } finally {
    rmSync(root, { recursive: true, force: true });
  }
});

test("check rejects a mismatched runtime", { skip: SKIP_ON_WINDOWS }, () => {
  const root = tempRoot();
  try {
    writeExecutable(join(root, "goodboy"), goodboyScript("0.1.2"));
    const result = invoke(["check"], baseEnv(root));
    assert.equal(result.status, 11);
    const status = parseStatus(result.stdout);
    assert.equal(status.status, "mismatch");
    assert.equal(status.found_version, "0.1.2");
    assert.equal(status.expected_version, "0.2.1");
  } finally {
    rmSync(root, { recursive: true, force: true });
  }
});

test("check rejects an executable with unreadable version output", { skip: SKIP_ON_WINDOWS }, () => {
  const root = tempRoot();
  try {
    writeExecutable(join(root, "goodboy"), "printf 'unknown build\\n'");
    const result = invoke(["check"], baseEnv(root));
    assert.equal(result.status, 12);
    assert.equal(parseStatus(result.stdout).status, "invalid");
  } finally {
    rmSync(root, { recursive: true, force: true });
  }
});

test("install refuses to run without the explicit approval flag", { skip: SKIP_ON_WINDOWS }, () => {
  const root = tempRoot();
  const uvLog = join(root, "uv.log");
  try {
    writeExecutable(join(root, "uv"), `printf '%s\\n' "$*" >> "${uvLog}"`);
    const result = invoke(["install"], baseEnv(root));
    assert.equal(result.status, 20);
    assert.equal(parseStatus(result.stderr).status, "approval_required");
    assert.equal(existsSync(uvLog), false, "uv must not run before approval");
  } finally {
    rmSync(root, { recursive: true, force: true });
  }
});

test("approved install stops separately when uv is unavailable", { skip: SKIP_ON_WINDOWS }, () => {
  const root = tempRoot();
  try {
    const result = invoke(["install", "--user-approved"], baseEnv(root));
    assert.equal(result.status, 21);
    assert.equal(parseStatus(result.stderr).status, "uv_missing");
  } finally {
    rmSync(root, { recursive: true, force: true });
  }
});

test("approved install uses the exact pinned spec and verifies the result", { skip: SKIP_ON_WINDOWS }, () => {
  const root = tempRoot();
  const uvLog = join(root, "uv.log");
  const ready = join(root, "goodboy-ready");
  try {
    writeExecutable(ready, goodboyScript("0.2.1"));
    writeExecutable(
      join(root, "uv"),
      `if [ "$1" = "--version" ]; then\n  printf 'uv 1.0.0\\n'\nelif [ "$1" = "tool" ] && [ "$2" = "dir" ]; then\n  printf '%s\\n' "${root}"\nelif [ "$1" = "tool" ] && [ "$2" = "install" ]; then\n  printf '%s\\n' "$*" > "${uvLog}"\n  /bin/cp "${ready}" "${join(root, "goodboy")}"\n  /bin/chmod 755 "${join(root, "goodboy")}"\nelse\n  exit 2\nfi`
    );
    const result = invoke(["install", "--user-approved"], baseEnv(root));
    assert.equal(result.status, 0, result.stderr);
    assert.equal(parseStatus(result.stdout).status, "ready");
    assert.equal(readFileSync(uvLog, "utf8").trim(), "tool install goodboy-codex[ui]==0.2.1");

    const run = invoke(["run", "--", "--version"], baseEnv(root));
    assert.equal(run.status, 0, run.stderr);
    assert.match(run.stdout, /goodboy 0\.2\.1/u);
  } finally {
    rmSync(root, { recursive: true, force: true });
  }
});

test("approved install replaces a mismatched uv-managed runtime", { skip: SKIP_ON_WINDOWS }, () => {
  const root = tempRoot();
  const ready = join(root, "goodboy-ready");
  try {
    writeExecutable(join(root, "goodboy"), goodboyScript("0.1.2"));
    writeExecutable(ready, goodboyScript("0.2.1"));
    writeExecutable(
      join(root, "uv"),
      `if [ "$1" = "--version" ]; then\n  printf 'uv 1.0.0\\n'\nelif [ "$1" = "tool" ] && [ "$2" = "dir" ]; then\n  printf '%s\\n' "${root}"\nelif [ "$1" = "tool" ] && [ "$2" = "install" ]; then\n  /bin/cp "${ready}" "${join(root, "goodboy")}"\n  /bin/chmod 755 "${join(root, "goodboy")}"\nelse\n  exit 2\nfi`
    );
    const result = invoke(["install", "--user-approved"], baseEnv(root));
    assert.equal(result.status, 0, result.stderr);
    assert.equal(parseStatus(result.stdout).found_version, "0.2.1");
  } finally {
    rmSync(root, { recursive: true, force: true });
  }
});

test("failed uv installation is surfaced and never reported ready", { skip: SKIP_ON_WINDOWS }, () => {
  const root = tempRoot();
  try {
    writeExecutable(
      join(root, "uv"),
      "if [ \"$1\" = \"--version\" ]; then printf 'uv 1.0.0\\n'; elif [ \"$1\" = \"tool\" ] && [ \"$2\" = \"dir\" ]; then printf '%s\\n' \"$PATH\"; else printf 'network failed\\n' >&2; exit 7; fi"
    );
    const result = invoke(["install", "--user-approved"], baseEnv(root));
    assert.equal(result.status, 22);
    assert.equal(parseStatus(result.stderr).status, "install_failed");
    assert.match(result.stderr, /network failed/u);
  } finally {
    rmSync(root, { recursive: true, force: true });
  }
});

test("installer success without an exact executable fails post-install verification", { skip: SKIP_ON_WINDOWS }, () => {
  const root = tempRoot();
  try {
    writeExecutable(
      join(root, "uv"),
      `if [ "$1" = "--version" ]; then\n  printf 'uv 1.0.0\\n'\nelif [ "$1" = "tool" ] && [ "$2" = "dir" ]; then\n  printf '%s\\n' "${root}"\nelif [ "$1" = "tool" ] && [ "$2" = "install" ]; then\n  exit 0\nelse\n  exit 2\nfi`
    );
    const result = invoke(["install", "--user-approved"], baseEnv(root));
    assert.equal(result.status, 23);
    assert.equal(parseStatus(result.stderr).status, "post_install_failed");
  } finally {
    rmSync(root, { recursive: true, force: true });
  }
});

test("run refuses to execute a mismatched runtime", { skip: SKIP_ON_WINDOWS }, () => {
  const root = tempRoot();
  const runLog = join(root, "goodboy.log");
  try {
    writeExecutable(join(root, "goodboy"), goodboyScript("0.1.2", runLog));
    const result = invoke(["run", "--", "doctor", "/tmp/pet"], baseEnv(root));
    assert.equal(result.status, 11);
    assert.equal(parseStatus(result.stderr).status, "mismatch");
    assert.equal(readFileSync(runLog, "utf8").trim(), "--version");
  } finally {
    rmSync(root, { recursive: true, force: true });
  }
});
