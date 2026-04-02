from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path

from .config import Config


@dataclass
class RepoInfo:
    path: Path
    branch: str
    dirty_count: int
    staged: int
    modified: int
    untracked: int
    last_commit: str
    age: str
    ahead: int
    behind: int
    error: bool = False

    @property
    def name(self) -> str:
        return self.path.name


def _run(cmd: list[str], cwd: Path) -> tuple[bool, str]:
    try:
        result = subprocess.run(
            cmd,
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode != 0:
            return False, result.stderr.strip()
        return True, result.stdout.strip()
    except (subprocess.TimeoutExpired, OSError):
        return False, ""


def collect_repo(path: Path) -> RepoInfo:
    ok, branch = _run(["git", "branch", "--show-current"], path)
    if not ok:
        return RepoInfo(path=path, branch="", dirty_count=0, staged=0, modified=0, untracked=0, last_commit="", age="", ahead=0, behind=0, error=True)

    _, status_out = _run(["git", "status", "--short"], path)
    staged = modified = untracked = 0
    for line in (status_out.splitlines() if status_out else []):
        if len(line) < 2:
            continue
        x, y = line[0], line[1]
        if x == "?" and y == "?":
            untracked += 1
        else:
            if x not in (" ", "?"):
                staged += 1
            if y not in (" ", "?"):
                modified += 1
    dirty_count = staged + modified + untracked

    ok, log_out = _run(["git", "log", "-1", "--format=%s|%cr"], path)
    if ok and "|" in log_out:
        parts = log_out.split("|", 1)
        last_commit = parts[0][:50]
        age = parts[1]
    else:
        last_commit = ""
        age = ""

    ok, rev_out = _run(["git", "rev-list", "--left-right", "--count", "HEAD...@{u}"], path)
    if ok and "\t" in rev_out:
        parts = rev_out.split()
        try:
            ahead, behind = int(parts[0]), int(parts[1])
        except (ValueError, IndexError):
            ahead, behind = 0, 0
    else:
        ahead, behind = 0, 0

    return RepoInfo(
        path=path,
        branch=branch or "HEAD",
        dirty_count=dirty_count,
        staged=staged,
        modified=modified,
        untracked=untracked,
        last_commit=last_commit,
        age=age,
        ahead=ahead,
        behind=behind,
    )


def _is_git_repo(path: Path) -> bool:
    return (path / ".git").exists()


def _scan(directory: Path, depth: int, exclude: list[str]) -> list[Path]:
    repos: list[Path] = []
    if depth < 0:
        return repos
    try:
        for child in directory.iterdir():
            if not child.is_dir():
                continue
            if child.name in exclude:
                continue
            if _is_git_repo(child):
                repos.append(child)
            else:
                repos.extend(_scan(child, depth - 1, exclude))
    except PermissionError:
        pass
    return repos


def find_and_collect(config: Config) -> list[RepoInfo]:
    paths: list[Path] = []
    for scan_dir in config.scan_dirs:
        if not scan_dir.exists():
            continue
        paths.extend(_scan(scan_dir, config.depth, config.exclude))

    # deduplicate
    seen: set[Path] = set()
    unique: list[Path] = []
    for p in paths:
        rp = p.resolve()
        if rp not in seen:
            seen.add(rp)
            unique.append(p)

    repos = [collect_repo(p) for p in unique]

    # sort: dirty first, then alphabetical
    repos.sort(key=lambda r: (not r.error and r.dirty_count == 0, r.name.lower()))
    return repos
