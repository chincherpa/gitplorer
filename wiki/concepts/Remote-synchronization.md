# Remote synchronization

**Definition:** Track commits ahead/behind origin to detect sync issues.
**Why it matters:** Catch pushed commits, unpushed work, and diverged branches quickly.

## How it works

1. Run `git rev-list --left-right --count HEAD...origin/branch`
2. Output: two numbers separated by tab (e.g., "3\t1" = 3 ahead, 1 behind)
3. Store in RepoInfo: `ahead`, `behind`
4. Display in table with arrows: `↑3` `↓1`

## Semantics

- **ahead**: commits in HEAD not in origin (unpushed work)
- **behind**: commits in origin not in HEAD (need pull)
- Both > 0: diverged — merge or rebase needed

## UI display

- Table column shows `↑N ↓M` if either nonzero
- Detail screen: shows in branch line, e.g., "main ↑2"
- On push (via `p` key): auto-fetch origin, re-run rev-list check

## Related

- [[RepoInfo]] — ahead, behind fields
- [[GitplorerApp]] — push action + refresh logic

## Open questions

- What if tracking branch differs from default? (currently: assumes origin/<branch>)
- Handle detached HEAD state? (currently: might error)
