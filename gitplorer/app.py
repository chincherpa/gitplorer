from __future__ import annotations

import subprocess
from pathlib import Path

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.widgets import DataTable, Footer, Header, Label
from textual.worker import Worker, WorkerState

from .collector import RepoInfo, find_and_collect, _run
from .config import load_config

_COMMIT_KEY_PREFIX = "__commit__"
_REMOTE_KEY_PREFIX = "__remote__"


class GitplorerApp(App):
    TITLE = "gitplorer"
    SUB_TITLE = "Git repository dashboard"

    BINDINGS = [
        Binding("f5", "refresh", "Refresh"),
        Binding("f", "toggle_filter", "Filter dirty"),
        Binding("enter", "open_vscode", "Open in VSCode"),
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
    """

    def __init__(self) -> None:
        super().__init__()
        self._all_repos: list[RepoInfo] = []
        self._filter_dirty = False
        self._expanded_path: str | None = None
        self._expanded_commits: list[tuple[str, str]] = []
        self._remote_expanded_path: str | None = None
        self._remote_url: str = ""

    def compose(self) -> ComposeResult:
        yield Header()
        yield Label("Loading...", id="status")
        yield DataTable()
        yield Footer()

    def on_mount(self) -> None:
        table = self.query_one(DataTable)
        table.cursor_type = "row"
        table.add_columns("Repo", "Branch", "Status", "Last Commit", "Age", "↑↓")
        self.action_refresh()

    def action_refresh(self) -> None:
        self._expanded_path = None
        self._expanded_commits = []
        self._remote_expanded_path = None
        self._remote_url = ""
        self.query_one("#status", Label).update("Scanning...")
        self.run_worker(self._load_repos, exclusive=True, thread=True)

    def _load_repos(self) -> list[RepoInfo]:
        config = load_config()
        return find_and_collect(config)

    def _visible_repos(self) -> list[RepoInfo]:
        if self._filter_dirty:
            return [r for r in self._all_repos if r.error or r.dirty_count > 0]
        return self._all_repos

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
            table.add_row(
                repo.name,
                f"[cyan]{repo.branch}[/cyan]" if not repo.error else "",
                self._format_status(repo),
                repo.last_commit if not repo.error else "",
                repo.age if not repo.error else "",
                self._format_ahead_behind(repo),
                key=path_str,
            )
            if path_str == selected_key:
                restore_at = row_index
            row_index += 1

            if path_str == self._remote_expanded_path:
                table.add_row(
                    f"[dim]  remote  [/dim][blue]{self._remote_url or '(no remote)'}[/blue]",
                    "", "", "", "", "",
                    key=f"{_REMOTE_KEY_PREFIX}{path_str}",
                )
                row_index += 1

            if path_str == self._expanded_path:
                for i, (msg, age) in enumerate(self._expanded_commits):
                    table.add_row(
                        f"[dim]  {'└─' if i == len(self._expanded_commits) - 1 else '├─'} {msg}[/dim]",
                        "", "", "", f"[dim]{age}[/dim]", "",
                        key=f"{_COMMIT_KEY_PREFIX}{path_str}_{i}",
                    )
                    row_index += 1

        if restore_at is not None:
            table.move_cursor(row=restore_at)

        filter_note = " [yellow](dirty only)[/yellow]" if self._filter_dirty else ""
        count = len(repos)
        total = len(self._all_repos)
        self.query_one("#status", Label).update(
            f"{count}/{total} repos{filter_note}  "
            f"[dim]f5=refresh  f=filter  r=remote  →=commits  p=push  enter=vscode  q=quit[/dim]"
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

    def _selected_repo(self) -> RepoInfo | None:
        table = self.query_one(DataTable)
        if table.row_count == 0:
            return None
        cursor_key = table.coordinate_to_cell_key(table.cursor_coordinate)
        path_str = cursor_key.row_key.value
        if not path_str or self._is_expand_key(path_str):
            return None
        return next((r for r in self._all_repos if str(r.path) == path_str), None)

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

    def action_open_vscode(self) -> None:
        repo = self._selected_repo()
        if repo:
            subprocess.Popen(
                ["code", str(repo.path)],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )

    def action_git_push(self) -> None:
        repo = self._selected_repo()
        if repo is None or repo.error:
            return
        self.notify(f"Pushing {repo.name}…", timeout=2)
        self.run_worker(
            lambda: _run(["git", "push"], repo.path),
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
                    self.action_refresh()
                else:
                    self.notify(f"✗ Push failed: {msg[:80]}", severity="error", timeout=6)
            return
        if event.state == WorkerState.SUCCESS:
            self._all_repos = event.worker.result
            self._render_table()
        elif event.state == WorkerState.ERROR:
            self.query_one("#status", Label).update("[red]Error during scan[/red]")


def main() -> None:
    GitplorerApp().run()
