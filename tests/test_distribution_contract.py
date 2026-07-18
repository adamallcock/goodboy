from __future__ import annotations

import json
import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def json_file(relative_path: str) -> dict[str, object]:
    return json.loads((ROOT / relative_path).read_text(encoding="utf-8"))


class DistributionContractTests(unittest.TestCase):
    def test_public_versions_and_runtime_contract_stay_in_lockstep(self) -> None:
        pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
        project_match = re.search(r'^version = "([^"]+)"$', pyproject, re.MULTILINE)
        self.assertIsNotNone(project_match)
        version = project_match.group(1)

        init_source = (ROOT / "src/goodboy/__init__.py").read_text(encoding="utf-8")
        init_match = re.search(r'^__version__ = "([^"]+)"$', init_source, re.MULTILINE)
        self.assertIsNotNone(init_match)

        plugin = json_file("plugins/goodboy/.codex-plugin/plugin.json")
        runtime = json_file("plugins/goodboy/runtime.json")
        npm = json_file("packages/npm-goodboy/package.json")
        npm_launcher = (ROOT / "packages/npm-goodboy/bin/goodboy.js").read_text(encoding="utf-8")
        npm_launcher_match = re.search(r'^const VERSION = "([^"]+)";$', npm_launcher, re.MULTILINE)
        self.assertIsNotNone(npm_launcher_match)

        self.assertEqual(init_match.group(1), version)
        self.assertEqual(plugin["version"], version)
        self.assertEqual(runtime["version"], version)
        self.assertEqual(npm["version"], version)
        self.assertEqual(npm_launcher_match.group(1), version)
        self.assertEqual(runtime["distribution"], "goodboy-codex")
        self.assertEqual(runtime["command"], "goodboy")
        self.assertEqual(runtime["installer"], "uv")

    def test_plugin_runtime_and_skill_ship_together(self) -> None:
        runner = ROOT / "plugins/goodboy/scripts/goodboy-runtime.mjs"
        self.assertTrue(runner.is_file())
        runner_text = runner.read_text(encoding="utf-8")
        self.assertIn('join(PLUGIN_ROOT, "runtime.json")', runner_text)
        self.assertIn('"--user-approved"', runner_text)
        self.assertNotIn("curl ", runner_text)
        manifest = (ROOT / "MANIFEST.in").read_text(encoding="utf-8")
        self.assertIn("recursive-include plugins/goodboy *.json *.md *.mjs", manifest)

        standalone = (ROOT / "codex-skill/goodboy/SKILL.md").read_bytes()
        plugin_skill = (ROOT / "plugins/goodboy/skills/goodboy/SKILL.md").read_bytes()
        self.assertEqual(standalone, plugin_skill)
        self.assertIn(b"goodboy-codex[ui]==0.2.0", standalone)

    def test_marketplace_is_publicly_named_and_points_at_the_plugin(self) -> None:
        marketplace = json_file(".agents/plugins/marketplace.json")
        self.assertEqual(marketplace["name"], "goodboy")
        self.assertEqual(marketplace["interface"]["displayName"], "Goodboy")
        entry = marketplace["plugins"][0]
        self.assertEqual(entry["name"], "goodboy")
        self.assertEqual(entry["source"]["path"], "./plugins/goodboy")

    def test_npm_trusted_publish_workflow_is_narrow_and_tokenless(self) -> None:
        workflow = (ROOT / ".github/workflows/publish-npm.yml").read_text(encoding="utf-8")

        self.assertIn('      - "v*"', workflow)
        self.assertIn("  workflow_dispatch:", workflow)
        self.assertIn("    environment: npm", workflow)
        self.assertIn("      id-token: write", workflow)
        self.assertIn("git merge-base --is-ancestor", workflow)
        self.assertIn("https://pypi.org/pypi/goodboy-codex/", workflow)
        self.assertIn("node --test tests/launcher.test.mjs", workflow)
        self.assertIn("npm pack --dry-run --json", workflow)
        self.assertIn("npm publish --access public", workflow)
        self.assertNotIn("NPM_TOKEN", workflow)
        self.assertNotIn("NODE_AUTH_TOKEN", workflow)


if __name__ == "__main__":
    unittest.main()
