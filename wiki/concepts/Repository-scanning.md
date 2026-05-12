# Repository scanning

**Definition:** Recursive directory traversal to discover git repos and capture their current state.
**Why it matters:** Foundation for dashboard — must be fast, handle errors gracefully, exclude unwanted paths.

## How it works

1. Config specifies scan_dirs (e.g., `C:\users\name\projects`)
2. `find_and_collect(config)` walks each dir to depth limit
3. For each subdir, check if `.git/` exists
4. If yes, call `collect_repo(path)` to capture metadata
5. On progress, invoke callback (UI updates "Scanning: X")
6. Return list of RepoInfo + errors

## Scanning parameters

- `scan_dirs`: list of root paths to search
- `depth`: max nesting level (default 3)
- `exclude`: glob patterns to skip (e.g., node_modules, venv)

## Performance

- Shallow depth prevents deep searches in monorepos
- Timeout on each git command (5s) prevents hung processes
- Run in worker thread to keep UI responsive

## Related

- [[Dirty tracking]] — what metadata is collected per repo
- [[Config]] — where scan params are defined
- [[Collector]] — implementation detail

## Examples

Config: `{ "scan_dirs": ["C:\\users\\me\\projects"], "depth": 3, "exclude": ["node_modules", ".venv"] }`
Result: discovers all .git folders 3 levels deep, skips node_modules dirs
