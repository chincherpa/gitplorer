# Repo Panel Design

**Date:** 2026-05-14  
**Status:** Approved

## Summary

Add a persistent right-side panel to `GitplorerApp` that shows commit history and repo metadata for the currently selected repository. Panel updates automatically as the cursor moves through the table.

## Layout

`GitplorerApp.compose()` changes: the inner content area becomes a horizontal split between `DataTable` and a new `RepoPanel` widget.

```
Screen
└── Horizontal
    ├── #sidebar          (existing, togglable via b)
    └── #main-area (Vertical)
        ├── Label#status  (existing)
        └── Horizontal    ← new
            ├── DataTable (width: 1fr)
            └── RepoPanel (width: reactive, default 40)
```

## RepoPanel Widget

New widget class in `app.py`.

**Structure:** `VerticalScroll` > `Static#panel-content`

**Public interface:**
- `load_repo(repo: RepoInfo | None)` — starts a new thread worker with `exclusive=True, group="panel"` (Textual cancels the previous worker in that group automatically), clears content to "Loading…" or empty state

**Worker fetches:**
- `git log -20 --format=%h\x1f%s\x1f%cr` (short hash, subject, relative age)
- `git remote get-url origin` for remote URL

**Rendered content:**
```
{name}                         ← cyan bold
{branch} · ↑{ahead} ↓{behind} ← dim if both zero
{remote_url}                   ← dim blue, or "(no remote)" dim
────────────────────────────── ← rule
{hash} {subject:<truncated>} {age}   ← 20 entries
…
(no commits)                   ← fallback
```

Subject truncated to `panel_width - 20` chars (hash=7 + space + age≈10 + padding).

## Cursor Tracking

`GitplorerApp.on_data_table_row_highlighted(event)` → calls `_selected_repo()` → calls `self.query_one(RepoPanel).load_repo(repo)`.

`_is_expand_key` guard: if highlighted row is an expansion row, call `load_repo(None)` to clear panel.

Existing inline expansion rows (`→` key) are unchanged.

## Resize

- `GitplorerApp` holds `_panel_width: int = 40`  
- Bindings: `[` → `action_shrink_panel` (step −4, min 20), `]` → `action_grow_panel` (step +4, max 70)  
- Actions set `self._panel_width` and call `self.query_one(RepoPanel).styles.width = self._panel_width`

## CSS

```css
RepoPanel {
    width: 40;
    border-left: tall $primary-darken-2;
    padding: 0 1;
    background: $surface;
}
```

## Out of Scope

- Mouse drag-to-resize
- Showing changed files in panel (covered by existing `d` diff key and `enter` detail screen)
- Stash entries in panel
- Removing inline expansion rows
