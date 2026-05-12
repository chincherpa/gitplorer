# RepoInfo

**Type:** data model (dataclass)
**Summary:** Immutable snapshot of git repo metadata. Populated by `collect_repo()`. Read-only after creation.

## Fields

- `path: Path` — repo root directory
- `branch: str` — current branch name (empty if error)
- `dirty_count: int` — total staged + modified + untracked
- `staged: int` — files in index
- `modified: int` — tracked files with changes
- `untracked: int` — new files
- `last_commit: str` — first line of HEAD commit msg
- `age: str` — human-readable age (e.g., "5 days ago")
- `ahead: int` — commits ahead of origin
- `behind: int` — commits behind origin
- `has_remote: bool` — origin exists (default False)
- `error: bool` — repo is invalid/inaccessible (default False)

## Computed properties

- `name: str` — repo folder name (path.name)

## Error handling

If `git branch --show-current` fails, `error=True` is set + all fields initialized to defaults (empty strings, 0, False).

## Connections

- [[GitplorerApp]] — maintains list of RepoInfo
- [[Collector]] — creates instances via `collect_repo(path)`
- [[RepoDetailScreen]] — receives single RepoInfo instance to display
