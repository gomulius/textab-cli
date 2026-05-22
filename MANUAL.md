# TexTab CLI — User Manual

## Overview

`textab` is a command-line tool that syncs your TexTab notes to local files, making them available as config files for AI coding assistants (CLAUDE.md, .cursorrules, etc.).

---

## Installation

### Requirements

- Python 3.9 or later
- pip

### Install from source

```bash
git clone <repo>
cd textab-cli
pip install .
```

### Install in development mode (with test dependencies)

```bash
pip install -e ".[dev]"
```

### Verify installation

```bash
textab --help
```

---

## Quick Start

**New project — upload existing local files to TexTab:**

```bash
textab auth login
cd ~/my-project
textab upload --all --tag my-project   # discovers and uploads AI config files
```

**Existing TexTab notes — pull them to a local folder:**

```bash
textab auth login
cd ~/my-project
textab init                            # link directory to a TexTab tag
textab sync                            # pull notes to local files
textab push CLAUDE.md                  # push edits back
```

---

## Commands

### `textab auth login`

Store API credentials and verify they work.

```bash
textab auth login
```

You will be prompted for:

- **Personal Access Token** — generate one in TexTab → Profile → API Keys
- **TexTab base URL** — defaults to `https://textab.app/pro`

Credentials are stored in the OS keychain (macOS Keychain, Windows Credential Manager, Linux Secret Service). If the keychain is unavailable they fall back to `~/.textab-credentials` (chmod 600).

| Flag | Description |
|---|---|
| `--token TEXT` | Provide token non-interactively |
| `--base-url TEXT` | Override base URL |

---

### `textab auth logout`

Remove stored credentials.

```bash
textab auth logout
```

---

### `textab auth whoami`

Show the currently authenticated user and base URL.

```bash
textab auth whoami
# Logged in as: you@example.com
# Base URL:     https://textab.app/pro
```

---

### `textab init`

Link the current directory to a TexTab tag. Creates a `.textab` config file in the current directory.

```bash
textab init
# Prompt: TexTab tag name to sync with this directory
```

The tag must already exist in your TexTab account. `.textab` contains no credentials and is safe to commit to git (or add to `.gitignore` for personal configs).

| Flag | Description |
|---|---|
| `--tag TEXT` | Tag name (prompted if omitted) |
| `--base-url TEXT` | Override base URL for this project |

---

### `textab sync`

Pull all notes tagged with the linked tag from TexTab and write them to local files.

```bash
textab sync
```

**Conflict behaviour:**

| Scenario | Action |
|---|---|
| Server unchanged, local clean | Skip |
| Server updated, local clean | Overwrite local file |
| Local modified, server unchanged | Skip + warn (use `textab push`) |
| Both changed | Write `.server.md` alongside local file, warn to resolve manually |

| Flag | Description |
|---|---|
| `--compile` / `--no-compile` | Compile AI Variables blocks before writing (default: on) |
| `--dry-run` | Show what would change without writing anything |
| `--force` | Overwrite local files even when locally modified |

**Example output:**

```
Fetching notes tagged 'my-project'…
  [new]        CLAUDE.md
  [updated]    .cursorrules
  [skip]       README.md  (modified locally — use `textab push README.md` to upload)

Done. 1 new, 1 updated, 1 up to date, 1 local-only, 0 conflicts.
```

---

### `textab push <filename>`

Push a locally edited file back to its TexTab note. The previous server state is automatically versioned before overwriting.

```bash
textab push CLAUDE.md
textab push docs/architecture.md
```

Before pushing, the server is checked for remote changes. If the server has newer content the push is blocked — run `textab sync` first or use `--force`.

| Flag | Description |
|---|---|
| `--force` | Push even if the server has newer changes |
| `--title TEXT` | Override the note title on the server |

**Example output:**

```
Pushed 'CLAUDE.md' → note #1263.
Previous server state was automatically versioned.
```

---

### `textab upload [filename] --tag <tag>`

Upload local files to TexTab as new notes and tag them. Also creates or updates `.textab` so the files are immediately tracked for future `push`/`sync`.

