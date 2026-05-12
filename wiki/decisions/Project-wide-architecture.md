# Decision: TUI app + collector pattern

**Date:** 2026-04-19
**Status:** decided

## Context

Need tool to browse + manage many git repos. User has folder trees like C:\users\me\projects\ with dozens of nested repos. Manual checking each is slow.

## Options considered

| Option | Pro | Con |
|--------|-----|-----|
| Web dashboard | Familiar UI, easy to share | Requires server + browser |
| CLI with flags | Lightweight, scriptable | No overview, tedious one-by-one |
| TUI (Textual) | Fast, local, keyboard-driven, low resource | Limited to terminal |
| GUI (Qt/Tkinter) | Rich UI, cross-platform | Heavyweight, maintenance burden |

## Decision

TUI app using Textual framework + separate collector module.

**Architecture:**
- `app.py` — GitplorerApp (UI rendering, keybindings, user interaction)
- `collector.py` — RepoInfo + collection logic (git operations, metadata capture)
- `config.py` — Config dataclass + TOML loading
- Worker threads — UI responsive during long scans

**Why:** TUI gives responsive, keyboard-friendly dashboard. Separation of concerns: app owns UI, collector owns git logic. Workers keep UI responsive during scan.

## Consequences

- Enables: fast overview of dozens of repos, instant filter/sort, detail drill-down
- Constrains: terminal-only (no web), single-machine (no network dashboard)
- Future: could extract collector as library for other tools
