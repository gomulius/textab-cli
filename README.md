# textab-cli

Sync [TexTab](https://textab.app) cloud notes to local AI coding assistant configuration files (`CLAUDE.md`, `.cursorrules`, etc.).

## Installation

```bash
pip install textab-cli
# or, recommended:
pipx install textab-cli
```

## Quick Start

```bash
# 1. Authenticate with your TexTab Personal Access Token
textab auth login

# 2. Link the current project directory to a TexTab tag
textab init

# 3. Pull all notes tagged with that tag to local files
textab sync

# 4. Check what has changed
textab status

# 5. Push a locally edited file back to TexTab
textab push CLAUDE.md
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

## Auto-Routing

Note titles are mapped to local files automatically:

| Note title | Local path |
|---|---|
| `CLAUDE.md` | `./CLAUDE.md` |
| `.cursorrules` | `./.cursorrules` |
| `.agents/rules/workflow.md` | `./.agents/rules/workflow.md` |
| `My Workflow` | `./my-workflow.md` |

## The `.textab` config file

Running `textab init` creates a `.textab` file in your project root. It is safe to commit to git — it contains no credentials, only note IDs and file paths.

Add it to your `.gitignore` if you prefer personal configurations to stay local.
