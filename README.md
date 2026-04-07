# gitplorer

A terminal dashboard for all your local Git repositories.

![Python](https://img.shields.io/badge/python-3.11%2B-blue) ![Textual](https://img.shields.io/badge/textual-TUI-green)

## Features

- Scans one or more directories for Git repos (configurable depth)
- Shows branch, working-tree status, last commit, age, and ahead/behind counts at a glance
- Dirty repos sorted to the top
- Inline commit and remote URL expansion
- One-key push and VSCode integration
- Detail view with full status, stash entries, and last 10 commits

## Requirements

- Python 3.11+
- [Textual](https://github.com/Textualize/textual) >= 0.50

## Installation

```bash
pip install .
```

Or in development mode:

```bash
pip install -e .
```

Then run:

```bash
gitplorer
```

Or directly:

```bash
python main.py
```

## Configuration

Create `~/.gitplorer.toml` to customize the scan:

```toml
scan_dirs = ["~/projects", "~/work"]
depth     = 2
exclude   = [".venv", "node_modules", "__pycache__"]
```

| Option | Default | Description |
|---|---|---|
| `scan_dirs` | `["D:/Projects"]` | Directories to scan for repos |
| `depth` | `2` | How many levels deep to recurse |
| `exclude` | `[".venv", "node_modules", "__pycache__"]` | Directory names to skip |

## Keybindings

### Main table

| Key | Action |
|---|---|
| `Enter` | Open detail view |
| `v` | Open repo in VSCode |
| `→` | Expand last 5 commits inline |
| `←` | Collapse expanded rows |
| `r` | Show / hide remote URL |
| `p` | `git push` the selected repo |
| `f` | Toggle dirty-only filter |
| `F5` | Refresh all repos |
| `q` | Quit |

### Detail view

| Key | Action |
|---|---|
| `Enter` / `Esc` / `q` | Back to table |
| `v` | Open repo in VSCode |

## Status indicators

| Symbol | Meaning |
|---|---|
| `✓` (green) | Clean working tree |
| `+N` (green) | N staged changes |
| `~N` (yellow) | N modified files |
| `?N` (dim) | N untracked files |
| `↑N` (magenta) | N commits ahead of remote |
| `↓N` (magenta) | N commits behind remote |
| `ERR` (red) | Could not read repo |
