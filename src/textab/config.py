"""
Credentials and project config management.

Credentials (~/.textab-credentials or OS keychain):
    {"token": "...", "base_url": "https://textab.app/pro"}

Project config (.textab in project root):
    {
      "sync_tag": "project-alpha",
      "tag_id": 7,
      "base_url": null,          # null = use credentials base_url
      "last_synced": "2026-...", # ISO-8601 UTC or null
      "notes": [
        {"id": 42, "title": "CLAUDE.md", "local_path": "CLAUDE.md",
         "server_updated_at": "2026-..."}
      ]
    }
"""

from __future__ import annotations

import json
import os
import stat
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Optional

from textab.errors import CredentialsNotFound, ProjectConfigNotFound

CREDENTIALS_PATH = Path.home() / ".textab-credentials"
DOTFILE_NAME = ".textab"
KEYRING_SERVICE = "textab-cli"
KEYRING_USERNAME = "api-token"
KEYRING_BASEURL = "base-url"


# ── Credentials ──────────────────────────────────────────────────────────────

def save_credentials(token: str, base_url: str) -> None:
    try:
        import keyring
        keyring.set_password(KEYRING_SERVICE, KEYRING_USERNAME, token)
        keyring.set_password(KEYRING_SERVICE, KEYRING_BASEURL, base_url)
        return
    except Exception:
        pass

    data = {"token": token, "base_url": base_url}
    CREDENTIALS_PATH.write_text(json.dumps(data, indent=2))
    CREDENTIALS_PATH.chmod(stat.S_IRUSR | stat.S_IWUSR)  # chmod 600


def load_credentials() -> tuple[str, str]:
    """Returns (token, base_url). Raises CredentialsNotFound if missing."""
    try:
        import keyring
        token = keyring.get_password(KEYRING_SERVICE, KEYRING_USERNAME)
        base_url = keyring.get_password(KEYRING_SERVICE, KEYRING_BASEURL)
        if token and base_url:
            return token, base_url
    except Exception:
        pass

    if CREDENTIALS_PATH.exists():
        data = json.loads(CREDENTIALS_PATH.read_text())
        token = data.get("token", "")
        base_url = data.get("base_url", "")
        if token and base_url:
            return token, base_url

    raise CredentialsNotFound()


def delete_credentials() -> bool:
    """Remove stored credentials. Returns True if anything was deleted."""
    deleted = False
    try:
        import keyring
        if keyring.get_password(KEYRING_SERVICE, KEYRING_USERNAME):
            keyring.delete_password(KEYRING_SERVICE, KEYRING_USERNAME)
            keyring.delete_password(KEYRING_SERVICE, KEYRING_BASEURL)
            deleted = True
    except Exception:
        pass

    if CREDENTIALS_PATH.exists():
        CREDENTIALS_PATH.unlink()
        deleted = True

    return deleted


# ── Project config ────────────────────────────────────────────────────────────

@dataclass
class NoteRef:
    id: int
    title: str
    local_path: str          # relative to project root
    server_updated_at: str   # ISO-8601 UTC


@dataclass
class ProjectConfig:
    sync_tag: str
    tag_id: int
    last_synced: Optional[str] = None
    base_url: Optional[str] = None   # None = use credentials base_url
    notes: list = field(default_factory=list)  # list of NoteRef dicts

    def get_note_by_id(self, note_id: int) -> Optional[dict]:
        return next((n for n in self.notes if n["id"] == note_id), None)

    def get_note_by_path(self, path: str) -> Optional[dict]:
        return next((n for n in self.notes if n["local_path"] == path), None)

    def upsert_note(self, ref: NoteRef) -> None:
        d = asdict(ref)
        for i, n in enumerate(self.notes):
            if n["id"] == ref.id:
                self.notes[i] = d
                return
        self.notes.append(d)

    def remove_note(self, note_id: int) -> None:
        self.notes = [n for n in self.notes if n["id"] != note_id]


def find_dotfile(start: Optional[Path] = None) -> Path:
    """Walk up from start (default CWD) to find .textab. Returns its Path."""
    current = (start or Path.cwd()).resolve()
    for parent in [current] + list(current.parents):
        candidate = parent / DOTFILE_NAME
        if candidate.exists():
            return candidate
    raise ProjectConfigNotFound()


def load_project_config(path: Optional[Path] = None) -> ProjectConfig:
    p = path or _default_dotfile_path()
    if not p.exists():
        raise ProjectConfigNotFound()
    data = json.loads(p.read_text())
    return ProjectConfig(
        sync_tag=data["sync_tag"],
        tag_id=data["tag_id"],
        last_synced=data.get("last_synced"),
        base_url=data.get("base_url"),
        notes=data.get("notes", []),
    )


def save_project_config(cfg: ProjectConfig, path: Optional[Path] = None) -> None:
    p = path or _default_dotfile_path()
    data = {
        "sync_tag": cfg.sync_tag,
        "tag_id": cfg.tag_id,
        "last_synced": cfg.last_synced,
        "base_url": cfg.base_url,
        "notes": cfg.notes,
    }
    p.write_text(json.dumps(data, indent=2))


def _default_dotfile_path() -> Path:
    return Path.cwd() / DOTFILE_NAME
