import assert from "node:assert/strict";
import { chmodSync, mkdtempSync, readFileSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { dirname, join, resolve } from "node:path";
import { spawnSync } from "node:child_process";
import { fileURLToPath } from "node:url";
import test from "node:test";

const HERE = dirname(fileURLToPath(import.meta.url));
const LAUNCHER = resolve(HERE, "..", "bin", "goodboy.js");
const SKIP_ON_WINDOWS = process.platform === "win32";

function writeExecutable(path, body) {
  writeFileSync(path, `#!/bin/sh\nset -eu\n${body}\n`, "utf8");
  chmodSync(path, 0o755);
}

function fixture(version) {
  const root = mkdtempSync(join(tmpdir(), "goodboy-npm-"));
  const log = join(root, "runtime.log");
  const runtime = join(root, "goodboy");
  const uv = join(root, "uv");
  writeExecutable(
    runtime,
    `printf '%s\\n' "$*" >> "${log}"\nif [ "$1" = "--version" ]; then printf 'goodboy ${version}\\n'; else printf 'ran:%s\\n' "$*"; fi`
  );
  writeExecutable(
    uv,
    `if [ "$1" = "tool" ] && [ "$2" = "dir" ]; then printf '%s\\n' "${root}"; else exit 2; fi`
  );
  return { root, log, uv };
}

function invoke(args, env = {}) {
  return spawnSync(process.execPath, [LAUNCHER, ...args], {
    encoding: "utf8",
    env: { ...process.env, ...env }
  });
}

test("help recommends the plugin-first path and pinned standalone runtime", () => {
  const result = invoke(["--help"]);
  assert.equal(result.status, 0);
  assert.match(result.stdout, /install the Goodboy plugin/u);
  assert.match(result.stdout, /goodboy-codex\[ui\]==0\.2\.0/u);
});

test("launcher discovers and executes the exact uv-managed runtime", { skip: SKIP_ON_WINDOWS }, () => {
  const { root, log, uv } = fixture("0.2.0");
  try {
    const result = invoke(["doctor", "/tmp/pet"], {
      GOODBOY_UV_COMMAND: uv,
      GOODBOY_COMMAND: "",
      GOODBOY_PYTHON: ""
    });
    assert.equal(result.status, 0, result.stderr);
    assert.match(result.stdout, /ran:doctor \/tmp\/pet/u);
    assert.deepEqual(readFileSync(log, "utf8").trim().split("\n"), ["--version", "doctor /tmp/pet"]);
  } finally {
    rmSync(root, { recursive: true, force: true });
  }
});

test("launcher refuses a runtime version mismatch", { skip: SKIP_ON_WINDOWS }, () => {
  const { root, log, uv } = fixture("0.1.2");
  try {
    const result = invoke(["doctor", "/tmp/pet"], {
      PATH: root,
      GOODBOY_UV_COMMAND: uv,
      GOODBOY_COMMAND: "",
      GOODBOY_PYTHON: join(root, "missing-python")
    });
    assert.equal(result.status, 1);
    assert.match(result.stderr, /found Goodboy 0\.1\.2; launcher requires 0\.2\.0/u);
    assert.equal(readFileSync(log, "utf8").trim(), "--version");
  } finally {
    rmSync(root, { recursive: true, force: true });
  }
});
