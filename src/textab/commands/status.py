from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import typer

from textab.client import TexTabClient
from textab.config import load_credentials, load_project_config
from textab.errors import APIError, CredentialsNotFound, TextabError


def status_command(
    fetch: bool = typer.Option(
        False, "--fetch",
        help="Check server for remote changes (requires network).",
    ),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON."),
) -> None:
    """Show sync status of all tracked files."""
    try:
        cfg = load_project_config()
    except TextabError as e:
        typer.echo(str(e), err=True)
        raise typer.Exit(1)

    project_root = Path.cwd()
    last_synced_dt = _parse_dt(cfg.last_synced)

    server_map: dict[int, str] = {}   # note_id → server updated_at

    if fetch:
        try:
            token, cred_base_url = load_credentials()
            base_url = cfg.base_url or cred_base_url
            with TexTabClient(token, base_url) as client:
                summaries = client.list_notes_by_tag(cfg.tag_id)
            server_map = {s["id"]: s.get("updated_at", "") for s in summaries}
        except CredentialsNotFound as e:
            typer.echo(f"Warning: {e} — skipping remote check.", err=True)
        except APIError as e:
            typer.echo(f"Warning: API error during --fetch: {e} — skipping remote check.", err=True)

    rows = []
    for note in cfg.notes:
        note_id = note["id"]
        rel = note["local_path"]
        local_path = project_root / rel
        stored_server_dt = _parse_dt(note.get("server_updated_at"))

        if not local_path.exists():
            status = "Missing locally"
            icon = "?"
        else:
            local_mtime = datetime.fromtimestamp(
                local_path.stat().st_mtime, tz=timezone.utc
            )
            local_modified = (
                last_synced_dt is not None
                and _trunc(local_mtime) > _trunc(last_synced_dt)
            )

            if fetch and note_id in server_map:
                server_dt = _parse_dt(server_map[note_id])
                server_changed = (
                    server_dt is not None
                    and stored_server_dt is not None
                    and _trunc(server_dt) > _trunc(stored_server_dt)
                )
                if local_modified and server_changed:
                    status = "Conflict (both changed)"
                    icon = "!"
                elif server_changed:
                    status = "Outdated (remote changes)"
                    icon = "U"
                elif local_modified:
                    status = "Modified locally"
                    icon = "M"
                else:
                    status = "Up to date"
                    icon = "✓"
            else:
                if local_modified:
                    status = "Modified locally"
                    icon = "M"
                else:
                    status = "Up to date"
                    icon = "✓"

        rows.append({"icon": icon, "path": rel, "status": status, "id": note_id})

    if json_output:
        import json
        typer.echo(json.dumps(rows, indent=2))
        return

    if not rows:
        typer.echo("No tracked files. Run `textab sync` to pull notes.")
        return

    typer.echo(f"Tag: {cfg.sync_tag}   Last synced: {cfg.last_synced or 'never'}")
    if not fetch:
        typer.echo("(Run with --fetch to check for remote changes)")
    typer.echo("")

    col = max(len(r["path"]) for r in rows) + 2
    for r in rows:
        typer.echo(f"  {r['icon']}  {r['path']:<{col}} {r['status']}")


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
    return dt.replace(microsecond=0)
