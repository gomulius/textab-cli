"""
textab sync — pull all notes for the linked tag and write them to local files.

Conflict scenarios:
  A. Server unchanged, local clean       → skip (already up to date)
  B. Server updated, local clean         → overwrite local
  C. Server unchanged, local modified    → skip + warn (use `textab push`)
  D. Server updated, local modified      → true conflict: write .server.md + warn
"""

from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import typer

from textab.client import TexTabClient
from textab.compiler import compile_note
from textab.config import (
    DOTFILE_NAME,
    NoteRef,
    load_credentials,
    load_project_config,
    save_project_config,
)
from textab.errors import APIError, CredentialsNotFound, RoutingConflict, TextabError
from textab.router import check_routing_conflicts, note_title_to_path, relative_path


def sync_command(
    compile_vars: bool = typer.Option(
        True, "--compile/--no-compile",
        help="Compile AI Variables blocks before writing files.",
    ),
    dry_run: bool = typer.Option(
        False, "--dry-run",
        help="Show what would change without writing anything.",
    ),
    force: bool = typer.Option(
        False, "--force",
        help="Overwrite local files even when locally modified.",
    ),
) -> None:
    """Pull all tagged notes from TexTab and write them to local files."""
    try:
        cfg = load_project_config()
    except TextabError as e:
        typer.echo(str(e), err=True)
        raise typer.Exit(1)

    try:
        token, cred_base_url = load_credentials()
    except CredentialsNotFound as e:
        typer.echo(str(e), err=True)
        raise typer.Exit(1)

    base_url = cfg.base_url or cred_base_url
    project_root = Path.cwd()
    dotfile = project_root / DOTFILE_NAME

    try:
        with TexTabClient(token, base_url) as client:
            typer.echo(f"Fetching notes tagged '{cfg.sync_tag}'…")
            summaries = client.list_notes_by_tag(cfg.tag_id)

        if not summaries:
            typer.echo("No notes found for that tag.")
            return

        # Check for routing conflicts before doing anything
        try:
            check_routing_conflicts(summaries, project_root)
        except RoutingConflict as e:
            typer.echo(f"Routing conflict: {e}", err=True)
            raise typer.Exit(1)

        last_synced_dt = _parse_dt(cfg.last_synced)
        counters = {"new": 0, "updated": 0, "skipped": 0, "conflict": 0, "warn_local": 0}
        server_ids = {s["id"] for s in summaries}

        with TexTabClient(token, base_url) as client:
            for summary in summaries:
                note_id = summary["id"]
                title = summary["title"]
                server_updated_at = summary.get("updated_at", "")
                server_dt = _parse_dt(server_updated_at)

                local_path = note_title_to_path(title, project_root)
                rel = relative_path(title)

                stored = cfg.get_note_by_id(note_id)
                stored_server_dt = _parse_dt(stored["server_updated_at"]) if stored else None
                local_exists = local_path.exists()
                local_mtime_dt = (
                    datetime.fromtimestamp(local_path.stat().st_mtime, tz=timezone.utc)
                    if local_exists else None
                )

                local_modified = (
                    local_exists
                    and last_synced_dt is not None
                    and local_mtime_dt is not None
                    and _trunc(local_mtime_dt) > _trunc(last_synced_dt)
                )
                server_changed = (
                    stored_server_dt is None
                    or (server_dt is not None and _trunc(server_dt) > _trunc(stored_server_dt))
                )
                is_new = stored is None

                # Determine action
                if is_new:
                    action = "new"
                elif not server_changed and not local_modified:
                    action = "skip"
                elif server_changed and not local_modified:
                    action = "update"
                elif not server_changed and local_modified:
                    action = "warn_local"
                else:
                    action = "conflict"

                if action == "skip":
                    counters["skipped"] += 1
                    continue

                if action == "warn_local":
                    typer.echo(
                        f"  [skip]     {rel}  (modified locally — use `textab push {rel}` to upload)"
                    )
                    counters["warn_local"] += 1
                    continue

                if action == "conflict" and not force:
                    # Write the server version alongside the local file
                    server_file = local_path.with_suffix(".server" + local_path.suffix)
                    typer.echo(
                        f"  [conflict] {rel}  (both local and remote changed)\n"
                        f"             Server version written to: {server_file.name}\n"
                        f"             Resolve manually, then `textab push {rel} --force`"
                    )
                    if not dry_run:
                        note_data = client.get_note(note_id, compile_vars=compile_vars)
                        content, unresolved = _extract_content(note_data, compile_vars)
                        _warn_unresolved(rel, unresolved)
                        server_file.parent.mkdir(parents=True, exist_ok=True)
                        server_file.write_text(content, encoding="utf-8")
                    counters["conflict"] += 1
                    continue

                # Fetch full content
                if dry_run:
                    label = "new" if is_new else "update"
                    typer.echo(f"  [{label}]     {rel}  (dry-run, not written)")
                    counters["new" if is_new else "updated"] += 1
                    continue

                note_data = client.get_note(note_id, compile_vars=compile_vars)
                content, unresolved = _extract_content(note_data, compile_vars)
                _warn_unresolved(rel, unresolved)

                local_path.parent.mkdir(parents=True, exist_ok=True)
                local_path.write_text(content, encoding="utf-8")
                typer.echo(f"  {'[new]' if is_new else '[updated]':12} {rel}")

                cfg.upsert_note(NoteRef(
                    id=note_id,
                    title=title,
                    local_path=rel,
                    server_updated_at=server_updated_at or "",
                ))
                counters["new" if is_new else "updated"] += 1

        # Warn about notes that disappeared from the tag
        for stored_note in list(cfg.notes):
            if stored_note["id"] not in server_ids:
                typer.echo(
                    f"  [removed]  {stored_note['local_path']}  "
                    f"(no longer tagged '{cfg.sync_tag}' on server — local file kept)"
                )
                cfg.remove_note(stored_note["id"])

        now_iso = datetime.now(tz=timezone.utc).isoformat()
        cfg.last_synced = now_iso
        if not dry_run:
            save_project_config(cfg, dotfile)

        typer.echo(
            f"\nDone. {counters['new']} new, {counters['updated']} updated, "
            f"{counters['skipped']} up to date, {counters['warn_local']} local-only, "
            f"{counters['conflict']} conflicts."
        )

    except APIError as e:
        typer.echo(f"API error: {e}", err=True)
        raise typer.Exit(1)
    except TextabError as e:
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _extract_content(note_data: dict, compile_vars: bool) -> tuple[str, list[str]]:
    """
    Extract content from the note dict.
    If compile_vars is True but the server didn't compile (no compile endpoint),
    fall back to client-side compilation.
    """
    content = note_data.get("content") or ""
    # Server returned pre-compiled content → unresolved already in data
    if "unresolved" in note_data:
        return content, note_data.get("unresolved", [])
    # Client-side compilation fallback
    if compile_vars:
        compiled, unresolved, _ = compile_note(content)
        return compiled, unresolved
    return content, []


def _warn_unresolved(rel: str, unresolved: list[str]) -> None:
    if unresolved:
        typer.echo(
            f"  [warning]  {rel} has unresolved variables: "
            + ", ".join(f"{{{{{v}}}}}" for v in unresolved)
        )


def _parse_dt(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    try:
        from dateutil.parser import parse as _parse
        dt = _parse(value)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except Exception:
        return None


def _trunc(dt: datetime) -> datetime:
    """Truncate to second precision for comparison."""
    return dt.replace(microsecond=0)
