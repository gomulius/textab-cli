import typer

from textab.client import TexTabClient
from textab.config import delete_credentials, load_credentials, save_credentials
from textab.errors import APIError, CredentialsNotFound, TextabError

app = typer.Typer(help="Manage TexTab authentication credentials.")

DEFAULT_BASE_URL = "https://textab.app/pro"


@app.command("login")
def login(
    token: str = typer.Option(
        ..., prompt="Personal Access Token", hide_input=True,
        help="Generate one in TexTab → Profile → API Keys.",
    ),
    base_url: str = typer.Option(
        DEFAULT_BASE_URL, prompt="TexTab base URL",
        help="Base URL of your TexTab instance.",
    ),
) -> None:
    """Store API credentials and verify they work."""
    try:
        with TexTabClient(token, base_url) as client:
            user = client.get_current_user()
        email = user.get("email") or user.get("username") or "unknown"
        save_credentials(token, base_url)
        typer.echo(f"Authenticated as {email}")
        typer.echo("Credentials saved. Run `textab init` to link a project directory.")
    except APIError as e:
        typer.echo(f"Authentication failed: {e}", err=True)
        raise typer.Exit(1)
    except TextabError as e:
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)


@app.command("logout")
def logout() -> None:
    """Remove stored credentials."""
    if delete_credentials():
        typer.echo("Credentials removed.")
    else:
        typer.echo("No credentials were stored.")


@app.command("whoami")
def whoami() -> None:
    """Show the currently authenticated user."""
    try:
        token, base_url = load_credentials()
        with TexTabClient(token, base_url) as client:
            user = client.get_current_user()
        email = user.get("email") or user.get("username") or "unknown"
        typer.echo(f"Logged in as: {email}")
        typer.echo(f"Base URL:     {base_url}")
    except CredentialsNotFound as e:
        typer.echo(str(e), err=True)
        raise typer.Exit(1)
    except APIError as e:
        typer.echo(f"API error: {e}", err=True)
        raise typer.Exit(1)
