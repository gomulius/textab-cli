"""
Maps a TexTab note title to a local filesystem path.

Rules applied in order:
  1. Title contains '/'  → treat as relative path from project root
  2. Title looks like a filename (has extension or starts with '.') → place in root
  3. Freeform title → slugify + .md → place in root
"""

from __future__ import annotations

import re
from pathlib import Path

from textab.errors import RoutingConflict

_KNOWN_EXTENSIONS = {
    ".md", ".txt", ".yaml", ".yml", ".json", ".toml",
    ".cursorrules", ".windsurfrules", ".clinerules", ".gitignore",
    ".env",
}

_SLUG_RE = re.compile(r"[^a-z0-9]+")


def note_title_to_path(title: str, project_root: Path) -> Path:
    """
    Resolve a note title to an absolute local path under project_root.
    Raises ValueError if the resolved path escapes the project root.
    """
    title = title.strip()

    if "/" in title:
        # Rule 1: treat as relative path
        relative = Path(title)
    elif _looks_like_filename(title):
        # Rule 2: place in project root as-is
        relative = Path(title)
    else:
        # Rule 3: slugify
        slug = _slugify(title)
        relative = Path(f"{slug}.md")

    resolved = (project_root / relative).resolve()
    _assert_under_root(resolved, project_root.resolve())
    return resolved


def relative_path(title: str) -> str:
    """Return the relative path string (without project root prefix)."""
    title = title.strip()
    if "/" in title:
        return title
    if _looks_like_filename(title):
        return title
    return f"{_slugify(title)}.md"


def check_routing_conflicts(notes: list[dict], project_root: Path) -> None:
    """
    Raise RoutingConflict if two notes in the list route to the same local path.
    notes is a list of dicts with at least 'id' and 'title' keys.
    """
    seen: dict[Path, list[int]] = {}
    for note in notes:
        path = note_title_to_path(note["title"], project_root)
        seen.setdefault(path, []).append(note["id"])

    for path, ids in seen.items():
        if len(ids) > 1:
            raise RoutingConflict(path, ids)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _looks_like_filename(title: str) -> bool:
    """Return True if the title looks like a bare filename."""
    # Leading dot file: .cursorrules, .gitignore, etc.
    if title.startswith(".") and len(title) > 1 and "/" not in title:
        return True
    # Has an extension that appears in our known set OR any extension at all
    suffix = Path(title).suffix.lower()
    if suffix and suffix in _KNOWN_EXTENSIONS:
        return True
    # Generic: has any extension (e.g. "something.py")
    if "." in title and not title.startswith("."):
        return True
    return False


def _slugify(title: str) -> str:
    slug = title.lower()
    slug = _SLUG_RE.sub("-", slug)
    slug = slug.strip("-")
    return slug or "untitled"


def _assert_under_root(resolved: Path, root: Path) -> None:
    try:
        resolved.relative_to(root)
    except ValueError:
        raise ValueError(
            f"Note title resolves to a path outside the project root: {resolved}"
        )
