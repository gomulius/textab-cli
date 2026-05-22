from pathlib import Path


class TextabError(Exception):
    """Base class for all textab-cli errors."""


class CredentialsNotFound(TextabError):
    def __init__(self) -> None:
        super().__init__(
            "No credentials found. Run `textab auth login` first."
        )


class ProjectConfigNotFound(TextabError):
    def __init__(self) -> None:
        super().__init__(
            "No .textab file found in the current directory. "
            "Run `textab init` to link this directory to a TexTab tag."
        )


class APIError(TextabError):
    def __init__(self, message: str, code: str = "", status_code: int = 0) -> None:
        self.code = code
        self.status_code = status_code
        super().__init__(f"{message} (code={code}, http={status_code})" if code else message)


class ConflictError(TextabError):
    def __init__(self, note_id: int, title: str, server_updated_at: str) -> None:
        self.note_id = note_id
        self.title = title
        self.server_updated_at = server_updated_at
        super().__init__(
            f"Remote note '{title}' (#{note_id}) has changes since last sync "
            f"(server: {server_updated_at}). "
            "Run `textab sync` to pull first, or use --force to overwrite."
        )


class RoutingConflict(TextabError):
    def __init__(self, path: Path, note_ids: list) -> None:
        self.path = path
        self.note_ids = note_ids
        super().__init__(
            f"Multiple notes route to the same file '{path}': "
            f"note IDs {note_ids}. Rename one of them in TexTab."
        )
