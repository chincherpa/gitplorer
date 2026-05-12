# RepoDetailScreen

**Type:** component (Textual Screen)
**Summary:** Modal detail view for single repo. Shows status, commits, stash, remote, dirty files. Dismissible.

## Key Facts

- Class: `RepoDetailScreen(Screen)` in app.py
- Receives `repo: RepoInfo` in `__init__()`
- Worker-driven: runs `_gather_details()` in thread on mount
- Header + scrollable content + footer layout

## Display sections

1. **Title + path**
2. **Branch** + ahead/behind arrows
3. **Remote URL** (fetched live via `git remote get-url origin`)
4. **Status** — clean or dirty count + breakdown (staged/modified/untracked)
5. **Changed files** — first 25 dirty files via `git status --short`
6. **Stash** — count + first 4 entries
7. **Last 10 commits** — hash, message, age, author

## Keybindings

- `enter` / `escape` / `q`: dismiss + return to main app
- `v`: open repo in VSCode
- `o`: open repo folder in Explorer

## Connections

- [[GitplorerApp]] — pushed when user presses enter on table row
- [[RepoInfo]] — source data for display

## Error handling

If repo.error=True, shows "Error reading repo" instead of computed fields.
