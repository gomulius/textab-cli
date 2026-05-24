import typer

from textab.commands import auth, init_, sync, push, status, upload

app = typer.Typer(
    name="textab",
    help="Sync TexTab notes to local AI coding assistant config files.\n\nRun 'textab examples' to see common usage patterns.",
    no_args_is_help=True,
    rich_markup_mode="rich",
)

app.add_typer(auth.app, name="auth", help="Manage authentication credentials.")
app.command("init")(init_.init_command)
app.command("sync")(sync.sync_command)
app.command("push")(push.push_command)
app.command("status")(status.status_command)
app.command("upload")(upload.upload_command)


@app.command("examples")
def examples_command() -> None:
    """Show common usage examples."""
    typer.echo("""
FIRST-TIME SETUP
  textab auth login

UPLOAD existing local AI config files to TexTab
  textab upload --all --tag my-project          # auto-discover all AI files
  textab upload CLAUDE.md --tag my-project      # single file
  textab upload --all --tag my-project --dry-run  # preview first

PULL notes from TexTab to a local folder
  textab init --tag my-project                  # link directory to a tag
  textab sync                                   # pull all tagged notes
  textab sync --dry-run                         # preview without writing

CHECK STATUS
  textab status                                 # offline (local mtime check)
  textab status --fetch                         # also checks the server

PUSH local edits back to TexTab
  textab push CLAUDE.md
  textab push .cursorrules --force              # overwrite even if server is newer

ACCOUNT
  textab auth whoami                            # show logged-in user
  textab auth logout

Run 'textab COMMAND --help' for full options and flags per command.
""")


def main() -> None:
    app()
