import pytest
from pathlib import Path

from textab.router import (
    note_title_to_path,
    relative_path,
    check_routing_conflicts,
    _slugify,
    _looks_like_filename,
)
from textab.errors import RoutingConflict


# ── _slugify ──────────────────────────────────────────────────────────────────

def test_slugify_basic():
    assert _slugify("Hello World") == "hello-world"

def test_slugify_special_chars():
    assert _slugify("My Note! (2024)") == "my-note-2024"

def test_slugify_empty():
    assert _slugify("") == "untitled"

def test_slugify_only_special():
    assert _slugify("!!!") == "untitled"

def test_slugify_numbers():
    assert _slugify("Chapter 1") == "chapter-1"


# ── _looks_like_filename ──────────────────────────────────────────────────────

def test_looks_like_filename_dotfile():
    assert _looks_like_filename(".cursorrules") is True
    assert _looks_like_filename(".gitignore") is True
    assert _looks_like_filename(".env") is True

def test_looks_like_filename_with_known_ext():
    assert _looks_like_filename("README.md") is True
    assert _looks_like_filename("config.yaml") is True
    assert _looks_like_filename("data.json") is True

def test_looks_like_filename_unknown_ext():
    assert _looks_like_filename("script.py") is True

def test_looks_like_filename_no_ext():
    assert _looks_like_filename("My Notes") is False
    assert _looks_like_filename("Project Alpha") is False

def test_looks_like_filename_dot_only():
    assert _looks_like_filename(".") is False


# ── note_title_to_path ────────────────────────────────────────────────────────

def test_rule1_slash_title(tmp_path):
    path = note_title_to_path("docs/architecture.md", tmp_path)
    assert path == (tmp_path / "docs" / "architecture.md").resolve()

def test_rule1_nested_path(tmp_path):
    path = note_title_to_path("src/components/Button.tsx", tmp_path)
    assert path == (tmp_path / "src" / "components" / "Button.tsx").resolve()

def test_rule2_known_extension(tmp_path):
    path = note_title_to_path("CLAUDE.md", tmp_path)
    assert path == (tmp_path / "CLAUDE.md").resolve()

def test_rule2_dotfile(tmp_path):
    path = note_title_to_path(".cursorrules", tmp_path)
    assert path == (tmp_path / ".cursorrules").resolve()

def test_rule3_freeform_title(tmp_path):
    path = note_title_to_path("My Meeting Notes", tmp_path)
    assert path == (tmp_path / "my-meeting-notes.md").resolve()

def test_rule3_strip_whitespace(tmp_path):
    path = note_title_to_path("  Hello World  ", tmp_path)
    assert path == (tmp_path / "hello-world.md").resolve()

def test_path_traversal_rejected(tmp_path):
    with pytest.raises(ValueError, match="outside the project root"):
        note_title_to_path("../secret.txt", tmp_path)

def test_path_traversal_absolute_rejected(tmp_path):
    with pytest.raises(ValueError, match="outside the project root"):
        note_title_to_path("../../etc/passwd", tmp_path)


# ── relative_path ─────────────────────────────────────────────────────────────

def test_relative_path_slash():
    assert relative_path("docs/README.md") == "docs/README.md"

def test_relative_path_filename():
    assert relative_path("CLAUDE.md") == "CLAUDE.md"

def test_relative_path_freeform():
    assert relative_path("Meeting Notes") == "meeting-notes.md"


# ── check_routing_conflicts ───────────────────────────────────────────────────

def test_no_conflict(tmp_path):
    notes = [
        {"id": 1, "title": "CLAUDE.md"},
        {"id": 2, "title": "README.md"},
        {"id": 3, "title": "Meeting Notes"},
    ]
    check_routing_conflicts(notes, tmp_path)  # should not raise

def test_conflict_same_title_different_id(tmp_path):
    notes = [
        {"id": 1, "title": "My Note"},
        {"id": 2, "title": "My Note"},
    ]
    with pytest.raises(RoutingConflict):
        check_routing_conflicts(notes, tmp_path)

def test_conflict_titles_routing_to_same_path(tmp_path):
    # Both "My Note" and "My-Note" slugify differently but let's test explicit collision
    notes = [
        {"id": 1, "title": "CLAUDE.md"},
        {"id": 2, "title": "CLAUDE.md"},
    ]
    with pytest.raises(RoutingConflict):
        check_routing_conflicts(notes, tmp_path)

def test_empty_notes_no_conflict(tmp_path):
    check_routing_conflicts([], tmp_path)  # should not raise
