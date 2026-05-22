from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import typer

from textab.client import TexTabClient
from textab.config import (
    DOTFILE_NAME,
    load_credentials,
    load_project_config,
    save_project_config,
)
from textab.errors import APIError, CredentialsNotFound, TextabError


def push_command(
    filename: str = typer.Argument(..., help="Local file to push (e.g. CLAUDE.md)"),
    force: bool = typer.Option(
        False, "--force",
        help="Push even if the server has newer changes (server will auto-version first).",
    ),
    title: Optional[str] = typer.Option(
        None, "--title", help="Override the note title on the server."
    ),
) -> None:
    """Push a local file back to its TexTab note (server auto-versions the previous state)."""
    try:
        cfg = load_project_config()
    except TextabError as e:
        typer.echo(str(e), err=True)
        raise typer.Exit(1)

    # Normalise filename to a relative path string
    local_path = Path(filename).resolve()
    project_root = Path.cwd()
    try:
        rel = str(local_path.relative_to(project_root))
    except ValueError:
        rel = filename

    stored = cfg.get_note_by_path(rel)
    if stored is None:
        # Try matching by basename too
        stored = next(
            (n for n in cfg.notes if Path(n["local_path"]).name == Path(rel).name),
            None,
        )
    if stored is None:
        typer.echo(
            f"'{filename}' is not tracked in .textab.\n"
            "Run `textab sync` first to pull the note from TexTab.",
            err=True,
        )
        raise typer.Exit(1)

    if not local_path.exists():
        typer.echo(f"File not found: {local_path}", err=True)
        raise typer.Exit(1)

    try:
        token, cred_base_url = load_credentials()
    except CredentialsNotFound as e:
        typer.echo(str(e), err=True)
        raise typer.Exit(1)

    base_url = cfg.base_url or cred_base_url
    note_id = stored["id"]
    stored_server_dt = _parse_dt(stored.get("server_updated_at"))

    try:
        with TexTabClient(token, base_url) as client:
            # Conflict check
            if not force:
                server_note = client.get_note_meta(note_id)
                server_updated_at = server_note.get("updated_at", "")
                server_dt = _parse_dt(server_updated_at)

                if (
                    server_dt is not None
                    and stored_server_dt is not None
                    and _trunc(server_dt) > _trunc(stored_server_dt)
                ):
                    typer.echo(
                        f"Conflict: remote note has changes since last sync.\n"
                        f"  Server:    {server_updated_at}\n"
                        f"  Last sync: {stored.get('server_updated_at', 'never')}\n\n"
                        "Run `textab sync` to pull remote changes first.\n"
                        "Or use --force to overwrite (the previous server state will be auto-versioned).",
                        err=True,
                    )
                    raise typer.Exit(1)

            content = local_path.read_text(encoding="utf-8")
            result = client.update_note(note_id, content=content, title=title)

        # Update stored server_updated_at
        new_updated_at = result.get("updated_at") if isinstance(result, dict) else None
        if new_updated_at:
            stored["server_updated_at"] = new_updated_at

        now_iso = datetime.now(tz=timezone.utc).isoformat()
        cfg.last_synced = now_iso
        save_project_config(cfg, project_root / DOTFILE_NAME)

        typer.echo(
            f"Pushed '{rel}' → note #{note_id}.\n"
            "Previous server state was automatically versioned."
        )

    except APIError as e:
        typer.echo(f"API error: {e}", err=True)
        raise typer.Exit(1)
    except TextabError as e:
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)


def _parse_dt(value):
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
