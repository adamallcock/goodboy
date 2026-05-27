"""Safety checks that keep generated pet projects agent-proof."""

from __future__ import annotations

from pathlib import Path


SUSPICIOUS_RENDERER_NAMES = ("render", "renderer", "draw", "sprite", "row_strip")
SUSPICIOUS_RENDERER_TOKENS = ("ImageDraw", "Image.new", "PIL import", "<svg", "canvas")


def find_suspicious_renderer_scripts(project_dir: Path) -> list[str]:
    """Return project-local scripts that look like ad hoc sprite renderers."""
    matches: list[str] = []
    for path in sorted(project_dir.rglob("*.py")):
        if should_ignore_path(project_dir, path):
            continue
        rel = path.relative_to(project_dir)
        name = path.name.lower()
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            text = ""
        name_suspicious = any(token in name for token in SUSPICIOUS_RENDERER_NAMES)
        content_suspicious = any(token in text for token in SUSPICIOUS_RENDERER_TOKENS)
        under_tools = rel.parts and rel.parts[0] in {"tools", "scripts"}
        if (under_tools and name_suspicious) or (name_suspicious and content_suspicious):
            matches.append(str(rel))
    return matches


def should_ignore_path(project_dir: Path, path: Path) -> bool:
    rel_parts = path.relative_to(project_dir).parts
    return any(part in {".venv", "__pycache__", "site-packages"} for part in rel_parts)
