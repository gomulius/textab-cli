import json
from pathlib import Path

import pytest


@pytest.fixture
def tmp_project(tmp_path):
    """Return a temporary directory usable as a project root."""
    return tmp_path


@pytest.fixture
def sample_dotfile(tmp_project):
    """Write a minimal .textab file and return its Path."""
    data = {
        "sync_tag": "test-tag",
        "tag_id": 7,
        "last_synced": "2026-01-01T00:00:00+00:00",
        "base_url": None,
        "notes": [
            {
                "id": 42,
                "title": "CLAUDE.md",
                "local_path": "CLAUDE.md",
                "server_updated_at": "2026-01-01T00:00:00+00:00",
            }
        ],
    }
    p = tmp_project / ".textab"
    p.write_text(json.dumps(data))
    return p
