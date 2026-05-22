import json
import pytest
import httpx

from textab.client import TexTabClient
from textab.errors import APIError


BASE = "https://test.local"


def _ok(data: dict) -> dict:
    return {"success": True, "data": data}


def _err(message: str, code: str, status: int) -> tuple[int, dict]:
    return status, {"success": False, "error": {"message": message, "code": code, "http_status": status}}


def _make_client(routes: dict[tuple[str, str], tuple[int, dict]]) -> TexTabClient:
    """
    Build a TexTabClient backed by a MockTransport.
    routes maps (METHOD, path_suffix) → (status_code, json_body).
    """
    def handler(request: httpx.Request) -> httpx.Response:
        key = (request.method, request.url.path)
        if key not in routes:
            return httpx.Response(404, json={"success": False, "error": {"message": "not found", "code": "NOT_FOUND", "http_status": 404}})
        status, body = routes[key]
        return httpx.Response(status, json=body)

    transport = httpx.MockTransport(handler)
    client = TexTabClient.__new__(TexTabClient)
    client._base_url = BASE
    client._http = httpx.Client(
        base_url=BASE,
        transport=transport,
        headers={"X-API-Key": "test-token", "Content-Type": "application/json"},
    )
    return client


# ── _unwrap ───────────────────────────────────────────────────────────────────

def test_unwrap_success():
    routes = {("GET", "/api/v1/tags"): (200, _ok({"tags": []}))}
    with _make_client(routes) as client:
        data = client._get("/api/v1/tags")
    assert data == {"tags": []}

def test_unwrap_error_raises_api_error():
    status, body = _err("Unauthorized", "UNAUTHORIZED", 401)
    routes = {("GET", "/api/v1/tags"): (status, body)}
    with _make_client(routes) as client:
        with pytest.raises(APIError) as exc_info:
            client._get("/api/v1/tags")
    assert exc_info.value.code == "UNAUTHORIZED"
    assert exc_info.value.status_code == 401

def test_unwrap_non_json_raises():
    def handler(request):
        return httpx.Response(500, text="Internal Server Error")

    transport = httpx.MockTransport(handler)
    client = TexTabClient.__new__(TexTabClient)
    client._base_url = BASE
    client._http = httpx.Client(base_url=BASE, transport=transport, headers={})
    with client:
        with pytest.raises(APIError) as exc_info:
            client._get("/api/v1/tags")
    assert exc_info.value.code == "PARSE_ERROR"


# ── list_tags ─────────────────────────────────────────────────────────────────

def test_list_tags_returns_list():
    tags = [{"id": 1, "name": "alpha"}, {"id": 2, "name": "beta"}]
    routes = {("GET", "/api/v1/tags"): (200, _ok({"tags": tags}))}
    with _make_client(routes) as client:
        result = client.list_tags()
    assert result == tags

def test_get_tag_by_name_found():
    tags = [{"id": 5, "name": "MyTag"}]
    routes = {("GET", "/api/v1/tags"): (200, _ok({"tags": tags}))}
    with _make_client(routes) as client:
        tag = client.get_tag_by_name("mytag")
    assert tag["id"] == 5

def test_get_tag_by_name_not_found():
    routes = {("GET", "/api/v1/tags"): (200, _ok({"tags": []}))}
    with _make_client(routes) as client:
        tag = client.get_tag_by_name("nonexistent")
    assert tag is None


# ── list_notes_by_tag ─────────────────────────────────────────────────────────

def test_list_notes_by_tag_single_page():
    notes = [{"id": 1, "title": "Note A"}, {"id": 2, "title": "Note B"}]
    payload = _ok({"notes": notes, "pagination": {"page": 1, "pages": 1, "total": 2}})
    routes = {("GET", "/api/v1/notes"): (200, payload)}
    with _make_client(routes) as client:
        result = client.list_notes_by_tag(tag_id=7)
    assert len(result) == 2