**Single file:**

```bash
textab upload CLAUDE.md --tag my-project
textab upload .github/copilot-instructions.md --tag my-project
```

**Bulk — auto-discovers all AI assistant config files in the current directory:**

```bash
textab upload --all --tag my-project
```

Files discovered by `--all`:

| File | Tool |
|---|---|
| `CLAUDE.md`, `CLAUDE.local.md` | Claude Code |
| `AGENTS.md` | OpenAI Codex |
| `GEMINI.md` | Gemini CLI |
| `.cursorrules` | Cursor |
| `.windsurfrules` | Windsurf |
| `.clinerules` | Cline |
| `.github/copilot-instructions.md` | GitHub Copilot |
| `.aider.conf.yml` | Aider |

The tag must already exist in your TexTab account. If `.textab` does not exist it is created automatically — no need to run `textab init` first.

| Flag | Description |
|---|---|
| `--tag TEXT` | TexTab tag to assign (required) |
| `--all` | Discover and upload all known AI assistant files |
| `--title TEXT` | Override note title on the server (single-file only) |
| `--dry-run` | Show what would be uploaded without making changes |
| `--force` | Re-upload files that are already tracked in `.textab` |

**Behaviour notes:**

- Already-tracked files are skipped by default. Use `--force` to re-upload them — this updates the existing note rather than creating a duplicate.
- After a note is created the CLI fetches its `updated_at` timestamp from the server so that future `textab sync` and `textab push` conflict detection works correctly from day one.
- `--title` only affects the note title shown in the TexTab UI. The local file path is always tracked exactly as it appears on disk, so `push` and `sync` continue to work correctly regardless of the title.
- Notes uploaded with `--all` use the file's relative path as the title (e.g. `CLAUDE.md`, `.cursorrules`). This matches the file-naming rules so a `textab sync` on a fresh machine will place them back in exactly the same locations.

**Example output:**

```
  [created]  CLAUDE.md         → note #1263
  [created]  .cursorrules      → note #1264
  [skip]     AGENTS.md         (file not found)

Done. 2 created, 0 updated, 1 skipped.
Run `textab sync` to verify round-trip consistency.
```

---

### `textab status`

Show the sync status of all tracked files.

```bash
textab status
textab status --fetch
```

**Status icons:**

| Icon | Meaning |
|---|---|
| `✓` | Up to date |
| `M` | Modified locally since last sync |
| `U` | Outdated — remote has changes (requires `--fetch`) |
| `!` | Conflict — both local and remote changed (requires `--fetch`) |
| `?` | Missing locally |

| Flag | Description |
|---|---|
| `--fetch` | Check the server for remote changes (requires network) |
| `--json` | Output as JSON (useful for scripting) |

**Example output:**

```
Tag: my-project   Last synced: 2026-05-22T10:00:00+00:00
(Run with --fetch to check for remote changes)

  ✓  CLAUDE.md          Up to date
  M  .cursorrules        Modified locally
  ?  docs/notes.md       Missing locally
```

---

## File naming rules

Note titles are mapped to local paths using these rules, applied in order:

| Title pattern | Example | Local path |
|---|---|---|
| Contains `/` | `docs/architecture.md` | `docs/architecture.md` |
| Looks like a filename | `CLAUDE.md`, `.cursorrules` | `CLAUDE.md`, `.cursorrules` |
| Freeform text | `Project Overview` | `project-overview.md` |

---

## The `.textab` file

Created by `textab init` or `textab upload`, updated automatically by `textab sync`, `textab push`, and `textab upload`. Safe to commit to git.

```json
{
  "sync_tag": "my-project",
  "tag_id": 7,
  "last_synced": "2026-05-22T10:00:00+00:00",
  "base_url": null,
  "notes": [
    {
      "id": 1263,
      "title": "CLAUDE.md",
      "local_path": "CLAUDE.md",
      "server_updated_at": "2026-05-22T09:55:00+00:00"
    }
  ]
}
```

`base_url: null` means "use the URL from stored credentials". Set it explicitly per-project to target a different instance or the sandbox (`https://textab.app/sandbox`).
