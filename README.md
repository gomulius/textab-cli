# textab-cli

Sync [TexTab](https://textab.app) cloud notes to local AI coding assistant configuration files (`CLAUDE.md`, `.cursorrules`, etc.).

## Installation

```bash
pip install textab-cli
# or, recommended:
pipx install textab-cli
```

## Quick Start

**Already have local AI config files? Upload them to TexTab:**

```bash
textab auth login
cd ~/my-project
textab upload --all --tag my-project   # auto-discovers CLAUDE.md, .cursorrules, etc.
```

**Already have notes in TexTab? Pull them locally:**

```bash
textab auth login
cd ~/my-project
textab init        # link directory to a TexTab tag
textab sync        # pull notes to local files
textab push CLAUDE.md  # push edits back
```

## Commands

| Command | Description |
|---|---|
| `textab auth login` | Store API credentials |
| `textab auth logout` | Remove stored credentials |
| `textab auth whoami` | Show current user |
| `textab init` | Link current directory to a TexTab tag |
| `textab sync` | Pull remote notes to local files |
| `textab push <file>` | Push local file changes to TexTab |
| `textab status` | Show sync status of tracked files |
| `textab upload <file> --tag <tag>` | Upload a local file to TexTab as a new note |
| `textab upload --all --tag <tag>` | Auto-discover and upload all AI assistant config files |

## `upload --all` — Auto-discovered files

`textab upload --all` scans the current directory for known AI assistant config files and uploads any it finds:

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

Creates or updates `.textab` automatically — no need to run `textab init` first.

## Auto-Routing

Note titles are mapped to local files automatically:

| Note title | Local path |
|---|---|
| `CLAUDE.md` | `./CLAUDE.md` |
| `.cursorrules` | `./.cursorrules` |
| `.agents/rules/workflow.md` | `./.agents/rules/workflow.md` |
| `My Workflow` | `./my-workflow.md` |

## The `.textab` config file

Created by `textab init` or `textab upload`, updated automatically by `textab sync`, `textab push`, and `textab upload`. Safe to commit to git — it contains no credentials, only note IDs and file paths.

Add it to your `.gitignore` if you prefer personal configurations to stay local.

## Full documentation

See [MANUAL.md](MANUAL.md) for the complete reference including all flags, conflict behaviour, and examples.