def test_list_notes_by_tag_pagination():
    page1 = _ok({"notes": [{"id": 1, "title": "A"}], "pagination": {"page": 1, "pages": 2, "total": 2}})
    page2 = _ok({"notes": [{"id": 2, "title": "B"}], "pagination": {"page": 2, "pages": 2, "total": 2}})
    call_count = [0]

    def handler(request: httpx.Request) -> httpx.Response:
        call_count[0] += 1
        page = int(request.url.params.get("page", 1))
        if page == 1:
            return httpx.Response(200, json=page1)
        return httpx.Response(200, json=page2)

    transport = httpx.MockTransport(handler)
    client = TexTabClient.__new__(TexTabClient)
    client._base_url = BASE
    client._http = httpx.Client(base_url=BASE, transport=transport, headers={})
    with client:
        result = client.list_notes_by_tag(tag_id=7)
    assert len(result) == 2
    assert call_count[0] == 2


# ── get_note ──────────────────────────────────────────────────────────────────

def test_get_note_basic():
    note = {"id": 42, "title": "CLAUDE.md", "content": "# Hello", "updated_at": "2026-01-01T00:00:00+00:00"}
    routes = {("GET", "/api/v1/notes/42"): (200, _ok(note))}
    with _make_client(routes) as client:
        result = client.get_note(42)
    assert result["id"] == 42
    assert result["content"] == "# Hello"

def test_get_note_compile_vars_uses_compile_endpoint():
    compiled_data = {
        "compiled_content": "Hello Alice",
        "unresolved": [],
        "title": "Note",
    }
    routes = {("GET", "/api/plugins/ai_variables/compile/42"): (200, _ok(compiled_data))}
    with _make_client(routes) as client:
        result = client.get_note(42, compile_vars=True)
    assert result["content"] == "Hello Alice"
    assert result["unresolved"] == []

def test_get_note_compile_vars_fallback_on_no_variables_block():
    status, err_body = _err("No variables block", "NO_VARIABLES_BLOCK", 422)
    note = {"id": 42, "title": "Plain Note", "content": "# Plain", "updated_at": ""}
    routes = {
        ("GET", "/api/plugins/ai_variables/compile/42"): (status, err_body),
        ("GET", "/api/v1/notes/42"): (200, _ok(note)),
    }
    with _make_client(routes) as client:
        result = client.get_note(42, compile_vars=True)
    assert result["content"] == "# Plain"

def test_get_note_compile_vars_non_422_raises():
    status, err_body = _err("Server error", "INTERNAL", 500)
    routes = {("GET", "/api/plugins/ai_variables/compile/42"): (status, err_body)}
    with _make_client(routes) as client:
        with pytest.raises(APIError) as exc_info:
            client.get_note(42, compile_vars=True)
    assert exc_info.value.code == "INTERNAL"


# ── update_note ───────────────────────────────────────────────────────────────

def test_update_note_success():
    updated = {"id": 42, "updated_at": "2026-06-01T00:00:00+00:00"}
    routes = {("PUT", "/api/v1/notes/42"): (200, _ok(updated))}
    with _make_client(routes) as client:
        result = client.update_note(42, content="New content")
    assert result["updated_at"] == "2026-06-01T00:00:00+00:00"

def test_update_note_with_title():
    updated = {"id": 42, "title": "New Title", "updated_at": "2026-06-01T00:00:00+00:00"}
    routes = {("PUT", "/api/v1/notes/42"): (200, _ok(updated))}
    with _make_client(routes) as client:
        result = client.update_note(42, content="New content", title="New Title")
    assert result["title"] == "New Title"


# ── get_current_user ──────────────────────────────────────────────────────────

def test_get_current_user():
    profile = {"id": 1, "email": "test@example.com", "username": "testuser"}
    routes = {("GET", "/api/v1/user/profile"): (200, _ok(profile))}
    with _make_client(routes) as client:
        result = client.get_current_user()
    assert result["email"] == "test@example.com"
