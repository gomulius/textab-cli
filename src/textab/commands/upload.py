"""
textab upload — push local files to TexTab as new notes and tag them.

Single file:   textab upload CLAUDE.md --tag my-project
Bulk discover: textab upload --all --tag my-project
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import typer

from textab.client import TexTabClient
from textab.config import (
    DOTFILE_NAME,
    NoteRef,
    ProjectConfig,
    load_credentials,
    load_project_config,
    save_project_config,
)
from textab.errors import APIError, CredentialsNotFound, TextabError

# Known AI coding-assistant config files, checked relative to the project root.
_AI_FILES = [
    "CLAUDE.md",                            # Claude Code
    "CLAUDE.local.md",                      # Claude Code (local overrides)
    "AGENTS.md",                            # OpenAI Codex
    "GEMINI.md",                            # Gemini CLI
    ".cursorrules",                         # Cursor
    ".windsurfrules",                       # Windsurf
    ".clinerules",                          # Cline
    ".github/copilot-instructions.md",      # GitHub Copilot
    ".aider.conf.yml",                      # Aider
]


def upload_command(
    filename: Optional[str] = typer.Argument(
        None, help="Local file to upload (e.g. CLAUDE.md)."
    ),
    tag: str = typer.Option(
        ..., "--tag", "-t",
        help="TexTab tag to assign to the uploaded note(s).",
    ),
    all_files: bool = typer.Option(
        False, "--all",
        help="Discover and upload all known AI assistant config files.",
    ),
    title: Optional[str] = typer.Option(
        None, "--title",
        help="Override note title on the server (single-file upload only).",
    ),
    dry_run: bool = typer.Option(
        False, "--dry-run",
        help="Show what would be uploaded without making any changes.",
    ),
    force: bool = typer.Option(
        False, "--force",
        help="Re-upload files that are already tracked in .textab.",
    ),
) -> None:
    """Upload local files to TexTab as notes and tag them.

    \b
    Upload a single file:
      textab upload CLAUDE.md --tag my-project
      textab upload .cursorrules --tag my-project
      textab upload .github/copilot-instructions.md --tag my-project

    \b
    Auto-discover and upload all AI assistant config files:
      textab upload --all --tag my-project

    \b
    Preview what would be uploaded without making changes:
      textab upload --all --tag my-project --dry-run

    \b
    Re-upload files that are already tracked:
      textab upload --all --tag my-project --force

    \b
    Files discovered by --all:
      CLAUDE.md, CLAUDE.local.md  (Claude Code)
      AGENTS.md                   (OpenAI Codex)
      GEMINI.md                   (Gemini CLI)
      .cursorrules                (Cursor)
      .windsurfrules              (Windsurf)
      .clinerules                 (Cline)
      .github/copilot-instructions.md  (GitHub Copilot)
      .aider.conf.yml             (Aider)
    """
    if not filename and not all_files:
        typer.echo(
            "Provide a filename or use --all to discover AI assistant files.\n"
            "Examples:\n"
            "  textab upload CLAUDE.md --tag my-project\n"
            "  textab upload --all --tag my-project",
            err=True,
        )
        raise typer.Exit(1)

    if filename and all_files:
        typer.echo("Cannot combine a filename with --all.", err=True)
        raise typer.Exit(1)

    if title and all_files:
        typer.echo("--title is only valid for single-file uploads.", err=True)
        raise typer.Exit(1)

    try:
        token, cred_base_url = load_credentials()
    except CredentialsNotFound as e:
        typer.echo(str(e), err=True)
        raise typer.Exit(1)

    project_root = Path.cwd()
    dotfile = project_root / DOTFILE_NAME

    try:
        cfg = load_project_config(dotfile)
    except TextabError:
        cfg = None  # will be created after tag lookup

    try:
        with TexTabClient(token, cred_base_url) as client:
            tag_obj = client.get_tag_by_name(tag)
            if tag_obj is None:
                typer.echo(
                    f"Tag '{tag}' not found in your TexTab account.\n"
                    "Create it in the TexTab UI first, or check the spelling.",
                    err=True,
                )
                raise typer.Exit(1)

            tag_id = tag_obj["id"]

            if cfg is None:
                cfg = ProjectConfig(sync_tag=tag, tag_id=tag_id)
            else:
                cfg.sync_tag = tag
                cfg.tag_id = tag_id

            # Build list of (abs_path, rel_str, note_title)
            if all_files:
                candidates = _discover(project_root)
                if not candidates:
                    typer.echo(
                        "No known AI assistant files found in this directory.\n"
                        "Searched for: " + ", ".join(_AI_FILES)
                    )
                    return
            else:
                candidates = [_resolve(filename, project_root, title)]

            counters = {"created": 0, "updated": 0, "skipped": 0}

            for local_path, rel, note_title in candidates:
                if not local_path.exists():
                    typer.echo(f"  [skip]     {rel}  (file not found)")
                    counters["skipped"] += 1
                    continue

                tracked = cfg.get_note_by_path(rel)

                if tracked and not force:
                    typer.echo(
                        f"  [skip]     {rel}  "
                        f"(already tracked as note #{tracked['id']} — use --force to re-upload)"
                    )
                    counters["skipped"] += 1
                    continue

                if dry_run:
                    label = "update" if tracked else "create"
                    typer.echo(f"  [{label}]    {rel}  (dry-run, not uploaded)")
                    counters["updated" if tracked else "created"] += 1
                    continue

                content = local_path.read_text(encoding="utf-8")

                if tracked:
                    # Push to the existing note
                    result = client.update_note(tracked["id"], content=content)
                    updated_at = result.get("updated_at", "") if isinstance(result, dict) else ""
                    cfg.upsert_note(NoteRef(
                        id=tracked["id"],
                        title=tracked["title"],
                        local_path=rel,
                        server_updated_at=updated_at,
                    ))
                    typer.echo(f"  [updated]  {rel}  → note #{tracked['id']}")
                    counters["updated"] += 1
                else:
                    # Create a new note
                    result = client.create_note(title=note_title, content=content)
                    note_id = result["id"]

                    # Tag it
                    client.add_note_tag(note_id, tag_id=tag_id)

                    # Fetch metadata so we have a real updated_at for conflict detection
                    meta = client.get_note_meta(note_id)
                    updated_at = meta.get("updated_at", "")

                    cfg.upsert_note(NoteRef(
                        id=note_id,
                        title=note_title,
                        local_path=rel,
                        server_updated_at=updated_at,
                    ))
                    typer.echo(f"  [created]  {rel}  → note #{note_id}")
                    counters["created"] += 1

            if not dry_run:
                save_project_config(cfg, dotfile)

            typer.echo(
                f"\nDone. {counters['created']} created, "
                f"{counters['updated']} updated, "
                f"{counters['skipped']} skipped."
            )
            if counters["created"] or counters["updated"]:
                typer.echo("Run `textab sync` to verify round-trip consistency.")

    except APIError as e:
        typer.echo(f"API error: {e}", err=True)
        raise typer.Exit(1)
    except TextabError as e:
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _discover(project_root: Path) -> list[tuple[Path, str, str]]:
    """Return (abs_path, rel_str, title) for every AI file that exists on disk."""
    found = []
    for pattern in _AI_FILES:
        local_path = project_root / pattern
        if local_path.exists() and local_path.is_file():
            found.append((local_path, pattern, pattern))
    return found


def _resolve(
    filename: str, project_root: Path, title_override: Optional[str]
) -> tuple[Path, str, str]:
    """Return (abs_path, rel_str, title) for a caller-supplied filename."""
    local_path = Path(filename).resolve()
    try:
        rel = str(local_path.relative_to(project_root))
    except ValueError:
        rel = filename
    note_title = title_override or rel
    return local_path, rel, note_title
