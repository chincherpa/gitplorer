# Collector

**Type:** module (git operations, data extraction)
**Summary:** Functions to discover repos and capture metadata. Separates git logic from UI.

## Key functions

- `collect_repo(path: Path) -> RepoInfo` — snapshot single repo state
  - Runs ~8 git commands (branch, status, log, rev-list, remote, stash)
  - Returns RepoInfo or error state if any command fails
  - 5s timeout per command prevents hangs

- `find_and_collect(config: Config, on_progress) -> list[RepoInfo]` — scan directory tree
  - Walks scan_dirs to depth limit
  - Skips paths matching exclude patterns
  - For each .git folder found, calls collect_repo()
  - Invokes on_progress callback for UI updates

- `_run(cmd: list[str], cwd: Path) -> tuple[bool, str]` — execute git command
  - Wrapper around subprocess.run
  - Returns (success, output_or_error_message)
  - Handles timeout, OSError gracefully

## Connections

- [[GitplorerApp]] — calls find_and_collect() in worker
- [[RepoInfo]] — produces instances
- [[Repository scanning]] — implements scanning logic
- [[Dirty tracking]] — extracts dirty files
- [[Remote synchronization]] — checks ahead/behind

## Error handling

- Command timeout: return (False, "")
- Invalid repo: return RepoInfo with error=True
- File not found: return (False, "")
