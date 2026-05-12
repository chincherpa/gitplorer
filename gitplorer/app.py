from __future__ import annotations

import string
import subprocess
from datetime import datetime
from pathlib import Path

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.screen import Screen
from textual.widgets import Button, DataTable, DirectoryTree, Footer, Header, Label, Static
from textual.worker import Worker, WorkerState


def _get_drives() -> list[str]:
    return [f"{l}:" for l in string.ascii_uppercase if Path(f"{l}:\\").exists()]


def _push_with_auto_commit(repo_path: Path) -> tuple[bool, str]:
    ok, status_out = _run(["git", "status", "--porcelain"], repo_path)
    if not ok:
        return False, status_out
    if status_out.strip():
        ok, msg = _run(["git", "add", "-A"], repo_path)
        if not ok:
            return False, msg
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        ok, msg = _run(["git", "commit", "-m", f"auto push {timestamp}"], repo_path)
        if not ok:
            return False, msg
    return _run(["git", "push"], repo_path)

from .collector import RepoInfo, collect_repo, find_and_collect, _run
from .config import load_config

_COMMIT_KEY_PREFIX = "__commit__"
_REMOTE_KEY_PREFIX = "__remote__"


class RepoDetailScreen(Screen):
    BINDINGS = [
        Binding("enter", "back", "Back"),
        Binding("escape", "back", "Back"),
        Binding("q", "back", "Back"),
        Binding("v", "open_vscode", "Open in VSCode"),
        Binding("o", "open_folder", "Open folder"),
    ]

    CSS = """
    RepoDetailScreen {
        background: $surface;
    }
    VerticalScroll {
        height: 1fr;
        padding: 1 2;
    }
    """

    def __init__(self, repo: RepoInfo) -> None:
        super().__init__()
        self._repo = repo

    def compose(self) -> ComposeResult:
        yield Header()
        with VerticalScroll():
            yield Static("Loading…", id="detail-content")
        yield Footer()

    def on_mount(self) -> None:
        self.run_worker(self._gather_details, thread=True)

    def _gather_details(self) -> str:
        repo = self._repo
        lines: list[str] = []

        # ── Title ────────────────────────────────────────────────────────────
        lines.append(f"[bold cyan]{repo.name}[/bold cyan]  [dim]{repo.path}[/dim]")
        lines.append("")

        # ── Branch + ahead/behind ────────────────────────────────────────────
        ab_parts: list[str] = []
        if repo.ahead:
            ab_parts.append(f"[magenta]↑{repo.ahead}[/magenta]")
        if repo.behind:
            ab_parts.append(f"[magenta]↓{repo.behind}[/magenta]")
        ab_str = "  " + " ".join(ab_parts) if ab_parts else ""
        lines.append(f"Branch: [cyan]{repo.branch}[/cyan]{ab_str}")

        # ── Remote ──────────────────────────────────────────────────────────
        _, url = _run(["git", "remote", "get-url", "origin"], repo.path)
        lines.append(f"Remote: [blue]{url}[/blue]" if url else "Remote: [dim](none)[/dim]")
        lines.append("")

        # ── Working-tree status ──────────────────────────────────────────────
        if repo.error:
            lines.append("[red]Error reading repo[/red]")
        elif repo.dirty_count == 0:
            lines.append("Status: [green]✓ Clean[/green]")
        else:
            parts: list[str] = []
            if repo.staged:
                parts.append(f"[green]{repo.staged} staged[/green]")
            if repo.modified:
                parts.append(f"[yellow]{repo.modified} modified[/yellow]")
            if repo.untracked:
                parts.append(f"[dim]{repo.untracked} untracked[/dim]")
            lines.append(f"Status: [bold]{repo.dirty_count} dirty[/bold]  ({', '.join(parts)})")

            ok, status_out = _run(["git", "status", "--short"], repo.path)
            if ok and status_out:
                for raw in status_out.splitlines()[:25]:
                    if len(raw) < 3:
                        continue
                    x, y, fname = raw[0], raw[1], raw[3:]
                    if x == "?" and y == "?":
                        lines.append(f"  [dim]?  {fname}[/dim]")
                    elif x not in (" ", "?"):
                        lines.append(f"  [green]+  {fname}[/green]")
                    else:
                        lines.append(f"  [yellow]~  {fname}[/yellow]")

        lines.append("")

        # ── Stash ────────────────────────────────────────────────────────────
        ok, stash_out = _run(["git", "stash", "list"], repo.path)
        stash_entries = stash_out.splitlines() if (ok and stash_out) else []
        if stash_entries:
            lines.append(f"Stash: [yellow]{len(stash_entries)} {'entry' if len(stash_entries) == 1 else 'entries'}[/yellow]")
            for entry in stash_entries[:4]:
                lines.append(f"  [dim]{entry}[/dim]")
            if len(stash_entries) > 4:
                lines.append(f"  [dim]… and {len(stash_entries) - 4} more[/dim]")
            lines.append("")

        # ── Last 10 commits ──────────────────────────────────────────────────
        lines.append("[bold]Last 10 commits:[/bold]")
        ok, log_out = _run(
            ["git", "log", "-10", "--format=%h\x1f%s\x1f%cr\x1f%an"],
            repo.path,
        )
        if ok and log_out.strip():
            commit_lines = log_out.splitlines()
            for i, raw in enumerate(commit_lines):
                cols = raw.split("\x1f", 3)
                if len(cols) != 4:
                    continue
                h, msg, age, author = cols
                connector = "└─" if i == len(commit_lines) - 1 else "├─"
                lines.append(
                    f"  [dim]{connector}[/dim] [yellow]{h}[/yellow]  "
                    f"{msg[:55]:<55}  [dim]{age:<18}[/dim]  [cyan]{author}[/cyan]"
                )
        else:
            lines.append("  [dim](no commits)[/dim]")

        return "\n".join(lines)

    def on_worker_state_changed(self, event: Worker.StateChanged) -> None:
        if event.state == WorkerState.SUCCESS:
            self.query_one("#detail-content", Static).update(event.worker.result)

    def action_back(self) -> None:
        self.app.pop_screen()

    def action_open_vscode(self) -> None:
        subprocess.Popen(
            ["code", str(self._repo.path)],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

    def action_open_folder(self) -> None:
        subprocess.Popen(["explorer", str(self._repo.path)])


class QuickDiffScreen(Screen):
    BINDINGS = [
        Binding("escape", "back", "Close"),
        Binding("q", "back", "Close"),
    ]

    CSS = """
    QuickDiffScreen {
        align: center middle;
    }
    #diff-container {
        width: 80%;
        height: 80%;
        border: round $accent;
        background: $surface;
        padding: 1 2;
    }
    """

    def __init__(self, repo: RepoInfo) -> None:
        super().__init__()
        self._repo = repo

    def compose(self) -> ComposeResult:
        with VerticalScroll(id="diff-container"):
            yield Static(
                f"[bold]{self._repo.name}[/bold] — diff --stat\n\n[dim]Loading…[/dim]",
                id="diff-content",
            )

    def on_mount(self) -> None:
        self.run_worker(self._gather_diff, thread=True)

    def _gather_diff(self) -> str:
        ok, out = _run(["git", "diff", "--stat", "HEAD"], self._repo.path)
        if not ok or not out:
            _, out = _run(["git", "diff", "--stat"], self._repo.path)
        return out or "(no changes)"

    def on_worker_state_changed(self, event: Worker.StateChanged) -> None:
        if event.state == WorkerState.SUCCESS:
            content = event.worker.result
            self.query_one("#diff-content", Static).update(
                f"[bold]{self._repo.name}[/bold] — diff --stat\n\n{content}"
            )

    def action_back(self) -> None:
        self.app.pop_screen()


class GitplorerApp(App):
    TITLE = "gitplorer"
    SUB_TITLE = "Git repository dashboard"

    BINDINGS = [
        Binding("f5", "refresh", "Refresh"),
        Binding("f", "toggle_filter", "Filter dirty"),
        Binding("s", "toggle_sort", "Sort"),
        Binding("d", "quick_diff", "Diff"),
        Binding("b", "toggle_sidebar", "Browse"),
        Binding("enter", "open_detail", "Detail"),
        Binding("v", "open_vscode", "VSCode"),
        Binding("o", "open_folder", "Open folder"),
        Binding("right", "expand_commits", "Commits"),
        Binding("left", "collapse_all", "Collapse"),
        Binding("r", "expand_remote", "Remote"),
        Binding("p", "git_push", "Push"),
        Binding("q", "quit", "Quit"),
    ]

    CSS = """
    Screen {
        background: $surface;
    }
    #status {
        height: 1;
        padding: 0 1;
        color: $text-muted;
    }
    DataTable {
        height: 1fr;
    }
    #sidebar {
        width: 30;
        border-right: tall $primary-darken-2;
        display: none;
    }
    #sidebar.active {
        display: block;
    }
    #drive-bar {
        height: 3;
        padding: 0 1;
    }
    .drive-btn {
        min-width: 4;
        height: 3;
        margin-right: 1;
    }
    #dir-tree {
        height: 1fr;
    }
    #main-area {
        width: 1fr;
    }
    """

    def __init__(self) -> None:
        super().__init__()
        self._all_repos: list[RepoInfo] = []
        self._filter_dirty = False
        self._sort_mode: str = "dirty"
        self._expanded_path: str | None = None
        self._expanded_commits: list[tuple[str, str]] = []
        self._remote_expanded_path: str | None = None
        self._remote_url: str = ""
        self._sidebar_visible: bool = False
        self._custom_scan_dir: Path | None = None

    def compose(self) -> ComposeResult:
        yield Header()
        with Horizontal():
            with Vertical(id="sidebar"):
                with Horizontal(id="drive-bar"):
                    for drive in _get_drives():
                        yield Button(drive, id=f"drive-{drive[0]}", classes="drive-btn")
                yield DirectoryTree(Path.home(), id="dir-tree")
            with Vertical(id="main-area"):
                yield Label("Loading...", id="status")
                yield DataTable()
        yield Footer()

    def on_mount(self) -> None:
        table = self.query_one(DataTable)
        table.cursor_type = "row"
        table.add_columns("Repo", "Branch", "Status", "Last Commit", "Age", "↑↓", "Remote")
        self.action_refresh()

    def action_refresh(self) -> None:
        self._custom_scan_dir = None
        self._expanded_path = None
        self._expanded_commits = []
        self._remote_expanded_path = None
        self._remote_url = ""
        self.query_one("#status", Label).update("Scanning...")
        self.run_worker(self._load_repos, exclusive=True, thread=True)

    def _load_repos(self) -> list[RepoInfo]:
        config = load_config()
        if self._custom_scan_dir is not None:
            from .config import Config
            config = Config(
                scan_dirs=[self._custom_scan_dir],
                depth=config.depth,
                exclude=config.exclude,
            )

        def on_progress(path):
            self.call_from_thread(
                self.query_one("#status", Label).update,
                f"Scanning: {path}",
            )

        return find_and_collect(config, on_progress=on_progress)

    def _sorted_repos(self) -> list[RepoInfo]:
        repos = list(self._all_repos)
        if self._sort_mode == "dirty":
            repos.sort(key=lambda r: (not r.error and r.dirty_count == 0, r.name.lower()))
        elif self._sort_mode == "alpha":
            repos.sort(key=lambda r: r.name.lower())
        elif self._sort_mode == "age":
            repos.sort(key=lambda r: (r.error, -r.last_commit_ts))
        return repos

    def _visible_repos(self) -> list[RepoInfo]:
        repos = self._sorted_repos()
        if self._filter_dirty:
            return [r for r in repos if r.error or r.dirty_count > 0]
        return repos

    def _is_expand_key(self, val: str | None) -> bool:
        if val is None:
            return False
        return val.startswith(_COMMIT_KEY_PREFIX) or val.startswith(_REMOTE_KEY_PREFIX)

    def _render_table(self) -> None:
        repos = self._visible_repos()
        table = self.query_one(DataTable)

        selected_key: str | None = None
        if table.row_count > 0:
            try:
                ck = table.coordinate_to_cell_key(table.cursor_coordinate)
                val = ck.row_key.value
                if val and not self._is_expand_key(val):
                    selected_key = val
            except Exception:
                pass

        table.clear()
        row_index = 0
        restore_at: int | None = None

        for repo in repos:
            path_str = str(repo.path)
            no_remote = not repo.error and not repo.has_remote
            if no_remote:
                o, c = "[orange1]", "[/orange1]"
                branch_cell = f"[orange1][cyan]{repo.branch}[/cyan][/orange1]" if not repo.error else ""
                remote_cell = f"[orange1][red]✗[/red][/orange1]"
            else:
                o, c = "", ""
                branch_cell = f"[cyan]{repo.branch}[/cyan]" if not repo.error else ""
                remote_cell = "[green]✓[/green]" if repo.has_remote else "[red]✗[/red]"
            table.add_row(
                f"{o}{repo.name}{c}",
                branch_cell,
                f"{o}{self._format_status(repo)}{c}",
                f"{o}{repo.last_commit if not repo.error else ''}{c}",
                f"{o}{repo.age if not repo.error else ''}{c}",
                f"{o}{self._format_ahead_behind(repo)}{c}",
                remote_cell,
                key=path_str,
            )
            if path_str == selected_key:
                restore_at = row_index
            row_index += 1

            if path_str == self._remote_expanded_path:
                table.add_row(
                    f"[dim]  remote  [/dim][blue]{self._remote_url or '(no remote)'}[/blue]",
                    "", "", "", "", "", "",
                    key=f"{_REMOTE_KEY_PREFIX}{path_str}",
                )
                row_index += 1

            if path_str == self._expanded_path:
                for i, (msg, age) in enumerate(self._expanded_commits):
                    table.add_row(
                        f"[dim]  {'└─' if i == len(self._expanded_commits) - 1 else '├─'} {msg}[/dim]",
                        "", "", "", f"[dim]{age}[/dim]", "", "",
                        key=f"{_COMMIT_KEY_PREFIX}{path_str}_{i}",
                    )
                    row_index += 1

        if restore_at is not None:
            table.move_cursor(row=restore_at)

        filter_note = " [yellow](dirty only)[/yellow]" if self._filter_dirty else ""
        sort_labels = {"dirty": "dirty", "alpha": "a-z", "age": "recent"}
        sort_note = f" [dim](sort: {sort_labels[self._sort_mode]})[/dim]"
        count = len(repos)
        total = len(self._all_repos)
        self.query_one("#status", Label).update(
            f"{count}/{total} repos{filter_note}{sort_note}  "
            f"[dim]f5=refresh  f=filter  s=sort  d=diff  r=remote  →=commits  p=push  enter=detail  v=vscode  o=folder  q=quit[/dim]"
        )

    def _format_status(self, repo: RepoInfo) -> str:
        if repo.error:
            return "[red]ERR[/red]"
        if repo.dirty_count == 0:
            return "[green]✓[/green]"
        parts = []
        if repo.staged:
            parts.append(f"[green]+{repo.staged}[/green]")
        if repo.modified:
            parts.append(f"[yellow]~{repo.modified}[/yellow]")
        if repo.untracked:
            parts.append(f"[dim]?{repo.untracked}[/dim]")
        return " ".join(parts)

    def _format_ahead_behind(self, repo: RepoInfo) -> str:
        if repo.error or (repo.ahead == 0 and repo.behind == 0):
            return ""
        parts = []
        if repo.ahead:
            parts.append(f"[magenta]↑{repo.ahead}[/magenta]")
        if repo.behind:
            parts.append(f"[magenta]↓{repo.behind}[/magenta]")
        return " ".join(parts)

    def action_toggle_filter(self) -> None:
        self._filter_dirty = not self._filter_dirty
        self._expanded_path = None
        self._expanded_commits = []
        self._remote_expanded_path = None
        self._render_table()

    def action_toggle_sort(self) -> None:
        modes = ["dirty", "alpha", "age"]
        self._sort_mode = modes[(modes.index(self._sort_mode) + 1) % len(modes)]
        self._render_table()

    def action_toggle_sidebar(self) -> None:
        self._sidebar_visible = not self._sidebar_visible
        sidebar = self.query_one("#sidebar")
        if self._sidebar_visible:
            sidebar.add_class("active")
            self.query_one("#dir-tree", DirectoryTree).focus()
        else:
            sidebar.remove_class("active")
            self.query_one(DataTable).focus()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        btn_id = event.button.id or ""
        if btn_id.startswith("drive-"):
            letter = btn_id[6]
            self.query_one("#dir-tree", DirectoryTree).path = Path(f"{letter}:\\")

    def _selected_repo(self) -> RepoInfo | None:
        table = self.query_one(DataTable)
        if table.row_count == 0:
            return None
        cursor_key = table.coordinate_to_cell_key(table.cursor_coordinate)
        path_str = cursor_key.row_key.value
        if not path_str or self._is_expand_key(path_str):
            return None
        return next((r for r in self._all_repos if str(r.path) == path_str), None)

    def on_directory_tree_directory_selected(
        self, event: DirectoryTree.DirectorySelected
    ) -> None:
        self._custom_scan_dir = event.path
        self._expanded_path = None
        self._expanded_commits = []
        self._remote_expanded_path = None
        self._remote_url = ""
        self.query_one("#status", Label).update(f"Scanning {event.path.name}...")
        self.run_worker(self._load_repos, exclusive=True, thread=True)

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        path_str = event.row_key.value
        if not path_str or self._is_expand_key(path_str):
            return
        repo = next((r for r in self._all_repos if str(r.path) == path_str), None)
        if repo and not repo.error:
            self.push_screen(RepoDetailScreen(repo))

    def action_open_detail(self) -> None:
        repo = self._selected_repo()
        if repo and not repo.error:
            self.push_screen(RepoDetailScreen(repo))

    def action_quick_diff(self) -> None:
        repo = self._selected_repo()
        if repo is None or repo.error:
            return
        self.push_screen(QuickDiffScreen(repo))

    def action_open_vscode(self) -> None:
        repo = self._selected_repo()
        if repo:
            subprocess.Popen(
                ["code", str(repo.path)],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                shell=True,
            )

    def action_open_folder(self) -> None:
        repo = self._selected_repo()
        if repo:
            subprocess.Popen(["explorer", str(repo.path)])

    def action_expand_commits(self) -> None:
        repo = self._selected_repo()
        if repo is None or repo.error:
            return
        path_str = str(repo.path)
        if self._expanded_path == path_str:
            self._expanded_path = None
            self._expanded_commits = []
            self._render_table()
            return

        ok, out = _run(["git", "log", "-5", "--format=%s\x1f%cr"], repo.path)
        commits: list[tuple[str, str]] = []
        if ok and out.strip():
            for line in out.splitlines():
                if "\x1f" in line:
                    msg, age = line.split("\x1f", 1)
                    commits.append((msg[:50], age))

        self._expanded_path = path_str
        self._expanded_commits = commits
        self._render_table()

    def action_expand_remote(self) -> None:
        repo = self._selected_repo()
        if repo is None or repo.error:
            return
        path_str = str(repo.path)
        if self._remote_expanded_path == path_str:
            self._remote_expanded_path = None
            self._remote_url = ""
            self._render_table()
            return

        _, url = _run(["git", "remote", "get-url", "origin"], repo.path)
        self._remote_expanded_path = path_str
        self._remote_url = url
        self._render_table()

    def action_collapse_all(self) -> None:
        changed = bool(self._expanded_path or self._remote_expanded_path)
        self._expanded_path = None
        self._expanded_commits = []
        self._remote_expanded_path = None
        self._remote_url = ""
        if changed:
            self._render_table()

    def action_git_push(self) -> None:
        repo = self._selected_repo()
        if repo is None or repo.error:
            return
        self.notify(f"Pushing {repo.name}…", timeout=2)
        self.run_worker(
            lambda: _push_with_auto_commit(repo.path),
            exclusive=False,
            thread=True,
            name=f"push_{repo.name}",
        )

    def on_worker_state_changed(self, event: Worker.StateChanged) -> None:
        if event.worker.name and event.worker.name.startswith("push_"):
            if event.state == WorkerState.SUCCESS:
                ok, msg = event.worker.result
                repo_name = event.worker.name[len("push_"):]
                if ok:
                    self.notify(f"✓ {repo_name} pushed", severity="information")
                    repo = next((r for r in self._all_repos if r.name == repo_name), None)
                    if repo is not None:
                        self._refresh_single_repo(repo.path)
                else:
                    self.notify(f"✗ Push failed: {msg[:80]}", severity="error", timeout=6)
            return
        if event.worker.name and event.worker.name.startswith("refresh_repo_"):
            if event.state == WorkerState.SUCCESS:
                updated = event.worker.result
                for i, r in enumerate(self._all_repos):
                    if r.path == updated.path:
                        self._all_repos[i] = updated
                        break
                self._render_table()
            return
        if event.state == WorkerState.SUCCESS:
            self._all_repos = event.worker.result
            self._render_table()
        elif event.state == WorkerState.ERROR:
            self.query_one("#status", Label).update("[red]Error during scan[/red]")

    def _refresh_single_repo(self, repo_path: Path) -> None:
        self.run_worker(
            lambda: collect_repo(repo_path),
            exclusive=False,
            thread=True,
            name=f"refresh_repo_{repo_path}",
        )


def main() -> None:
    GitplorerApp().run()
