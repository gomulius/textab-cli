import typer

from textab.commands import auth, init_, sync, push, status, upload

app = typer.Typer(
    name="textab",
    help="Sync TexTab notes to local AI coding assistant config files.",
    no_args_is_help=True,
    rich_markup_mode="rich",
)

app.add_typer(auth.app, name="auth", help="Manage authentication credentials.")
app.command("init")(init_.init_command)
app.command("sync")(sync.sync_command)
app.command("push")(push.push_command)
app.command("status")(status.status_command)
app.command("upload")(upload.upload_command)


def main() -> None:
    app()
