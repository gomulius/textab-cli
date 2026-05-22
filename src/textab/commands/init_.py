from pathlib import Path

import typer

from textab.client import TexTabClient
from textab.config import (
    DOTFILE_NAME,
    ProjectConfig,
    load_credentials,
    save_project_config,
)
from textab.errors import APIError, CredentialsNotFound, TextabError


def init_command(
    tag: str = typer.Option(..., prompt="TexTab tag name to sync with this directory"),
    base_url: str = typer.Option(
        None, "--base-url", help="Override base URL (defaults to value stored in credentials)."
    ),
) -> None:
    """Link the current directory to a TexTab tag."""
    try:
        token, cred_base_url = load_credentials()
    except CredentialsNotFound as e:
        typer.echo(str(e), err=True)
        raise typer.Exit(1)

    effective_base_url = base_url or cred_base_url
    dotfile = Path.cwd() / DOTFILE_NAME

    if dotfile.exists():
        overwrite = typer.confirm(
            f".textab already exists in this directory. Overwrite?", default=False
        )
        if not overwrite:
            typer.echo("Aborted.")
            raise typer.Exit(0)

    try:
        with TexTabClient(token, effective_base_url) as client:
            tag_obj = client.get_tag_by_name(tag)
            if tag_obj is None:
                typer.echo(
                    f"Tag '{tag}' not found in your TexTab account.\n"
                    "Create it in the TexTab UI first, or check the spelling.",
                    err=True,
                )
                raise typer.Exit(1)

        cfg = ProjectConfig(
            sync_tag=tag,
            tag_id=tag_obj["id"],
            base_url=base_url,   # None means "use credentials base_url"
        )
        save_project_config(cfg, dotfile)

        typer.echo(f"Initialized .textab for tag '{tag}' (ID {tag_obj['id']}).")
        typer.echo("")
        typer.echo("Next step:  textab sync")
        typer.echo("")
        typer.echo(
            "Tip: .textab contains no credentials and is safe to commit to git.\n"
            "     Add it to .gitignore if you prefer personal configs to stay local."
        )

    except APIError as e:
        typer.echo(f"API error: {e}", err=True)
        raise typer.Exit(1)
    except TextabError as e:
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
