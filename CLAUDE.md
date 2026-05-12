# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
# Install (dev mode)
pip install -e .

# Run
gitplorer
# or
python main.py

# No test suite — manual TUI testing only
```

## Architecture

Three-module Textual TUI app:

**`gitplorer/config.py`** — Loads `.gitplorer.toml` from CWD. Falls back to `D:/Projects`. Config drives scan dirs, depth, and exclude list.

**`gitplorer/collector.py`** — `_run()` wraps subprocess git calls with 5s timeout. `collect_repo()` runs ~4 git commands per repo to populate `RepoInfo`. `find_and_collect()` walks dirs recursively up to `config.depth`, deduplicates by resolved path, sorts dirty/errored repos to top.

**`gitplorer/app.py`** — Two Textual screens:
- `GitplorerApp` — main table screen. Workers run `_load_repos` and push ops on background threads. `_render_table()` rebuilds the full `DataTable` each time, inserting inline expansion rows with prefixed keys (`__commit__*`, `__remote__*`) to distinguish them from real repo rows.
- `RepoDetailScreen` — detail overlay pushed onto the screen stack. Gathers git info in a worker thread, renders Rich markup into a `Static`.

**`_push_with_auto_commit()`** in `app.py` — auto-stages and commits with timestamp before pushing (the "auto push" commits in git log).

**Key design constraint:** `DataTable` row keys double as repo path strings. Expansion rows use `_COMMIT_KEY_PREFIX` / `_REMOTE_KEY_PREFIX` guards everywhere cursor position is read — any new row-selection logic must check `_is_expand_key()`.

## Configuration

`.gitplorer.toml` in the working directory (not `~/.gitplorer.toml` despite what README says — `load_config()` reads from `.`):

```toml
scan_dirs = ["E:/Projects"]
depth     = 2
exclude   = [".venv", "node_modules", "__pycache__", "dist", "build"]
```
