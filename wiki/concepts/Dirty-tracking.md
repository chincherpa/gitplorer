# Dirty tracking

**Definition:** Aggregate count of staged + modified + untracked files. Display as single "dirty" count or breakdown.
**Why it matters:** Identifies repos needing attention. Filter by dirty state to focus on active work.

## How it works

1. Run `git status --short` for every repo
2. Parse output: first char = index state, second char = worktree state
3. Count by category:
   - `x == "?"`: untracked
   - `x != " "` and `x != "?"`: staged
   - `y != " "`: modified
4. Sum all three = `dirty_count`
5. Store breakdown in RepoInfo for display

## Status codes (git status --short)

| Code | Meaning |
|------|---------|
| ` M` | modified in worktree |
| `M ` | staged |
| `MM` | staged + modified |
| `A` | added to index |
| `??` | untracked |

## Display

- Status col in table: count + (staged/modified/untracked) breakdown
- Detail screen: first 25 dirty files with status markers
- Filter dirty: toggle to show only repos with dirty_count > 0

## Related

- [[RepoInfo]] — dirty_count, staged, modified, untracked fields
- [[GitplorerApp]] — `action_toggle_filter()` + filtering logic

## Open questions

- Should stashed changes count toward dirty? (currently: no)
