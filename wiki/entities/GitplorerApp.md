# GitplorerApp

**Type:** component (TUI application class)
**Summary:** Main Textual app. Renders data table of repos with filtering, sorting, detail views. Bindings for refresh, filter, push, VSCode open, folder open.

## Key Facts

- Class: `GitplorerApp(App)` in app.py
- Maintains list `_all_repos: list[RepoInfo]`
- Renders via Textual DataTable + DirectoryTree sidebar
- Stateful: `_filter_dirty`, `_expanded_path`, `_expanded_commits`, `_remote_expanded_path`
- Worker-driven: runs `_load_repos()` in thread, updates on `WorkerState.SUCCESS/ERROR`

## Keybindings

- `f5`: refresh repos
- `f`: toggle dirty filter
- `b`: toggle sidebar (DirectoryTree browse)
- `enter`: open detail screen
- `v`: open VSCode
- `o`: open folder in Explorer
- `→`: expand commits for selected repo
- `←`: collapse all
- `r`: expand remote URL
- `p`: git push + auto-commit
- `q`: quit

## Connections

- [[RepoInfo]] — stores repo metadata
- [[RepoDetailScreen]] — pushes detail view when enter pressed
- [[Collector]] — loads repos via `find_and_collect(config)`
- [[Config]] — reads scan dirs, depth, exclude patterns

## Architecture patterns

- Single source of truth: `_all_repos`
- Render-on-change: every action calls `_render_table()`
- Thread-safe updates: use `call_from_thread()` for UI updates from worker
- Restore cursor position after refresh (restore_at logic)
