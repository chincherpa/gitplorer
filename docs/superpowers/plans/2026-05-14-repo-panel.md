# Repo Panel Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a persistent right-side panel to `GitplorerApp` that shows commit history and repo metadata for the currently highlighted repo, resizable with `[`/`]` keys.

**Architecture:** New `RepoPanel` widget class (extends `VerticalScroll`) added to `app.py`. `GitplorerApp` wires cursor tracking via `on_data_table_row_highlighted`, which calls `panel.load_repo(repo)`. Panel fires a thread worker (exclusive, group="panel") to fetch git data without blocking the UI. Resize actions update both `styles.width` and `panel._width`.

**Tech Stack:** Python 3.11+, Textual 8.2.1, Rich markup

---

## Files

- **Modify:** `gitplorer/app.py` — all changes live here

---

### Task 1: Add `RepoPanel` class + update layout

**Files:**
- Modify: `gitplorer/app.py`

- [ ] **Step 1: Add `RepoPanel` class above `GitplorerApp`**

Insert this class in `gitplorer/app.py` immediately above the `GitplorerApp` class definition (after `QuickDiffScreen`):

```python
class RepoPanel(VerticalScroll):
    DEFAULT_CSS = """
    RepoPanel {
        width: 40;
        border-left: tall $primary-darken-2;
        padding: 0 1;
        background: $surface;
    }
    """

    def __init__(self) -> None:
        super().__init__()
        self._width: int = 40

    def compose(self) -> ComposeResult:
        yield Static("", id="panel-content")

    def load_repo(self, repo: "RepoInfo | None") -> None:
        content = self.query_one("#panel-content", Static)
        if repo is None:
            content.update("")
            return
        content.update("[dim]Loading…[/dim]")
        width = self._width
        self.run_worker(
            lambda: self._build_content(repo, width),
            exclusive=True,
            group="panel",
            thread=True,
        )

    def _build_content(self, repo: "RepoInfo", width: int) -> str:
        lines: list[str] = []
        lines.append(f"[bold cyan]{repo.name}[/bold cyan]")
        ab_parts: list[str] = []
        if repo.ahead:
            ab_parts.append(f"↑{repo.ahead}")
        if repo.behind:
            ab_parts.append(f"↓{repo.behind}")
        branch_line = f"[cyan]{repo.branch}[/cyan]"
        if ab_parts:
            branch_line += f"  [magenta]{' '.join(ab_parts)}[/magenta]"
        lines.append(branch_line)
        _, url = _run(["git", "remote", "get-url", "origin"], repo.path)
        lines.append(f"[dim blue]{url}[/dim blue]" if url else "[dim](no remote)[/dim]")
        lines.append("[dim]" + "─" * max(1, width - 4) + "[/dim]")
        ok, log_out = _run(
            ["git", "log", "-20", "--format=%h\x1f%s\x1f%cr"],
            repo.path,
        )
        if ok and log_out.strip():
            subj_len = max(10, width - 22)
            for raw in log_out.splitlines():
                cols = raw.split("\x1f", 2)
                if len(cols) != 3:
                    continue
                h, msg, age = cols
                lines.append(
                    f"[yellow]{h}[/yellow] {msg[:subj_len]:<{subj_len}}  [dim]{age}[/dim]"
                )
        else:
            lines.append("[dim](no commits)[/dim]")
        return "\n".join(lines)

    def on_worker_state_changed(self, event: Worker.StateChanged) -> None:
        event.stop()
        if event.state == WorkerState.SUCCESS:
            self.query_one("#panel-content", Static).update(event.worker.result)
```

- [ ] **Step 2: Add `#table-area` CSS to `GitplorerApp.CSS`**

In `GitplorerApp.CSS` (the multi-line string), add this rule after the existing `#main-area` rule:

```css
#table-area {
    height: 1fr;
}
```

- [ ] **Step 3: Update `GitplorerApp.compose()` to include `RepoPanel`**

Replace the `DataTable()` yield inside `with Vertical(id="main-area"):`:

```python
# Before:
with Vertical(id="main-area"):
    yield Label("Loading...", id="status")
    yield DataTable()

# After:
with Vertical(id="main-area"):
    yield Label("Loading...", id="status")
    with Horizontal(id="table-area"):
        yield DataTable()
        yield RepoPanel()
```

- [ ] **Step 4: Add `_panel_width` to `GitplorerApp.__init__`**

In `GitplorerApp.__init__`, add this line at the end of the method body:

```python
self._panel_width: int = 40
```

- [ ] **Step 5: Manual test — panel renders**

Run `gitplorer`. Verify:
- Right panel visible with left border, empty content
- Main table still works, no crash on startup
- `enter` on a repo still opens detail screen

---

### Task 2: Wire cursor tracking

**Files:**
- Modify: `gitplorer/app.py`

- [ ] **Step 1: Add `on_data_table_row_highlighted` to `GitplorerApp`**

Add this method to `GitplorerApp` (after `on_data_table_row_selected`):

```python
def on_data_table_row_highlighted(self, event: DataTable.RowHighlighted) -> None:
    path_str = event.row_key.value if event.row_key else None
    panel = self.query_one(RepoPanel)
    if not path_str or self._is_expand_key(path_str):
        panel.load_repo(None)
        return
    repo = next((r for r in self._all_repos if str(r.path) == path_str), None)
    panel.load_repo(repo)
```

- [ ] **Step 2: Refresh panel after table rebuild**

At the end of `GitplorerApp._render_table()`, add these lines (after `self.query_one("#status", Label).update(...)`):

```python
repo = self._selected_repo()
self.query_one(RepoPanel).load_repo(repo)
```

- [ ] **Step 4: Manual test — panel updates on cursor move**

Run `gitplorer`. Arrow-key through the repo list. Verify:
- Panel shows repo name, branch, remote URL, and commits for highlighted row
- Moving cursor updates panel within ~1 second (worker latency)
- Landing on an inline expansion row (press `→` to expand first) clears the panel
- Press `F5` to refresh — panel repopulates for the selected row after reload
- `error` repos load without crash (panel shows name + branch, no commits = "(no commits)")

---

### Task 3: Add resize bindings

**Files:**
- Modify: `gitplorer/app.py`

- [ ] **Step 1: Add `[` and `]` to `GitplorerApp.BINDINGS`**

In `GitplorerApp.BINDINGS`, add:

```python
Binding("[", "shrink_panel", "Panel −"),
Binding("]", "grow_panel", "Panel +"),
```

- [ ] **Step 2: Add resize actions to `GitplorerApp`**

Add these two methods to `GitplorerApp` (after `action_collapse_all`):

```python
def action_shrink_panel(self) -> None:
    self._panel_width = max(20, self._panel_width - 4)
    panel = self.query_one(RepoPanel)
    panel.styles.width = self._panel_width
    panel._width = self._panel_width

def action_grow_panel(self) -> None:
    self._panel_width = min(70, self._panel_width + 4)
    panel = self.query_one(RepoPanel)
    panel.styles.width = self._panel_width
    panel._width = self._panel_width
```

- [ ] **Step 3: Manual test — resize**

Run `gitplorer`. Press `]` three times — panel grows. Press `[` three times — panel shrinks. Verify min 20 and max 70 are respected. Verify commit subjects re-truncate on next cursor move after resize.

---

### Task 4: Commit

- [ ] **Step 1: Stage and commit**

```bash
git add gitplorer/app.py
git commit -m "feat: add persistent repo panel with commit history"
```
