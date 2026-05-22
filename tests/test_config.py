import json
import pytest
from pathlib import Path
from unittest.mock import patch

from textab.config import (
    ProjectConfig,
    NoteRef,
    load_project_config,
    save_project_config,
    find_dotfile,
    DOTFILE_NAME,
)
from textab.errors import ProjectConfigNotFound


# ── ProjectConfig dataclass ───────────────────────────────────────────────────

def test_get_note_by_id_found():
    cfg = ProjectConfig(sync_tag="t", tag_id=1)
    cfg.notes = [{"id": 42, "title": "A", "local_path": "a.md", "server_updated_at": ""}]
    assert cfg.get_note_by_id(42)["title"] == "A"

def test_get_note_by_id_missing():
    cfg = ProjectConfig(sync_tag="t", tag_id=1)
    assert cfg.get_note_by_id(99) is None

def test_get_note_by_path():
    cfg = ProjectConfig(sync_tag="t", tag_id=1)
    cfg.notes = [{"id": 1, "title": "X", "local_path": "x.md", "server_updated_at": ""}]
    assert cfg.get_note_by_path("x.md") is not None
    assert cfg.get_note_by_path("y.md") is None

def test_upsert_note_adds_new():
    cfg = ProjectConfig(sync_tag="t", tag_id=1)
    ref = NoteRef(id=5, title="New", local_path="new.md", server_updated_at="2026-01-01T00:00:00+00:00")
    cfg.upsert_note(ref)
    assert len(cfg.notes) == 1
    assert cfg.notes[0]["id"] == 5

def test_upsert_note_updates_existing():
    cfg = ProjectConfig(sync_tag="t", tag_id=1)
    cfg.notes = [{"id": 5, "title": "Old", "local_path": "old.md", "server_updated_at": ""}]
    ref = NoteRef(id=5, title="Updated", local_path="new.md", server_updated_at="2026-06-01T00:00:00+00:00")
    cfg.upsert_note(ref)
    assert len(cfg.notes) == 1
    assert cfg.notes[0]["title"] == "Updated"

def test_remove_note():
    cfg = ProjectConfig(sync_tag="t", tag_id=1)
    cfg.notes = [
        {"id": 1, "title": "A", "local_path": "a.md", "server_updated_at": ""},
        {"id": 2, "title": "B", "local_path": "b.md", "server_updated_at": ""},
    ]
    cfg.remove_note(1)
    assert len(cfg.notes) == 1
    assert cfg.notes[0]["id"] == 2

def test_remove_note_nonexistent():
    cfg = ProjectConfig(sync_tag="t", tag_id=1)
    cfg.notes = [{"id": 1, "title": "A", "local_path": "a.md", "server_updated_at": ""}]
    cfg.remove_note(99)  # should not raise
    assert len(cfg.notes) == 1


# ── load / save project config ────────────────────────────────────────────────

def test_save_and_load_roundtrip(tmp_path):
    cfg = ProjectConfig(
        sync_tag="alpha",
        tag_id=7,
        last_synced="2026-01-01T00:00:00+00:00",
        base_url="https://textab.app/pro",
        notes=[{"id": 42, "title": "CLAUDE.md", "local_path": "CLAUDE.md", "server_updated_at": "2026-01-01T00:00:00+00:00"}],
    )
    dotfile = tmp_path / DOTFILE_NAME
    save_project_config(cfg, dotfile)
    loaded = load_project_config(dotfile)
    assert loaded.sync_tag == "alpha"
    assert loaded.tag_id == 7
    assert loaded.last_synced == "2026-01-01T00:00:00+00:00"
    assert loaded.base_url == "https://textab.app/pro"
    assert len(loaded.notes) == 1
    assert loaded.notes[0]["id"] == 42

def test_load_missing_file_raises(tmp_path):
    dotfile = tmp_path / DOTFILE_NAME
    with pytest.raises(ProjectConfigNotFound):
        load_project_config(dotfile)

def test_load_minimal_config(tmp_path):
    data = {"sync_tag": "beta", "tag_id": 3}
    dotfile = tmp_path / DOTFILE_NAME
    dotfile.write_text(json.dumps(data))
    cfg = load_project_config(dotfile)
    assert cfg.sync_tag == "beta"
    assert cfg.tag_id == 3
    assert cfg.last_synced is None
    assert cfg.base_url is None
    assert cfg.notes == []

def test_save_writes_valid_json(tmp_path):
    cfg = ProjectConfig(sync_tag="t", tag_id=1)
    dotfile = tmp_path / DOTFILE_NAME
    save_project_config(cfg, dotfile)
    raw = json.loads(dotfile.read_text())
    assert raw["sync_tag"] == "t"
    assert raw["tag_id"] == 1
    assert raw["notes"] == []


# ── find_dotfile ──────────────────────────────────────────────────────────────

def test_find_dotfile_in_current_dir(tmp_path):
    dotfile = tmp_path / DOTFILE_NAME
    dotfile.write_text("{}")
    found = find_dotfile(tmp_path)
    assert found == dotfile

def test_find_dotfile_in_parent(tmp_path):
    # Place .textab in tmp_path, search from a subdir
    dotfile = tmp_path / DOTFILE_NAME
    dotfile.write_text("{}")
    subdir = tmp_path / "subdir"
    subdir.mkdir()
    found = find_dotfile(subdir)
    assert found == dotfile

def test_find_dotfile_not_found(tmp_path):
    with pytest.raises(ProjectConfigNotFound):
        find_dotfile(tmp_path)


# ── sample_dotfile fixture ────────────────────────────────────────────────────

def test_sample_dotfile_is_readable(sample_dotfile):
    cfg = load_project_config(sample_dotfile)
    assert cfg.sync_tag == "test-tag"
    assert cfg.tag_id == 7
    assert len(cfg.notes) == 1
    assert cfg.notes[0]["id"] == 42
