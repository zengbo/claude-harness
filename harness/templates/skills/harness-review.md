---
name: harness-review
description: Multi-perspective code review with configurable perspectives
---

## Steps

1. Get the diff to review:
   - Staged changes: `git diff --cached`
   - Last commit: `git diff HEAD~1`
   - Working tree: `git diff`
2. Determine the task context (ask user if unclear)
3. Run: `harness review --diff "$(git diff)" --task "<description>" --perspective all`
4. For each perspective:
   - Create a Reviewer teammate (prefer a different model for cross-model review)
   - Assign the perspective's review prompt as the task
5. Collect verdicts from all perspectives
6. If all PASS: report success with per-perspective summary
7. If any NEEDS_CHANGE: aggregate issues, group by file, present to user with suggested fixes

## Notes
- Perspectives are configured in `docs/ARCHITECTURE.md` under `review_perspectives`
- Default perspectives: security, performance, quality, accessibility
- Add/remove perspectives to match your project (e.g., remove accessibility for CLI tools, add migration_safety for DB projects)
