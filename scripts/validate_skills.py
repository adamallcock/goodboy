#!/usr/bin/env python3
"""Small public CI validator for Codex skill folders."""

from __future__ import annotations

import re
import sys
from pathlib import Path


FRONTMATTER_PATTERN = re.compile(r"^---\n(?P<body>.*?)\n---\n", re.DOTALL)
REQUIRED_KEYS = {"name", "description"}
ALLOWED_KEYS = {"name", "description"}


def parse_frontmatter(text: str) -> dict[str, str]:
    match = FRONTMATTER_PATTERN.match(text)
    if not match:
        raise ValueError("missing YAML frontmatter delimited by ---")
    data: dict[str, str] = {}
    for line in match.group("body").splitlines():
        if not line.strip():
            continue
        if ":" not in line:
            raise ValueError(f"invalid frontmatter line: {line}")
        key, value = line.split(":", 1)
        data[key.strip()] = value.strip()
    return data


def validate_skill(path: Path) -> list[str]:
    errors: list[str] = []
    skill_md = path / "SKILL.md"
    if not skill_md.is_file():
        return [f"{path}: missing SKILL.md"]
    text = skill_md.read_text(encoding="utf-8")
    try:
        frontmatter = parse_frontmatter(text)
    except ValueError as exc:
        return [f"{skill_md}: {exc}"]
    missing = sorted(REQUIRED_KEYS - set(frontmatter))
    unexpected = sorted(set(frontmatter) - ALLOWED_KEYS)
    for key in missing:
        errors.append(f"{skill_md}: missing frontmatter key `{key}`")
    for key in unexpected:
        errors.append(f"{skill_md}: unexpected frontmatter key `{key}`")
    if not frontmatter.get("name", "").strip():
        errors.append(f"{skill_md}: empty skill name")
    if len(frontmatter.get("description", "")) < 40:
        errors.append(f"{skill_md}: description should be specific enough for routing")
    if len(text.splitlines()) > 500:
        errors.append(f"{skill_md}: keep skill file under 500 lines")
    return errors


def main(argv: list[str]) -> int:
    if not argv:
        print("usage: validate_skills.py <skill-dir> [<skill-dir> ...]", file=sys.stderr)
        return 2
    errors: list[str] = []
    for raw in argv:
        errors.extend(validate_skill(Path(raw)))
    if errors:
        for error in errors:
            print(error, file=sys.stderr)
        return 1
    print("Skills are valid.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
