"""
TexTab API client built on httpx.

All methods raise APIError on non-2xx responses.
The server always responds with:
  Success: {"success": true, "data": {...}, "message": "..."}
  Error:   {"success": false, "error": {"message": "...", "code": "...", "http_status": N}}
"""

from __future__ import annotations

from typing import Any, Optional

import httpx

from textab.errors import APIError

DEFAULT_BASE_URL = "https://textab.app/pro"


class TexTabClient:
    def __init__(self, token: str, base_url: str = DEFAULT_BASE_URL) -> None:
        self._base_url = base_url.rstrip("/")
        self._http = httpx.Client(
            base_url=self._base_url,
            headers={
                "X-API-Key": token,
                "Content-Type": "application/json",
                "Accept": "application/json",
            },
            timeout=30.0,
            follow_redirects=True,
        )

    # ── Tags ─────────────────────────────────────────────────────────────────

    def list_tags(self) -> list[dict]:
        return self._get("/api/v1/tags").get("tags", [])

    def get_tag_by_name(self, name: str) -> Optional[dict]:
        tags = self.list_tags()
        for tag in tags:
            if tag.get("name", "").lower() == name.lower():
                return tag
        return None

    # ── Notes ─────────────────────────────────────────────────────────────────

    def list_notes_by_tag(self, tag_id: int) -> list[dict]:
        """Return all note summaries for a tag, handling pagination automatically."""
        notes: list[dict] = []
        page = 1
        while True:
            data = self._get("/api/v1/notes", params={
                "tags": str(tag_id),
                "per_page": 100,
                "page": page,
            })
            batch = data.get("notes", [])
            notes.extend(batch)
            pagination = data.get("pagination", {})
            if page >= pagination.get("pages", 1):
                break
            page += 1
        return notes

    def get_note(self, note_id: int, compile_vars: bool = False) -> dict:
        """
        Fetch a single note.

        compile_vars=True calls the AI Variables compile endpoint first.
        On NO_VARIABLES_BLOCK (422) it falls back transparently to the raw note.
        Returns a dict with at least: id, title, content, updated_at.
        """
        if compile_vars:
            try:
                data = self._get(f"/api/plugins/ai_variables/compile/{note_id}")
                return {
                    "id": note_id,
                    "title": data.get("title", ""),
                    "content": data.get("compiled_content", ""),
                    "updated_at": None,   # compile endpoint doesn't return updated_at
                    "unresolved": data.get("unresolved", []),
                }
            except APIError as e:
                if e.code != "NO_VARIABLES_BLOCK":
                    raise

        data = self._get(f"/api/v1/notes/{note_id}")
        note = data if "id" in data else data.get("note", data)
        return note

    def get_note_meta(self, note_id: int) -> dict:
        """Fetch note without content — just for updated_at conflict checking."""
        data = self._get(f"/api/v1/notes/{note_id}")
        return data if "id" in data else data.get("note", data)

    def create_note(self, title: str, content: str) -> dict:
        data = self._post("/api/v1/notes", {"title": title, "content": content})
        return data

    def update_note(self, note_id: int, content: str, title: Optional[str] = None) -> dict:
        """Update note content (and optionally title). Server auto-versions."""
        body: dict[str, Any] = {"content": content}
        if title is not None:
            body["title"] = title
        return self._put(f"/api/v1/notes/{note_id}", body)

    def add_note_tag(self, note_id: int, tag_id: int) -> None:
        """Tag a note. Silently ignores DUPLICATE_RELATIONSHIP errors."""
        try:
            self._post(f"/api/v1/notes/{note_id}/tags", {"tag_id": tag_id})
        except APIError as e:
            if e.code != "DUPLICATE_RELATIONSHIP":
                raise

    def get_current_user(self) -> dict:
        return self._get("/api/v1/user/profile")

    # ── HTTP helpers ──────────────────────────────────────────────────────────

    def _get(self, path: str, params: Optional[dict] = None) -> dict:
        r = self._http.get(path, params=params)
        return self._unwrap(r)

    def _post(self, path: str, body: dict) -> dict:
        r = self._http.post(path, json=body)
        return self._unwrap(r)

    def _put(self, path: str, body: dict) -> dict:
        r = self._http.put(path, json=body)
        return self._unwrap(r)

    def _unwrap(self, response: httpx.Response) -> dict:
        try:
            payload = response.json()
        except Exception:
            raise APIError(
                f"Non-JSON response ({response.status_code})", "PARSE_ERROR", response.status_code
            )
        if not payload.get("success", False):
            err = payload.get("error", {})
            raise APIError(
                err.get("message", "Unknown error"),
                err.get("code", ""),
                response.status_code,
            )
        return payload.get("data", payload)

    def close(self) -> None:
        self._http.close()

    def __enter__(self) -> "TexTabClient":
        return self

    def __exit__(self, *_: Any) -> None:
        self.close()
